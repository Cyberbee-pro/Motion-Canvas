# 👁 FreeFace — Hands-Free Assistive OS Controller

Control your laptop entirely with your face. No hands needed.
Built for people with ALS, spinal cord injury, cerebral palsy, and other mobility impairments.

---

## What It Does

| Input | Action |
|---|---|
| 👁️ Gaze direction | Moves mouse cursor |
| 😑 Slow blink | Left click |
| 😮 Double blink | Double click |
| 🤨 Eyebrow raise | Right click |
| ⏱️ Stare 2.5s (dwell) | Auto-click (for users who can't blink) |
| ↓ Head nod down | Scroll down |
| ↑ Head nod up | Scroll up |
| 😮 Mouth wide open | Open/close virtual keyboard |
| 🗣️ Voice | Type text / keyboard shortcuts |

---

## File Structure

```
freeface/
├── cpp/
│   ├── include/
│   │   ├── LandmarkFrame.h     ← 478-point face data structure
│   │   ├── Filters.h           ← KalmanFilter<T>, CircularBuffer<T>
│   │   ├── Detectors.h         ← Abstract FaceController + 5 derived classes
│   │   └── FreeFaceEngine.h    ← Main orchestrator
│   ├── src/
│   │   ├── Detectors.cpp       ← All 5 detector implementations
│   │   └── FreeFaceEngine.cpp  ← Engine + profile management
│   └── engine_api.cpp          ← C API for Python ctypes bridge
├── python/
│   ├── main.py                 ← Entry point + threading
│   ├── engine_bridge.py        ← Python ctypes wrapper for C++ .so
│   ├── face_mesh.py            ← MediaPipe FaceMesh wrapper
│   ├── os_control.py           ← OS mouse/keyboard via pynput
│   ├── voice_control.py        ← Speech recognition thread
│   └── virtual_keyboard.py    ← On-screen gaze-navigable keyboard
├── frontend/
│   └── dashboard.html          ← Live monitoring UI (open in browser)
├── profiles/                   ← Saved calibration profiles
├── requirements.txt
├── Makefile
└── setup.sh
```

---

## Setup (Step by Step)

### Requirements
- Linux or macOS (Windows: use WSL2)
- Python 3.10+
- g++ with C++17 support
- A webcam

### Step 1 — Install Python dependencies
```bash
pip install -r requirements.txt
```
If pyaudio fails on Linux:
```bash
sudo apt install portaudio19-dev
pip install pyaudio
```

### Step 2 — Build the C++ engine
```bash
make
```
This creates `engine.so` (the compiled C++ gesture classifier).

You should see: `✓ Built engine.so — ready for Python`

### Step 3 — Run FreeFace
```bash
cd python
python3 main.py
```

---

## How to Test It Yourself

### Test 1 — Calibration
On first run, a camera window opens.  
Look at the **center of your screen** and keep your face neutral.  
Hold for **3 seconds** — the blue bar fills up.  
✓ Calibration done. Profile saved.

### Test 2 — Gaze (cursor movement)
Look left → cursor moves left  
Look right → cursor moves right  
Look up → cursor moves up  
Look down → cursor moves down

Tip: move your eyes, not your whole head.

### Test 3 — Blink to click
Open a text editor. Gaze at it.  
Blink **slowly and deliberately** (not a natural fast blink) → left click  
The cursor should click where you're looking.

### Test 4 — Double click
Blink **twice quickly** (within ~0.6 seconds) → double click

### Test 5 — Scroll
**Nod your head down** → page scrolls down  
**Nod your head up** → page scrolls up

### Test 6 — Virtual keyboard
**Open your mouth wide** for 1 second → virtual keyboard appears  
Gaze at a letter → it highlights blue  
Blink → letter is typed  
**Open mouth wide again** → keyboard closes

### Test 7 — Voice
Say: **"press enter"** → Enter key pressed  
Say: **"scroll down"** → page scrolls  
Say: **"hello world"** → types "hello world"

### Test 8 — Dwell click (for users who can't blink)
Press **C** in camera window → recalibrate  
Then enable Dwell in the dashboard  
Gaze at any point for 2.5 seconds → auto-click fires

### Test 9 — Dashboard
Open `frontend/dashboard.html` in your browser  
It shows gaze position, blink count, action log, eye strain monitor  
Works in demo mode even without the engine running

---

## Recalibration
Press **C** in the camera window at any time.  
Useful if you move your chair, lighting changes, or accuracy degrades.

## Quit
Press **Q** in the camera window.

---

## OOP Concepts Covered

| Concept | Location |
|---|---|
| Abstract class + pure virtuals | `FaceController` in `Detectors.h` |
| Inheritance (5 derived classes) | `GazeTracker`, `BlinkDetector`, `HeadPoseEstimator`, `ExpressionEngine`, `DwellClicker` |
| Templates | `KalmanFilter<T>`, `CircularBuffer<T>` in `Filters.h` |
| Operator overloading | `LandmarkFrame[]`, `Point3D +−*==`, `FaceController+` |
| Exception handling | Out-of-range landmark access, bad webcam, corrupt profiles |
| Encapsulation | All math hidden behind clean interfaces |
| File I/O | Binary profile save/load in `FreeFaceEngine.cpp` |
| STL | `vector`, `array`, `unique_ptr`, `memory` |

---

## Optimisations Applied

| Problem | Solution |
|---|---|
| Jittery gaze | `KalmanFilter<float>` on x/y each frame |
| False blink triggers | EAR averaged over 8-frame buffer |
| False gesture triggers | `CircularBuffer` majority vote |
| CPU overload | Process every 2nd frame (15fps is enough) |
| Midas Touch problem | Gaze moves cursor, blink confirms — never combined |
| Slow OS calls | `pynput` direct system calls (not pyautogui) |
| Mouse jitter | Weighted interpolation: 70% old pos + 30% target |

---

## Hardware Requirements

| Component | Minimum |
|---|---|
| Camera | Any 720p webcam |
| CPU | Intel i5 / AMD Ryzen 5 (2018+) |
| RAM | 4GB |
| GPU | Not required |
| Internet | Only for voice (Google API); can use offline Whisper |

---

## Why This Matters

| Tool | Cost | Hardware needed |
|---|---|---|
| Tobii Eye Tracker | ₹80,000+ | Dedicated device |
| Grid 3 AAC software | ₹60,000/year | Special device |
| **FreeFace** | **₹0** | **Your existing webcam** |
