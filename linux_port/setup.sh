#!/bin/bash
# setup.sh -- FreeFace one-command setup
# Run: bash setup.sh

set -e

echo ""
echo "======================================"
echo "  FreeFace Setup"
echo "======================================"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: Python 3 not found. Install from https://python.org"
  exit 1
fi

if ! command -v g++ >/dev/null 2>&1; then
  echo "ERROR: g++ not found."
  echo "  Ubuntu/Debian: sudo apt install g++"
  echo "  macOS:         xcode-select --install"
  exit 1
fi

echo "Python and g++ found"

PY_VER=$(python3 - <<'PY'
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)
echo "Detected Python ${PY_VER}"
case "$PY_VER" in
  3.13|3.14|3.15)
    echo "WARN: MediaPipe and PyAudio can be less reliable on Python ${PY_VER}."
    echo "      FreeFace face tracking currently needs Python 3.10-3.12 on Linux."
    echo "      Newer Python versions only get MediaPipe wheels without mp.solutions.face_mesh."
    ;;
esac

if [ "$(uname -s)" = "Linux" ]; then
  echo ""
  echo "Linux notes:"
  echo "  - Global mouse/keyboard control usually needs an active desktop session."
  echo "  - On Wayland, pynput may be restricted by compositor permissions."
  echo "  - If PyAudio fails, install PortAudio dev libs (for example: portaudio19-dev)."
  echo "  - If tkinter is missing, install your distro's python3-tk package."
fi

echo ""
echo "Preparing virtual environment..."
if [ ! -f "venv/bin/activate" ]; then
  python3 -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "Upgrading pip tooling..."
python -m pip install --retries 8 --timeout 120 --upgrade pip setuptools wheel

echo ""
echo "Installing core Python dependencies..."
python -m pip install --retries 8 --timeout 120 -r requirements.txt
echo "Core dependencies installed"

echo ""
echo "Installing optional voice dependencies..."
if python -m pip install --retries 8 --timeout 120 -r requirements-voice.txt; then
  echo "Voice dependencies installed"
else
  echo "WARN: Optional voice dependencies could not be installed."
  echo "      Voice control will be disabled until PyAudio is available."
fi

echo ""
echo "Building C++ engine..."
make
echo "C++ engine built (engine.so)"

mkdir -p profiles
echo "Profiles directory ready"

echo ""
echo "======================================"
echo "  Setup complete"
echo ""
echo "  To run FreeFace:"
echo "  source venv/bin/activate"
echo "  cd python && python main.py"
echo ""
echo "  Controls:"
echo "  Q -> quit"
echo "  C -> recalibrate"
echo "======================================"
