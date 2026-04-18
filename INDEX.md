# 📖 FreeFace Documentation Index

**Project:** FreeFace — Hands-Free Assistive OS Controller  
**Status:** ✅ Unit Testing Complete  
**Last Updated:** April 17, 2026

---

## 🚀 Start Here

### First Time Setup
1. Read: [SETUP_SUMMARY.md](SETUP_SUMMARY.md) ← What was done and why
2. Run: `pip install -r requirements.txt`
3. Build: `make` or `make clean && make`
4. Test: `make test`

### Quick Commands
```bash
make test          # Run all tests
make test-engine   # Test C++ engine
make test-gaze     # Live gaze tracking
python3 test.py    # Direct test run
```

---

## 📚 Documentation Files

### Testing Documentation
| File | Purpose | Size | Read Time |
|------|---------|------|-----------|
| [TESTING.md](TESTING.md) | **Complete testing guide** with all tests, troubleshooting, and examples | 515 lines | 15 min |
| [TESTING_QUICKREF.md](TESTING_QUICKREF.md) | Quick reference with commands and troubleshooting matrix | ~100 lines | 2 min |
| [SETUP_SUMMARY.md](SETUP_SUMMARY.md) | What was set up, file changes, and verification checklist | ~200 lines | 5 min |
| **This File** | Documentation index and navigation guide | — | 2 min |

### Project Documentation
| File | Purpose |
|------|---------|
| [README.md](README.md) | Main project overview and features |
| [Makefile](Makefile) | Build system with test targets |
| [requirements.txt](requirements.txt) | Python dependencies |

---

## 🧪 Test Suite Overview

### Automated Tests (Default - Run with `make test`)
```
✓ test_engine    → C++ engine library validation
✓ test_camera    → Webcam availability check
✓ test_mediapipe → Face mesh processing
✓ test_os        → OS mouse/keyboard control
```

**Duration:** ~5 seconds | **Requires:** No user interaction

### Interactive Tests (Run individually)
```
✓ test_gaze      → Live gaze tracking (10s)
✓ test_blink     → Blink detection (15s)
✓ test_voice     → Voice recognition (~10s)
✓ test_keyboard  → Virtual keyboard (5s)
```

**Duration:** Individual tests | **Requires:** User interaction

---

## 📁 Project Structure

```
/data/programing/Help Snehal/
│
├── 📖 DOCUMENTATION
│   ├── README.md              ← Main project guide
│   ├── TESTING.md             ← Full testing docs (READ THIS)
│   ├── TESTING_QUICKREF.md    ← Quick commands
│   ├── SETUP_SUMMARY.md       ← Setup details
│   └── INDEX.md               ← This file
│
├── 🔨 BUILD & TEST
│   ├── Makefile               ← Build & test system
│   ├── test.py                ← Test suite (8 tests)
│   ├── requirements.txt       ← Python deps
│   ├── setup.sh               ← Initial setup
│   └── engine.so              ← Compiled C++ (after build)
│
├── 💻 C++ ENGINE
│   └── cpp/
│       ├── include/           ← Headers
│       │   ├── LandmarkFrame.h
│       │   ├── Filters.h
│       │   ├── Detectors.h
│       │   └── FreeFaceEngine.h
│       └── src/               ← Implementations
│           ├── Detectors.cpp
│           ├── FreeFaceEngine.cpp
│           └── engine_api.cpp
│
├── 🐍 PYTHON APPLICATION
│   └── python/
│       ├── main.py            ← App entry point
│       ├── engine_bridge.py   ← C++ wrapper
│       ├── face_mesh.py       ← MediaPipe
│       ├── os_control.py      ← Mouse/keyboard
│       ├── dashboard_server.py ← Web UI
│       ├── voice_control.py   ← Speech recognition
│       ├── virtual_keyboard.py ← On-screen keyboard
│       └── windows_compat.py  ← Windows support
│
├── 🌐 FRONTEND
│   └── frontend/
│       └── dashboard.html     ← Web dashboard
│
└── 👤 USER PROFILES
    └── profiles/              ← Calibration data
```

---

## ⚡ Common Tasks

### Build the Project
```bash
cd "/data/programing/Help Snehal"
make clean        # Clean previous builds
make              # Build C++ engine
```

### Run Unit Tests
```bash
make test                 # All default tests
make test-gaze            # Single interactive test
python3 test.py blink     # Direct test call
```

### Debug a Failing Test
1. Open [TESTING.md](TESTING.md)
2. Find the test section (e.g., "Gaze Tracking Test")
3. See "Troubleshooting" subsection

