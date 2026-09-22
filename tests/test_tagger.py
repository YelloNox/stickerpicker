import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tag_stickers', ROOT / 'scripts/tag-stickers.py')
tagger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tagger)


class TaggerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'thumbnails').mkdir()
        (self.root / 'thumbnails/image').write_bytes(b'image one')
        (self.root / 'index.json').write_text(json.dumps({'packs': ['pack.json']}))
        self.path = self.root / 'pack.json'
        self.path.write_text(json.dumps({'title': 'Test', 'stickers': [
            {'url': 'mxc://server/image', 'tags': ['manual'], 'excluded_tags': ['wrong'],
             'body': 'hello', 'custom': 42}]}))
        self.args = SimpleNamespace(packs_dir=self.root, pack=None, cache_dir=self.root/'cache',
                                    device='cpu', threshold=.35, max_tags=40, force=False, dry_run=False)
        self.calls = 0

    def factory(self, cache, device):
        self.calls += 1
        return SimpleNamespace(predict=lambda *args: [{'tag': 'happy', 'score': .9}])

    def test_resume_force_content_and_settings_changes(self):
        self.assertEqual(tagger.run(self.args, self.factory), 0)
        sticker = json.loads(self.path.read_text())['stickers'][0]
        self.assertEqual(sticker['tags'], ['manual'])
        self.assertEqual(sticker['excluded_tags'], ['wrong'])
        self.assertEqual(sticker['custom'], 42)
        before = self.path.read_bytes()
        tagger.run(self.args, self.factory)
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.path.read_bytes(), before)
        (self.root/'thumbnails/image').write_bytes(b'changed')
        tagger.run(self.args, self.factory)
        self.args.threshold = .5
        tagger.run(self.args, self.factory)
        self.args.force = True
        tagger.run(self.args, self.factory)
        self.assertEqual(self.calls, 4)

    def test_dry_run_no_model_or_changes(self):
        before = self.path.read_bytes()
        self.args.dry_run = True
        self.assertEqual(tagger.run(self.args, self.factory), 0)
        self.assertEqual(self.calls, 0)
        self.assertEqual(self.path.read_bytes(), before)

    def test_missing_thumbnail_does_not_erase_metadata(self):
        (self.root/'thumbnails/image').unlink()
        before = self.path.read_bytes()
        self.assertEqual(tagger.run(self.args, self.factory), 1)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.calls, 0)

    def test_completed_image_survives_later_failure(self):
        pack = json.loads(self.path.read_text())
        pack['stickers'].append({'url': 'mxc://server/missing'})
        self.path.write_text(json.dumps(pack))
        self.assertEqual(tagger.run(self.args, self.factory), 1)
        self.assertIn('auto_tags', json.loads(self.path.read_text())['stickers'][0])

    def test_remote_or_traversing_pack_rejected(self):
        for name in ['https://example.com/pack.json', '../outside.json']:
            with self.assertRaises(ValueError):
                tagger.pack_paths(self.root, [name])

    def test_setup_failure_not_retried_per_sticker(self):
        def broken(*args):
            raise OSError('download failed')
        with self.assertRaises(RuntimeError):
            tagger.run(self.args, broken)


if __name__ == '__main__':
    unittest.main()
