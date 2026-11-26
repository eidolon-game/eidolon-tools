#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "Usage: ${0##*/} [--require-ue] [--with-cmake]"
    echo "Set EIDOLON_GAME_ROOT to override the sibling eidolon-game checkout."
    echo "Set EIDOLON_CLOUD_DIR to override /workspace/.eidolon-cloud for optional tools."
    echo "Set UE_ROOT to an authorized Unreal Engine 5.6 Linux installation."
}

require_ue=0
with_cmake=0
for argument in "$@"; do
    case "$argument" in
        --require-ue) require_ue=1 ;;
        --with-cmake) with_cmake=1 ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done

tools_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
game_root="${EIDOLON_GAME_ROOT:-$tools_root/../eidolon-game}"

for tool in git python3; do
    if ! command -v "$tool" >/dev/null; then
        printf 'Missing required command: %s\n' "$tool" >&2
        exit 1
    fi
done

git --version
git lfs version
python3 --version
if ((with_cmake)); then
    # The locked wheels target the x86_64 Linux cloud image.
    if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
        echo 'The optional CMake installation requires x86_64 Linux.' >&2
        exit 1
    fi
    cmake_venv="${EIDOLON_CLOUD_DIR:-/workspace/.eidolon-cloud}/cmake-3.31.10"
    python3 -m venv "$cmake_venv"
    "$cmake_venv/bin/python" -m pip --isolated --disable-pip-version-check --no-cache-dir install \
        --index-url https://pypi.org/simple/ --only-binary=:all: --no-deps --require-hashes -r /dev/stdin <<'REQUIREMENTS'
cmake==3.31.10 \
    --hash=sha256:3c17bb24dba15f8ecc3fd706afe04264410ef88796f4115c119327c961d5dc57 \
    --hash=sha256:2f766bb46367e5e0559fa33184653754bce044583a06014dcaebf8e6dff8a1f1
REQUIREMENTS
    export PATH="$cmake_venv/bin:$PATH"
    cmake --version
fi
for tool in c++ clang++ cmake ninja blender ffmpeg magick; do
    if command -v "$tool" >/dev/null; then
        printf '%s: %s\n' "$tool" "$(command -v "$tool")"
    else
        printf '%s: unavailable\n' "$tool"
    fi
done
python3 "$tools_root/scripts/validate_project.py" "$game_root"
python3 "$game_root/scripts/validate_source.py"

if [[ -z "${UE_ROOT:-}" ]]; then
    if ((require_ue)); then
        echo 'Set UE_ROOT to an authorized Unreal Engine 5.6 Linux installation.' >&2
        exit 1
    fi
    echo 'Unreal toolchain probe skipped. Set UE_ROOT and use --require-ue to require it.'
    exit 0
fi

engine="$(cd -- "$UE_ROOT/Engine" && pwd -P)"
python3 - "$engine/Build/Build.version" <<'PY'
import json
import sys
from pathlib import Path

version = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
major, minor = version["MajorVersion"], version["MinorVersion"]
if (major, minor) != (5, 6):
    sys.exit(f"Expected Unreal Engine 5.6, found {major}.{minor}")
print(f"Unreal Engine version: {major}.{minor}.{version['PatchVersion']}")
PY

for executable in Binaries/Linux/UnrealEditor Build/BatchFiles/Linux/Build.sh Build/BatchFiles/RunUAT.sh; do
    if [[ ! -x "$engine/$executable" ]]; then
        printf 'Missing Unreal executable: %s\n' "$engine/$executable" >&2
        exit 1
    fi
done

probe_dir="$(mktemp -d)"
trap 'rm -rf -- "$probe_dir"' EXIT
"$engine/Build/BatchFiles/Linux/Build.sh" -Mode=QueryTargets \
    "-Project=$(cd -- "$game_root" && pwd -P)/Eidolon.uproject" \
    "-Output=$probe_dir/targets.json"
test -s "$probe_dir/targets.json"
"$engine/Build/BatchFiles/RunUAT.sh" -List
echo 'UnrealBuildTool and Unreal Automation Tool responded. Compilation and editor launch are separate checks.'