### Update Test Coverage
1. Edit [test.py](test.py)
2. Add new `test_*()` function
3. Add to `TESTS` dictionary
4. Document in [TESTING.md](TESTING.md)

### Run the Application
```bash
# After tests pass:
python3 python/main.py
# or
cd python && python3 main.py
```

---

## 🔗 Cross-References

### By Use Case

**"I want to understand the tests"**
→ Start with [TESTING_QUICKREF.md](TESTING_QUICKREF.md), then read [TESTING.md](TESTING.md)

**"A test is failing"**
→ Find the test in [TESTING.md](TESTING.md#-debugging-failed-tests) and check troubleshooting

**"I want to see what changed"**
→ Read [SETUP_SUMMARY.md](SETUP_SUMMARY.md#-files-modifiedcreated)

**"I want quick commands"**
→ Check [TESTING_QUICKREF.md](TESTING_QUICKREF.md#-quick-commands)

**"I need to build/compile"**
→ See [TESTING.md](TESTING.md#-setup--build) section

**"I want to add a test"**
→ Read [TESTING.md](TESTING.md#-test-development-workflow)

### By Component

**Engine (C++)**
- Build: [Makefile](Makefile)
- Test: [test.py](test.py) → `test_engine()`
- Docs: [TESTING.md](TESTING.md#1-c-engine-test-test_engine)

**Webcam**
- Code: [python/main.py](python/main.py)
- Test: [test.py](test.py) → `test_camera()`
- Docs: [TESTING.md](TESTING.md#2-webcam-test-test_camera)

**Face Detection**
- Code: [python/face_mesh.py](python/face_mesh.py)
- Test: [test.py](test.py) → `test_mediapipe()`
- Docs: [TESTING.md](TESTING.md#3-mediapipe-facemesh-test-test_mediapipe)

**Gaze Tracking**
- Code: [python/engine_bridge.py](python/engine_bridge.py)
- Test: [test.py](test.py) → `test_gaze_live()`
- Docs: [TESTING.md](TESTING.md#4-live-gaze-tracking-test-test_gaze---interactive)

**Voice Control**
- Code: [python/voice_control.py](python/voice_control.py)
- Test: [test.py](test.py) → `test_voice()`
- Docs: [TESTING.md](TESTING.md#6-voice-recognition-test-test_voice)

---

## 📊 Testing Coverage

```
Component          | Status | Type | Documentation
─────────────────────────────────────────────────
✓ C++ Engine       | ✅    | Unit | TESTING.md #1
✓ Webcam           | ✅    | Integ | TESTING.md #2
✓ MediaPipe       | ✅    | Unit | TESTING.md #3
✓ Gaze Tracking   | ✅    | Func | TESTING.md #4
✓ Blink Detection | ✅    | Func | TESTING.md #5
✓ Voice Recog     | ✅    | Integ | TESTING.md #6
✓ Virtual Keyboard | ✅   | UI   | TESTING.md #7
✓ OS Control      | ✅    | Sys  | TESTING.md #8
```

---

## 🎯 Next Steps

1. **Run Tests:** `make test`
2. **Review Results:** Check output for ✓ or ✗
3. **If Passing:** Run app with `python3 python/main.py`
4. **If Failing:** See [TESTING.md](TESTING.md#-debugging-failed-tests)
5. **For Details:** Browse documentation files above

---

## 📞 Help & Support

| Question | Answer |
|----------|--------|
| How do I run tests? | `make test` — See [TESTING_QUICKREF.md](TESTING_QUICKREF.md) |
| What if a test fails? | Check [TESTING.md](TESTING.md#-debugging-failed-tests) |
| How do I build the engine? | `make` — See [TESTING.md](TESTING.md#-setup--build) |
| How do I add a test? | See [TESTING.md](TESTING.md#-test-development-workflow) |
| What changed? | See [SETUP_SUMMARY.md](SETUP_SUMMARY.md) |

---

## ✅ Setup Verification Checklist

- [x] Project structure organized (cpp/, python/, frontend/, profiles/)
- [x] C++ files moved to correct locations
- [x] Python modules moved to python/ directory
- [x] Makefile updated with test targets
- [x] 8 test functions implemented and documented
- [x] Comprehensive documentation created
- [x] Quick reference guide added
- [x] Setup summary documented
- [x] This index file created

---

**Welcome to FreeFace! 👁️**  
Ready to get started? Run `make test` to verify everything!

```bash
cd "/data/programing/Help Snehal"
make test
```

**Last Updated:** April 17, 2026  
**Status:** ✅ ALL SYSTEMS READY
