#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="${1:-rocm}"
case "$BACKEND" in
  rocm) TORCH_INDEX="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/rocm7.2}" ;;
  cpu) TORCH_INDEX="https://download.pytorch.org/whl/cpu" ;;
  *) echo 'Usage: bash scripts/setup-tagger.sh [rocm|cpu]' >&2; exit 2 ;;
esac
"${TAGGER_PYTHON:-python3}" -m venv "$REPO_DIR/.venv-tagger"
TAGGER_PY="$REPO_DIR/.venv-tagger/bin/python"
"$TAGGER_PY" -m pip install --upgrade pip
"$TAGGER_PY" -m pip install torch torchvision --index-url "$TORCH_INDEX"
"$TAGGER_PY" -m pip install -r "$REPO_DIR/scripts/tagger-requirements.txt"
"$TAGGER_PY" - "$BACKEND" <<'PY'
import sys
import torch
print('PyTorch:', torch.__version__, 'ROCm:', torch.version.hip)
if sys.argv[1] == 'rocm' and (not torch.version.hip or not torch.cuda.is_available()):
    sys.exit('ROCm GPU is not accessible. Check /dev/kfd and /dev/dri permissions and your AMD drivers. '
             'CPU mode remains available: bash scripts/tag-stickers.sh --device cpu')
if torch.cuda.is_available():
    print('GPU:', torch.cuda.get_device_name(0))
    # Exercise a kernel as well as detecting the device.
    print('GPU check:', (torch.ones(2, device='cuda') + 1).cpu().tolist())
PY
printf '\nSetup complete. Run: bash scripts/tag-stickers.sh\n'
