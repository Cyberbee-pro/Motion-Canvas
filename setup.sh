#!/bin/bash
# setup.sh — FreeFace one-command setup
# Run: bash setup.sh

set -e
echo ""
echo "══════════════════════════════════════"
echo "  FreeFace — Setup"
echo "══════════════════════════════════════"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
  echo "ERROR: Python 3 not found. Install from https://python.org"
  exit 1
fi

# Check g++
if ! command -v g++ &>/dev/null; then
  echo "ERROR: g++ not found."
  echo "  Ubuntu/Debian: sudo apt install g++"
  echo "  macOS:         xcode-select --install"
  exit 1
fi

echo "✓ Python and g++ found"
echo ""

# Install Python deps
echo "Installing Python dependencies..."
pip3 install -r requirements.txt
echo "✓ Python dependencies installed"
echo ""

# Build C++ engine
echo "Building C++ engine..."
make
echo "✓ C++ engine built (engine.so)"
echo ""

# Create profiles directory
mkdir -p profiles
echo "✓ Profiles directory ready"
echo ""

echo "══════════════════════════════════════"
echo "  Setup complete!"
echo ""
echo "  To run FreeFace:"
echo "  cd python && python3 main.py"
echo ""
echo "  Controls:"
echo "  Q        → quit"
echo "  C        → recalibrate"
echo ""
echo "  On first run, look at screen center"
echo "  for 3 seconds to calibrate."
echo "══════════════════════════════════════"
echo ""
