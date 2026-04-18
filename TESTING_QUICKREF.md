# ⚡ FreeFace Testing Quick Reference

**Status:** ✅ Unit tests configured and ready

---

## 🚀 Quick Commands

```bash
# Build C++ engine
make

# Run all default tests (non-interactive)
make test

# Run specific tests
make test-engine       # C++ engine validation
make test-camera       # Webcam check
make test-mediapipe    # Face mesh processing
make test-os           # OS mouse/keyboard control
make test-gaze         # Live gaze tracking (10s, interactive)
make test-blink        # Blink detection (15s, interactive)
make test-voice        # Voice recognition (interactive)
make test-keyboard     # Virtual keyboard UI (5s, interactive)

# Or run directly
python3 test.py                    # all non-interactive tests
python3 test.py gaze               # specific test
```

---

## 📋 Default Test Suite (Auto-Run)

| Test | Status | Requires |
|------|--------|----------|
| C++ Engine | ✓ | `make` (builds engine.so) |
| Webcam | ✓ | Webcam connected |
| MediaPipe | ✓ | `pip install mediapipe` |
| OS Control | ✓ | `pip install pynput` |

**Duration:** ~5 seconds

---

## 🎯 Interactive Tests (Run Manually)

| Test | Duration | What It Does |
|------|----------|-------------|
| Gaze | 10s | Tracks eye gaze in real-time |
| Blink | 15s | Counts blinks + detects rapid blinks |
| Voice | ~10s | Listens and transcribes speech |
| Keyboard | 5s | Shows virtual on-screen keyboard |

---

## 📁 Project Structure

```
/data/programing/Help Snehal/
├── Makefile              ← Build & test targets
├── test.py               ← Test suite
├── TESTING.md            ← Full documentation (THIS FILE)
├── requirements.txt      ← Dependencies
├── cpp/                  ← C++ source
│   ├── include/          ← Headers
│   └── src/              ← Implementations
└── python/               ← Python modules
    ├── main.py           ← Application entry point
    ├── engine_bridge.py  ← C++ interface
    ├── face_mesh.py      ← MediaPipe wrapper
    └── ...
```

---

## ✅ Test Results

### ✓ All Pass
```bash
$ make test
✓ PASS  engine
✓ PASS  camera
✓ PASS  mediapipe
✓ PASS  os

✓ PASS  All core components working!
     Run: python3 python/main.py
```

→ **Next:** Run the main application

### ✗ Some Fail
Check [TESTING.md](TESTING.md#-debugging-failed-tests) debugging section for each failing test.

---

## 🔧 Setup (First Time Only)

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Build C++ engine
make clean
make

# 3. Run verification
make test
```

---

## 🐛 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| `engine.so not found` | Run `make` to build |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Webcam fails | Check `/dev/video*` devices |
| Voice fails | Check microphone + internet |
| Mouse won't move | Use `sudo python3 test.py os` |

---

## 📚 Full Documentation

See [TESTING.md](TESTING.md) for:
- ✓ Detailed test descriptions
- ✓ Complete troubleshooting guide
- ✓ Test development workflow
- ✓ CI/CD integration examples

---

**Last Updated:** April 17, 2026 | **Status:** Ready for Testing ✅
