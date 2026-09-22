#!/usr/bin/env python3
"""Tag local sticker thumbnails with a cached, pinned Taggerine model."""
import argparse
from contextlib import nullcontext
import hashlib
import importlib.util
from io import BytesIO
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MODEL = 'lodestones/taggerine'
REVISION = 'ba76a13a17a9d1844298a68c142c5aae6191505d'
FILES = ('inference_tagger_standalone.py', 'tagger_proto.safetensors',
         'tagger_vocab_with_categories_and_alias_updated.json')


def atomic_json(path, data):
    """Replace a complete JSON file, never leave a partially written pack."""
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         suffix='.tmp', delete=False) as out:
            temp = Path(out.name)
            json.dump(data, out, ensure_ascii=False, indent=2)
            out.write('\n')
        os.chmod(temp, path.stat().st_mode & 0o777)
        os.replace(temp, path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def model_files(cache):
    from huggingface_hub import hf_hub_download
    result = []
    for name in FILES:
        kwargs = dict(repo_id=MODEL, filename=name, revision=REVISION, cache_dir=str(cache))
        try:
            path = hf_hub_download(**kwargs, local_files_only=True)
        except FileNotFoundError:
            print(f'Downloading {name} (model weights are several GB)...', flush=True)
            path = hf_hub_download(**kwargs)
        result.append(path)
    return result


class Predictor:
    def __init__(self, cache, device):
        import torch
        script, checkpoint, vocab = model_files(cache)
        spec = importlib.util.spec_from_file_location('stickerpicker_taggerine', script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if device == 'cuda' and not torch.cuda.is_available():
            raise RuntimeError('GPU unavailable. Run setup-tagger.sh rocm, check ROCm/device permissions, '
                               'or use --device cpu.')
        self.torch = torch
        self.device = device
        dtype = torch.bfloat16 if device == 'cuda' else torch.float32
        self.tagger = module.Tagger(checkpoint, vocab, device=device, dtype=dtype, max_size=512)
        print('Using ' + (torch.cuda.get_device_name(0) if device == 'cuda' else 'CPU (slower)'))

    def predict(self, data, threshold, max_tags):
        from PIL import Image
        # Transparent stickers need a visible background, not discarded alpha.
        with Image.open(BytesIO(data)) as source:
            rgba = source.convert('RGBA')
            canvas = Image.new('RGBA', rgba.size, 'white')
            canvas.alpha_composite(rgba)
            prepared = BytesIO()
            canvas.convert('RGB').save(prepared, 'PNG')
        prepared.seek(0)
        # Upstream preprocessing is fp32 while the GPU backbone is bf16.
        context = (self.torch.autocast('cuda', dtype=self.torch.bfloat16)
                   if self.device == 'cuda' else nullcontext())
        with context:
            tags = self.tagger.predict(prepared, topk=None, threshold=threshold)
        return [{'tag': tag, 'score': round(score, 5)} for tag, score in tags[:max_tags]]


def pack_paths(directory, selected):
    names = selected or json.loads((directory / 'index.json').read_text())['packs']
    paths = []
    for name in names:
        if name.startswith(('http://', 'https://')):
            raise ValueError(f'Remote pack {name}: download it into the packs directory first.')
        path = (directory / name).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError(f'Pack must be inside {directory}: {name}')
        if path not in paths:
            paths.append(path)
    return paths


def run(args, predictor_factory=Predictor):
    predictor = None
    tagged = skipped = failed = pending = 0
    for path in pack_paths(args.packs_dir, args.pack):
        pack = json.loads(path.read_text(encoding='utf-8'))
        for sticker in pack['stickers']:
            label = sticker.get('id') or sticker.get('url', '(missing URL)')
            try:
                media_id = sticker['url'].rsplit('/', 1)[-1]
                if not media_id or media_id in ('.', '..'):
                    raise ValueError('Invalid sticker media ID')
                image_path = args.packs_dir / 'thumbnails' / media_id
                data = image_path.read_bytes()
                signature = dict(model=MODEL, revision=REVISION,
                                 image_sha256=hashlib.sha256(data).hexdigest(),
                                 threshold=args.threshold, max_tags=args.max_tags,
                                 preprocessing='white-background-512-v1')
                previous = sticker.get('auto_tags') or {}
                if (not args.force and isinstance(previous.get('tags'), list)
                        and all(previous.get(k) == v for k, v in signature.items())):
                    skipped += 1
                    continue
                pending += 1
                if args.dry_run:
                    print(f'Would tag {path.name}: {label}')
                    continue
                if predictor is None:
                    # Setup failures abort rather than retrying a multi-GB load per image.
                    try:
                        predictor = predictor_factory(args.cache_dir, args.device)
                    except Exception as error:
                        raise RuntimeError(f'Model setup failed: {error}') from error
                tags = predictor.predict(data, args.threshold, args.max_tags)
                sticker['auto_tags'] = {**signature, 'tags': tags}
                atomic_json(path, pack)
                tagged += 1
                print(f'Tagged {path.name}: {label} ({len(tags)} tags)', flush=True)
            except (OSError, ValueError, KeyError) as error:
                failed += 1
                print(f'Could not tag {path.name}: {label}: {error}', file=sys.stderr)
    print(f'{tagged} tagged, {skipped} unchanged, {failed} failed'
          + (f', {pending} need tagging' if args.dry_run else ''))
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packs-dir', type=Path, default=ROOT / 'web/packs')
    parser.add_argument('--pack', action='append', help='Pack filename; repeat to select several. Default: index.json')
    parser.add_argument('--cache-dir', type=Path,
                        default=Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'stickerpicker/taggerine')
    parser.add_argument('--device', choices=('auto', 'cuda', 'cpu'), default='auto',
                        help='cuda also selects AMD GPUs through PyTorch ROCm')
    parser.add_argument('--threshold', type=float, default=0.50)
    parser.add_argument('--max-tags', type=int, default=100)
    parser.add_argument('--force', action='store_true', help='Regenerate tags even for unchanged images')
    parser.add_argument('--dry-run', action='store_true', help='List work without downloading or loading a model')
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1 or args.max_tags < 1:
        parser.error('--threshold must be 0..1 and --max-tags must be positive')
    try:
        return run(args)
    except ImportError as error:
        print(f'Missing dependency: {error}. Run bash scripts/setup-tagger.sh first.', file=sys.stderr)
        return 1
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print(f'Tagging stopped: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
