# FreeFace Working Notes

This file explains how the whole FreeFace project works from source code to runtime behavior. It covers every readable source file in the workspace, the main functions/classes, the detector algorithms, data flow, build/test setup, dashboard behavior, and the technical details that matter when maintaining or extending the project.

`engine.so` and `profiles/current.profile` are binary files. Their readable behavior is documented from the C++ source, exported symbols, and binary layout observations.

## 1. Project Purpose

FreeFace is a hands-free assistive operating-system controller. It uses a webcam to read facial landmarks, sends those landmarks into a native C++ detection engine, converts detector outputs into actions, and then performs those actions on the OS.

The intended controls are:

| Input | Output |
| --- | --- |
| Gaze direction | Move mouse cursor |
| Slow blink | Left click |
| Two blinks close together | Double click |
| Eyebrow raise | Right click |
| Stable gaze dwell | Automatic click |
| Head nod down | Scroll down |
| Head nod up | Scroll up |
| Head turn right | Escape |
| Head turn left | Enter |
| Mouth open | Toggle virtual keyboard |
| Voice command/text | Press keys, scroll, or type text |

## 2. Repository Map

| Path | Role |
| --- | --- |
| `README.md` | Main feature and setup overview. |
| `INDEX.md` | Navigation index for setup/testing docs. |
| `SETUP_SUMMARY.md` | Summary of project organization and testing setup. |
| `TESTING.md` | Full test guide. |
| `TESTING_QUICKREF.md` | Short test command reference. |
| `Makefile` | C++ build and test targets. |
| `setup.sh` | One-command virtualenv/dependency/build setup script. |
| `requirements.txt` | Core Python dependencies. |
| `requirements-voice.txt` | Optional PyAudio dependency for voice. |
| `test.py` | Component test runner. |
| `engine.so` | Compiled native engine shared library for this machine. |
| `profiles/current.profile` | Binary persisted accessibility profile. |
| `cpp/include/*.h` | C++ engine public/internal headers. |
| `cpp/src/*.cpp` | C++ engine implementations and C API. |
| `python/*.py` | Python runtime, bridge, camera, OS control, dashboard, voice, keyboard. |
| `frontend/dashboard.html` | Browser dashboard UI. |
| `frontend/dashboard-2.html` | Exact duplicate of `dashboard.html`. |

## 3. End-to-End Runtime Flow

1. `python/main.py` starts the application.
2. It resolves the project root, loads `engine.so` through `python/engine_bridge.py`, and creates a native `FreeFaceEngine`.
3. It loads `profiles/current.profile` if present, then starts a live calibration cycle anyway.
4. It creates:
   - `FaceMesh` for MediaPipe landmark extraction.
   - `OSController` for real mouse/keyboard output.
   - `VirtualKeyboard` for gaze-accessible typing.
   - `VoiceControl` in a daemon thread if enabled.
   - `dashboard_server` in a daemon thread if enabled.
5. The OpenCV camera loop captures webcam frames, flips them horizontally, and asks `FaceMesh.process()` for landmarks and an annotated frame.
6. When landmarks exist, `engine.process(landmarks)` flattens them and calls the native `ff_process()` function.
7. C++ converts the flat float array into a `LandmarkFrame`, optionally calibrates, then runs detectors.
8. The returned action is parsed back into a Python `Action`.
9. Python routes the action:
   - Gaze updates move the OS cursor, update virtual keyboard hover state, and push dashboard gaze.
   - `OPEN_KB` toggles the virtual keyboard.
   - Blink/dwell clicks type the highlighted virtual key when the keyboard is visible.
   - Other actions go to `OSController`.
10. Every 30 frames, runtime stats are pushed to the dashboard.
11. On quit, the app closes windows, releases the camera, closes MediaPipe, saves the profile, and exits.

## 4. Native C++ Engine

### 4.1 `cpp/include/LandmarkFrame.h`

#### `struct Point3D`

Represents one MediaPipe landmark point.

Fields:

| Field | Meaning |
| --- | --- |
| `float x` | Normalized x coordinate. |
| `float y` | Normalized y coordinate. |
| `float z` | Relative depth coordinate. |

Functions/operators:

| Function | Detail |
| --- | --- |
| `Point3D()` | Default constructor initializes coordinates to zero. |
| `Point3D(float x, float y, float z)` | Constructs a point from coordinates. |
| `operator+` | Adds two points component-wise. |
| `operator-` | Subtracts two points component-wise. |
| `operator*` | Multiplies all coordinates by a scalar. |
| `operator==` | Exact coordinate equality comparison. |
| `norm()` | Euclidean length: `sqrt(x*x + y*y + z*z)`. |
| `dist(const Point3D& o)` | Euclidean distance to another point. |

#### `class LandmarkFrame`

Wraps one frame of face landmarks.

Important details:

| Item | Detail |
| --- | --- |
| `COUNT` | Fixed at `478`, matching MediaPipe FaceMesh with iris refinement. |
| `pts` | `std::array<Point3D, 478>`, so storage is fixed-size and heap-free. |
| `valid_` | Becomes true when at least one point is set. |

Functions:

| Function | Detail |
| --- | --- |
| `set(int i, float x, float y, float z)` | Stores landmark `i`; throws `std::out_of_range` for invalid index; marks frame valid. |
| `operator[](int i) const` | Read-only point access; throws `std::out_of_range` for invalid index. |
| `isValid() const` | Returns whether any point was set. |
| `invalidate()` | Marks frame invalid. |

MediaPipe indices stored as constants:

| Constant | Index | Use |
| --- | ---: | --- |
| `L_EYE_TOP` | 159 | Left eye top. |
| `L_EYE_BOT` | 145 | Left eye bottom. |
| `L_EYE_IN` | 133 | Left inner corner. |
| `L_EYE_OUT` | 33 | Left outer corner. |
| `R_EYE_TOP` | 386 | Right eye top. |
| `R_EYE_BOT` | 374 | Right eye bottom. |
| `R_EYE_IN` | 362 | Right inner corner. |
| `R_EYE_OUT` | 263 | Right outer corner. |
| `L_IRIS` | 468 | Left iris center/iris landmark start. |
| `R_IRIS` | 473 | Right iris center/iris landmark start. |
| `NOSE_TIP` | 1 | Nose tip for head pose. |
| `FOREHEAD` | 10 | Forehead reference. |
| `CHIN` | 152 | Chin reference. |
| `L_CHEEK` | 234 | Left cheek reference. |
| `R_CHEEK` | 454 | Right cheek reference. |
| `MOUTH_TOP` | 13 | Upper lip. |
| `MOUTH_BOT` | 14 | Lower lip. |
| `MOUTH_L` | 61 | Left mouth corner. |
| `MOUTH_R` | 291 | Right mouth corner. |
| `L_BROW` | 105 | Left eyebrow. |
| `R_BROW` | 334 | Right eyebrow. |

### 4.2 `cpp/include/Filters.h`

#### `template<class T> class KalmanFilter`

One-dimensional discrete Kalman filter used for smoothing noisy measurements such as gaze coordinates, head pose, and eye aspect ratio style values.

State:

| Field | Meaning |
| --- | --- |
| `estimate_` | Current filtered value. |
| `errorCov_` | Error covariance. |
| `processNoise_` | Q value; higher values follow motion faster. |
| `measureNoise_` | R value; higher values smooth more but add lag. |
| `init_` | Tracks whether the first measurement has initialized the estimate. |

Functions:

| Function | Detail |
| --- | --- |
| `KalmanFilter(T Q, T R)` | Constructor, defaults to `Q=1e-3`, `R=5e-2`. |
| `update(T measurement)` | Initializes on first measurement; otherwise predicts covariance, computes Kalman gain, updates estimate and covariance, and returns filtered value. |
| `value() const` | Returns current estimate. |
| `reset()` | Clears initialization and resets covariance to 1. |
| `setNoise(T Q, T R)` | Changes process/measurement noise. |

#### `template<class T, int N> class CircularBuffer`

Fixed-size ring buffer with no heap allocation.

State:

| Field | Meaning |
| --- | --- |
| `data_` | `std::array<T, N>` backing storage. |
| `head_` | Next write position. |
| `count_` | Number of valid entries, max `N`. |

Functions:

| Function | Detail |
| --- | --- |
| `push(const T& v)` | Writes a value at the head, wraps around, increments count until full. |
| `operator[](int i) const` | Newest-first access: `buf[0]` is newest. |
| `size() const` | Number of valid entries. |
| `full() const` | True when `count_ == N`. |
| `empty() const` | True when `count_ == 0`. |
| `clear()` | Resets head and count. |
| `majority() const` | Returns the most frequent value, used for gesture debouncing. |
| `average() const` | Numeric rolling average. Requires `T` to support `+` and scalar `*`. |
| `all(Pred p) const` | Returns true when all entries match a predicate and the buffer is non-empty. |

### 4.3 `cpp/include/Detectors.h` and `cpp/src/Detectors.cpp`

#### `enum class ActionType`

Must stay synchronized with Python `ActionType` in `engine_bridge.py`.

| Value | Name | Meaning |
| ---: | --- | --- |
| 0 | `NONE` | No action. |
| 1 | `MOUSE_MOVE` | Move cursor to normalized `x,y`. |
| 2 | `LEFT_CLICK` | Left mouse click. |
| 3 | `RIGHT_CLICK` | Right mouse click. |
| 4 | `DOUBLE_CLICK` | Double left click. |
| 5 | `SCROLL_UP` | Scroll up. |
| 6 | `SCROLL_DOWN` | Scroll down. |
| 7 | `KEY_ENTER` | Press Enter. |
| 8 | `KEY_ESCAPE` | Press Escape. |
| 9 | `KEY_SPACE` | Press Space. |
| 10 | `DWELL_CLICK` | Click from gaze dwell. |
| 11 | `OPEN_KB` | Toggle virtual keyboard. |

#### `struct Action`

Native action returned by detectors.

Fields:

| Field | Meaning |
| --- | --- |
| `type` | `ActionType`. |
| `x` | Normalized screen x for gaze/dwell actions. |
| `y` | Normalized screen y for gaze/dwell actions. |
| `magnitude` | Scroll intensity or other action magnitude. |
| `label` | C string label for HUD/dashboard. |

Function:

| Function | Detail |
| --- | --- |
| `isNone() const` | True when type is `ActionType::NONE`. |

#### `class FaceController`

Abstract base class for all detectors.

State:

| Field | Meaning |
| --- | --- |
| `enabled_` | Detector enabled/disabled. |
| `sensitivity_` | Multiplier or inverse threshold factor depending on detector. |

Virtual functions implemented by each detector:

| Function | Detail |
| --- | --- |
| `process(const LandmarkFrame&)` | Produces an `Action` for one frame. |
| `getName() const` | Detector name. |
| `calibrate(const LandmarkFrame&)` | Updates detector calibration baseline. |
| `reset()` | Clears detector runtime state. |

Common functions:

| Function | Detail |
| --- | --- |
| `setEnabled(bool)` | Enables/disables detector. |
| `setSensitivity(float)` | Sets detector sensitivity. |
| `isEnabled() const` | Returns enabled state. |
| `getSensitivity() const` | Returns sensitivity value. |
| `operator+(const FaceController&) const` | Returns a pipeline string such as `GazeTracker -> BlinkDetector` except the source uses a unicode arrow. |

#### `class GazeTracker`

Maps average iris location to normalized screen coordinates.

State:

| Field | Meaning |
| --- | --- |
| `kx_`, `ky_` | Kalman filters for x/y gaze output. |
| `xMin_`, `xMax_`, `yMin_`, `yMax_` | Calibration bounds used for mapping iris position to screen position. |

Functions:

| Function | Detail |
| --- | --- |
| `mapAxis(float v, float lo, float hi) const` | Returns clamped `(v - lo) / (hi - lo)`; if `hi <= lo`, returns center `0.5`. |
| `process(const LandmarkFrame&)` | Averages left/right iris x and y; maps through calibration bounds; applies sensitivity around center; clamps to `[0,1]`; smooths with Kalman filters; returns `MOUSE_MOVE` labeled `GAZE_MOVE`. |
| `calibrate(const LandmarkFrame&)` | Uses eye corners and eyelid landmarks to set gaze mapping bounds. |
| `reset()` | Resets filters and restores default bounds `0.33..0.67`. |
| `lastX() const` | Current filtered x estimate. |
| `lastY() const` | Current filtered y estimate. |

Calibration details:

- `xMin_ = min(left outer eye, right outer eye) - 0.04`.
- `xMax_ = max(left inner eye, right inner eye) + 0.04`.
- `yMin_ = left eye top y - 0.07`.
- `yMax_ = left eye bottom y + 0.10`.

#### `class BlinkDetector`

Detects deliberate blinks using Eye Aspect Ratio.

State:

| Field | Meaning |
| --- | --- |
| `earBuf_` | 8-frame circular buffer of EAR values. |
| `threshold_` | EAR closed threshold, default `0.22`. |
| `baseline_` | Calibrated open-eye EAR, default `0.30`. |
| `closed_` | Whether the previous state was closed. |
| `closedFor_` | Number of frames eye has been closed. |
| `sinceClick_` | Frames since last click, used for double-click detection. |

Functions:

| Function | Detail |
| --- | --- |
| `ear(const LandmarkFrame& f, bool left) const` | Computes vertical eyelid distance divided by horizontal eye-corner distance for one eye. |
| `process(const LandmarkFrame&)` | Pushes averaged two-eye EAR into buffer; smooths using average when buffer is full; detects open-to-closed and closed-to-open transitions; returns `LEFT_CLICK` or `DOUBLE_CLICK`. |
| `calibrate(const LandmarkFrame&)` | Pushes current EAR; once buffer is full, sets `baseline_` to average and `threshold_` to `baseline_ * 0.72`. |
| `reset()` | Clears buffer and blink state; resets `sinceClick_` to 999. |

Blink timing:

- `closedFor_ >= 2 && closedFor_ <= 25` is accepted as a blink.
- More than 25 closed frames is treated as long eye closure/fatigue and ignored.
- If a blink completes less than 18 frames after the previous click, it becomes `DOUBLE_CLICK`; otherwise `LEFT_CLICK`.

#### `class HeadPoseEstimator`

Estimates head pitch/yaw using landmark ratios rather than a full PnP solve.

State:

| Field | Meaning |
| --- | --- |
| `pitchK_`, `yawK_` | Kalman filters for pitch/yaw. |
| `basePitch_`, `baseYaw_` | Neutral calibration baselines. |
| `calibrated_` | Head gestures are ignored until calibrated. |
| `actionBuf_` | 10-frame circular buffer for majority-vote debouncing. |

Functions:

| Function | Detail |
| --- | --- |
| `pitch(const LandmarkFrame&) const` | Computes nose y position normalized between forehead and chin. Positive delta means head down. |
| `yaw(const LandmarkFrame&) const` | Computes nose x offset from cheek midpoint normalized by cheek width. |
| `process(const LandmarkFrame&)` | Filters pitch/yaw; compares deltas to thresholds; majority-votes gesture code; returns scroll/key action. |
| `calibrate(const LandmarkFrame&)` | Sets filtered neutral pitch/yaw and marks calibrated. |
| `reset()` | Resets filters, action buffer, and calibrated flag. |

Thresholds and outputs:

| Condition | Code | Action |
| --- | ---: | --- |
| `dp > 0.07 / sensitivity` | 1 | `SCROLL_DOWN`, label `NOD_DOWN`, magnitude `abs(dp)*4`. |
| `dp < -0.07 / sensitivity` | 2 | `SCROLL_UP`, label `NOD_UP`, magnitude `abs(dp)*4`. |
| `dy > 0.07 / sensitivity` | 3 | `KEY_ESCAPE`, label `HEAD_RIGHT`. |
| `dy < -0.07 / sensitivity` | 4 | `KEY_ENTER`, label `HEAD_LEFT`. |

#### `class ExpressionEngine`

Detects mouth-open and eyebrow-raise expressions.

State:

| Field | Meaning |
| --- | --- |
| `baseMouth_` | Neutral mouth-open ratio, default `0.12`. |
| `baseBrow_` | Neutral brow distance, default `0.06`. |
| `calibrated_` | Set during calibration, but currently not checked in `process()`. |
| `exprBuf_` | 8-frame expression code buffer for majority voting. |

Functions:

| Function | Detail |
| --- | --- |
| `mouthRatio(const LandmarkFrame&) const` | Vertical lip gap divided by mouth width. |
| `browRaise(const LandmarkFrame&) const` | Average vertical distance between eyebrow landmarks and eye-top landmarks. |
| `process(const LandmarkFrame&)` | Computes mouth/brow ratios; pushes expression code; majority-votes; returns `OPEN_KB` or `RIGHT_CLICK`. |
| `calibrate(const LandmarkFrame&)` | Stores neutral mouth and brow ratios. |
| `reset()` | Clears expression buffer. |

Thresholds:

- Mouth threshold: `(baseMouth_ + 0.20) / sensitivity`.
- Brow threshold: `(baseBrow_ + 0.02) * sensitivity`.

Outputs:

| Code | Action |
| ---: | --- |
| 1 | `OPEN_KB`, label `MOUTH_OPEN->KB` in concept; source label uses a unicode arrow. |
| 2 | `RIGHT_CLICK`, label `BROW_RAISE->RC` in concept; source label uses a unicode arrow. |

#### `class DwellClicker`

Clicks automatically if gaze stays nearly still for long enough.

Constants:

| Constant | Value | Meaning |
| --- | ---: | --- |
| `DWELL_FRAMES` | 40 | About 2.7 seconds at 15 FPS. |
| `DWELL_RADIUS` | 0.025 | Normalized screen radius for stable gaze. |

State:

| Field | Meaning |
| --- | --- |
| `cx_`, `cy_` | Current dwell center. `-1` means uninitialized. |
| `count_` | Consecutive stable frames. |

Functions:

| Function | Detail |
| --- | --- |
| `feedGaze(float x, float y)` | Initializes dwell center; increments count if gaze remains within radius; otherwise resets count and moves center. |
| `process(const LandmarkFrame&)` | If enabled and `count_ >= DWELL_FRAMES`, resets count and returns `DWELL_CLICK` at the dwell center. |
| `calibrate(const LandmarkFrame&)` | No-op. |
| `reset()` | Clears count and center. |
| `progress() const` | Returns `count_ / DWELL_FRAMES`. |

### 4.4 `cpp/include/FreeFaceEngine.h` and `cpp/src/FreeFaceEngine.cpp`

#### `struct AccessibilityProfile`

Persisted per-user settings and calibration values.

Fields:

| Field | Default | Meaning |
| --- | --- | --- |
| `name[64]` | `default` | Profile name. |
| `gazeOn` | true | Gaze enabled. |
| `blinkOn` | true | Blink enabled. |
| `headOn` | true | Head gestures enabled. |
| `expressionOn` | true | Expressions enabled. |
| `dwellOn` | false | Dwell click disabled by default. |
| `voiceOn` | true | Voice intended enabled flag. Python currently controls voice separately. |
| `gazeSens` | 1.0 | Gaze sensitivity. |
| `blinkSens` | 1.0 | Blink sensitivity. |
| `headSens` | 1.0 | Head sensitivity. |
| `exprSens` | 1.0 | Expression sensitivity. |
| `earThreshold` | 0.22 | Stored threshold field. Current detector calibration does not write this field. |
| `nodThreshold` | 0.06 | Stored threshold field. Current detector uses hard-coded `0.07`. |
| `mouthThreshold` | 0.35 | Stored threshold field. Current detector computes from baseline. |
| `browThreshold` | 0.04 | Stored threshold field. Current detector computes from baseline. |
| `gazeXmin/Xmax/Ymin/Ymax` | `0.33/0.67/...` | Stored gaze bounds. Current `GazeTracker` calibration does not write these fields. |

Functions:

| Function | Detail |
| --- | --- |
| `save(const char* path) const` | Writes raw binary struct bytes to disk. |
| `load(const char* path)` | Reads raw binary struct bytes from disk. |

Important technical note: the profile saves raw C++ struct bytes. That is simple and fast, but not portable across compilers, architectures, field changes, or padding changes.

#### `class FreeFaceEngine`

Owns all detectors and defines the action priority.

State:

| Field | Meaning |
| --- | --- |
| `gaze_` | `unique_ptr<GazeTracker>`. |
| `blink_` | `unique_ptr<BlinkDetector>`. |
| `head_` | `unique_ptr<HeadPoseEstimator>`. |
| `expr_` | `unique_ptr<ExpressionEngine>`. |
| `dwell_` | `unique_ptr<DwellClicker>`. |
| `profile_` | Accessibility toggles and stored config. |
| `frameCount_` | Processed frame counter. |
| `blinkCount_` | Count of blink click events. |
| `noBlinkFrames_` | Frames since last blink, used for fatigue detection. |
| `calibrating_` | Whether calibration mode is active. |
| `calibFrames_` | Calibration frames collected. |
| `CALIB_TOTAL` | 45 frames, intended as about 3 seconds at 15 FPS. |

Functions:

| Function | Detail |
| --- | --- |
| `FreeFaceEngine()` | Constructs all detectors with `std::make_unique`. |
| `processFrame(const float* landmarks, int count)` | Main engine entry. Builds a frame, increments counters, calibrates if needed, otherwise runs detectors in priority order. |
| `startCalibration()` | Enables calibration, resets `calibFrames_`, resets gaze/blink/head/expression detectors. |
| `calibrating() const` | Returns calibration flag. |
| `calibProgress() const` | Returns collected calibration frames. |
| `calibTotal() const` | Returns `45`. |
| `loadProfile(const char* path)` | Reads binary profile, applies toggles/sensitivities. |
| `saveProfile(const char* path) const` | Writes binary profile. |
| `applyProfile()` | Applies profile toggles and sensitivity values to detectors. |
| `setGaze(bool)` | Enables gaze detector and updates profile. |
| `setBlink(bool)` | Enables blink detector and updates profile. |
| `setHead(bool)` | Enables head detector and updates profile. |
| `setExpression(bool)` | Enables expression detector and updates profile. |
| `setDwell(bool)` | Enables dwell detector and updates profile. |
| `frameCount() const` | Returns processed frame count. |
| `blinkCount() const` | Returns detected blink click count. |
| `isFatigued() const` | True when `noBlinkFrames_ > 300`, about 20 seconds at 15 FPS. |
| `dwellProgress() const` | Returns dwell click progress. |
| `buildFrame(const float* data, int count) const` | Converts flat `[x,y,z,...]` float array into a `LandmarkFrame`; uses up to 478 points. |
| `doCalibrate(const LandmarkFrame&)` | Sends frame to detector calibrators, increments progress, exits calibration after 45 frames, and saves profile to `profiles/current.profile`. |

Detector priority in `processFrame()`:

1. Invalid input returns `NONE`.
2. Build `LandmarkFrame`; exceptions are caught and return `NONE`.
3. Increment `frameCount_` and `noBlinkFrames_`.
4. If calibrating, call `doCalibrate()` and return `NONE` labeled `CALIBRATING`.
5. Run gaze first to get current gaze position.
6. If dwell is enabled, feed gaze to dwell.
7. If dwell is enabled and complete, return `DWELL_CLICK`.
8. If blink is enabled and a blink action fires, reset fatigue counter, increment blink counter, and return blink action.
9. If expression is enabled and expression action fires, return it.
10. If head is enabled and head action fires, return it.
11. Otherwise return gaze move.

Important note: the comment in the header says priority is `Dwell > Blink > Gaze+Expression > Head`, but the implemented order is `Dwell > Blink > Expression > Head > Gaze`.

### 4.5 `cpp/src/engine_api.cpp`

This file exposes a plain C ABI for Python `ctypes`. It avoids pybind11 or SWIG.

Internal helper:

| Function | Detail |
| --- | --- |
| `encodeAction(const Action& a)` | Writes `"TYPE|x|y|magnitude|label"` into a static `char s_outBuf[128]` and returns it. |

Exported C functions:

| Function | Detail |
| --- | --- |
| `ff_create()` | Allocates `new FreeFaceEngine()` and returns an opaque pointer. |
| `ff_destroy(void* eng)` | Deletes the engine pointer. |
| `ff_process(void* eng, float* landmarks, int count)` | Calls `processFrame()` and returns encoded action string. |
| `ff_start_calibration(void* eng)` | Starts calibration. |
| `ff_calibrating(void* eng)` | Returns 1/0 calibration state. |
| `ff_calib_progress(void* eng)` | Returns calibration frames collected. |
| `ff_calib_total(void* eng)` | Returns total calibration frames. |
| `ff_load_profile(void* eng, const char* path)` | Loads profile; returns 1/0. |
| `ff_save_profile(void* eng, const char* path)` | Saves profile; returns 1/0. |
| `ff_set_gaze(void* eng, int on)` | Runtime gaze toggle. |
| `ff_set_blink(void* eng, int on)` | Runtime blink toggle. |
| `ff_set_head(void* eng, int on)` | Runtime head toggle. |
| `ff_set_expression(void* eng, int on)` | Runtime expression toggle. |
| `ff_set_dwell(void* eng, int on)` | Runtime dwell toggle. |
| `ff_frame_count(void* eng)` | Returns frame count. |
| `ff_blink_count(void* eng)` | Returns blink count. |
| `ff_is_fatigued(void* eng)` | Returns fatigue state as 1/0. |
| `ff_dwell_progress(void* eng)` | Returns dwell progress float. |

Technical note: `s_outBuf` is a single static output buffer. It is fine for one caller thread, but concurrent calls to `ff_process()` would overwrite each other.

## 5. Python Runtime

### 5.1 `python/engine_bridge.py`

This module loads `engine.so` and hides `ctypes` details behind Python classes.

#### `class ActionType(IntEnum)`

Mirrors the native C++ `ActionType`. Values must match exactly.

#### `@dataclass Action`

Fields:

| Field | Meaning |
| --- | --- |
| `type` | Python `ActionType`. |
| `x` | Normalized x. |
| `y` | Normalized y. |
| `magnitude` | Scroll/action intensity. |
| `label` | Human-readable action label. |

Function:

| Function | Detail |
| --- | --- |
| `is_none()` | True when `type == ActionType.NONE`. |

#### `parse_action(raw: bytes) -> Action`

Parses the C++ string format:

```text
TYPE|x|y|magnitude|label
```

If parsing fails for any reason, it returns `Action(type=ActionType.NONE)`.

#### `class FreeFaceEngine`

Functions:

| Function | Detail |
| --- | --- |
| `__init__(lib_path="./engine.so")` | Checks the library path, loads it with `ctypes.CDLL`, configures signatures, and creates a native engine via `ff_create()`. |
| `_setup_signatures()` | Defines `restype` and `argtypes` for every exported C function. This is critical for correct pointer/string/int/float behavior. |
| `process(landmarks)` | Flattens `[[x,y,z], ...]` to a C float array, calls `ff_process`, and parses the returned action. |
| `start_calibration()` | Calls `ff_start_calibration`. |
| `is_calibrating()` | Calls `ff_calibrating` and converts to bool. |
| `calib_progress()` | Returns `(current_frames, total_frames)`. |
| `load_profile(path)` | Calls `ff_load_profile` with encoded path. |
| `save_profile(path)` | Calls `ff_save_profile` with encoded path. |
| `set_gaze(on)` | Calls `ff_set_gaze`. |
| `set_blink(on)` | Calls `ff_set_blink`. |
| `set_head(on)` | Calls `ff_set_head`. |
| `set_expression(on)` | Calls `ff_set_expression`. |
| `set_dwell(on)` | Calls `ff_set_dwell`. |
| `frame_count` | Property calling `ff_frame_count`. |
| `blink_count` | Property calling `ff_blink_count`. |
| `is_fatigued` | Property calling `ff_is_fatigued`. |
| `dwell_progress` | Property calling `ff_dwell_progress`. |
| `__del__()` | Destroys native engine if present. |

### 5.2 `python/face_mesh.py`

Thin wrapper around MediaPipe FaceMesh.

#### `class FaceMesh`

State:

| Field | Meaning |
| --- | --- |
| `_mp` | `mp.solutions.face_mesh`. |
| `_mesh` | MediaPipe FaceMesh instance. |
| `_draw` | MediaPipe drawing utilities. |
| `_spec` | Face mesh tessellation spec, currently stored but not directly used. |
| `_process_every` | Process every Nth frame. |
| `_frame_idx` | Frame counter. |
| `_last_landmarks` | Cached landmarks from last processed frame. |

Functions:

| Function | Detail |
| --- | --- |
| `__init__(process_every_n=2)` | Creates one-face MediaPipe FaceMesh with `refine_landmarks=True` for iris landmarks and confidence thresholds at `0.5`. |
| `process(bgr_frame)` | Increments frame index; skips processing on non-Nth frames and returns cached landmarks plus raw frame; otherwise converts BGR to RGB, runs MediaPipe, draws mesh overlay, draws iris points, converts landmarks to Python list, caches and returns them. |
| `close()` | Closes MediaPipe resources. |

Technical notes:

- The C++ engine expects up to 478 landmarks. `refine_landmarks=True` is necessary for iris landmarks.
- On skipped frames, the returned annotated frame is the original `bgr_frame`, not a copied/drawn frame.
- In the iris drawing loop, `cx/cy` are computed outside the `if idx < len(face.landmark)` block. With normal 478 landmarks it works; with fewer landmarks it could reuse an old `lm` value or fail. Because `refine_landmarks=True`, this usually does not surface.

### 5.3 `python/os_control.py`

Translates `Action` objects into OS mouse and keyboard events using `pynput`.

#### `class OSController`

State:

| Field | Meaning |
| --- | --- |
| `_mouse` | `pynput.mouse.Controller`. |
| `_kb` | `pynput.keyboard.Controller`. |
| `_lock` | Thread lock around OS input actions. |
| `_sw`, `_sh` | Screen width/height. |
| `_cur_x`, `_cur_y` | Smoothed cursor position. |
| `_last_scroll` | Timestamp of last scroll. |
| `_last_click` | Timestamp of last click. |
| `_scroll_gap` | Minimum seconds between scrolls, `0.4`. |
| `_click_gap` | Minimum seconds between clicks, `0.8`. |

Functions:

| Function | Detail |
| --- | --- |
| `__init__(screen_w, screen_h)` | Initializes controllers, lock, screen size, cursor center, and rate limit timers. |
| `execute(action)` | Ignores `NONE`; otherwise locks and dispatches. Safe to call from multiple threads. |
| `_dispatch(a)` | Handles all action types. |
| `type_char(char)` | Presses/releases one character under lock. |
| `type_special(key)` | Presses/releases a special `pynput.keyboard.Key` under lock. |

Dispatch behavior:

| Action | OS behavior |
| --- | --- |
| `MOUSE_MOVE` | Converts normalized x/y to pixels; moves 30% toward target each frame for smoothing. |
| `LEFT_CLICK` / `DWELL_CLICK` | Left click if not within click cooldown. |
| `DOUBLE_CLICK` | Double left click if not within click cooldown. |
| `RIGHT_CLICK` | Right click if not within click cooldown. |
| `SCROLL_UP` | Scrolls up by `max(1, int(magnitude * 3))` if not within scroll cooldown. |
| `SCROLL_DOWN` | Scrolls down by same magnitude logic. |
| `KEY_ENTER` | Presses Enter. |
| `KEY_ESCAPE` | Presses Escape. |
| `KEY_SPACE` | Presses Space. |

### 5.4 `python/virtual_keyboard.py`

Tkinter keyboard navigated by gaze and activated by blink/dwell.

Constants:

| Name | Detail |
| --- | --- |
| `ROWS` | QWERTY-like keyboard rows with numbers, backspace, enter, comma, period, and space. |
| `SPECIAL` | Maps special key labels to `pynput.keyboard.Key`. |
| `KEY_W`, `KEY_H`, `PAD` | Key size constants, currently not used by button layout. |

#### `class VirtualKeyboard`

State:

| Field | Meaning |
| --- | --- |
| `_kb` | Keyboard controller. |
| `_root` | Tk root window or `None`. |
| `_buttons` | Label-to-button dictionary. |
| `_hovered` | Currently highlighted key label. |
| `_visible` | Whether keyboard is shown. |
| `_thread` | Tk thread. |

Functions:

| Function | Detail |
| --- | --- |
| `__init__()` | Initializes keyboard controller and UI state. |
| `show()` | If hidden, marks visible and starts `_build()` in a daemon thread. |
| `hide()` | Schedules root destruction, marks hidden, clears root. |
| `toggle()` | Shows or hides. |
| `update_gaze(screen_x, screen_y)` | Checks which button contains the current screen coordinate, highlights it, and stores `_hovered`. |
| `click_current()` | Presses the currently hovered key. Special labels use `SPECIAL`; normal labels are lowercased. Flashes green feedback. |
| `_unhighlight_all()` | Restores all buttons to normal colors and clears `_hovered`. |
| `_build()` | Creates always-on-top semi-transparent Tk window, builds all buttons, and runs `mainloop()`. |
| `_press(label)` | Mouse-click testing path for pressing a key directly. |

Technical note: Tkinter generally prefers UI operations on its own main thread. This code runs Tk in a daemon thread and uses `after()` for destruction/flash updates.

### 5.5 `python/voice_control.py`

Background speech recognizer using `speech_recognition` and Google speech recognition.

Constants:

| Name | Detail |
| --- | --- |
| `COMMANDS` | Exact text command map for Enter, Escape, Space, Tab, Delete, Backspace, and New Line. |

#### `class VoiceControl`

State:

| Field | Meaning |
| --- | --- |
| `_kb` | Keyboard controller. |
| `_mouse` | Mouse controller for scroll commands. |
| `_recognizer` | SpeechRecognition recognizer. |
| `_running` | Loop flag. |
| `_thread` | Daemon worker thread. |
| `_on_scroll_up`, `_on_scroll_down` | Optional callbacks accepted by constructor but not used in `_handle()`. |

Functions:

| Function | Detail |
| --- | --- |
| `__init__(on_scroll_up=None, on_scroll_down=None)` | Requires `speech_recognition`; configures recognizer threshold and dynamic energy. |
| `start()` | Verifies microphone backend, starts daemon `_loop()`, prints listening message. |
| `stop()` | Sets `_running` false. |
| `_loop()` | Opens microphone, adjusts ambient noise for 1 second, repeatedly listens with timeout 3 seconds and phrase limit 5 seconds, recognizes Google text, and handles it. |
| `_handle(text)` | Exact commands press keys; text containing `scroll up/down` scrolls mouse; other text is typed character by character plus trailing space. |

Error behavior:

- Missing SpeechRecognition raises at construction.
- Missing microphone/PyAudio raises a clear runtime error from `start()`.
- Recognition timeouts and unknown speech are ignored in the loop.
- API errors are printed.

### 5.6 `python/dashboard_server.py`

Flask + Socket.IO server for the live browser dashboard.

Global objects:

| Name | Detail |
| --- | --- |
| `app` | Flask app. |
| `io` | SocketIO app with CORS `*` and threading async mode. |
| `_state` | Shared state dictionary for gaze, action, frames, blinks, dwell, fatigue, calibration. |
| `_lock` | Protects `_state`. |

Functions:

| Function | Detail |
| --- | --- |
| `update(key, value)` | Lock and update one state key. |
| `update_all(**kwargs)` | Lock and update multiple state keys. |
| `push_gaze(x, y)` | Updates gaze state and emits `gaze` with rounded x/y. |
| `push_action(label, action_type)` | Updates action state and emits `action`. |
| `push_stats(frames, blinks, dwell, fatigued, calib, calib_pct)` | Updates stats and emits `stats`, converting dwell/calib to percentages. |
| `index()` | HTTP route `/`, serves `frontend/dashboard.html`. |
| `snapshot()` | HTTP route `/snapshot`, returns current `_state` as JSON. |
| `on_connect()` | Socket.IO connect handler; sends current stats. |
| `on_toggle(data)` | Socket.IO `toggle_feature`; currently only echoes `feature_ack`, does not call engine toggles. |
| `on_calibrate(data)` | Socket.IO `calibrate`; currently only emits `calib_started`, does not call engine calibration. |
| `start(port=5050)` | Starts Flask-SocketIO in a daemon thread and prints dashboard URL. |

Integration note: the dashboard HTML has an old `pollStats()` function that fetches `/stats`, but this server exposes `/snapshot`, not `/stats`. The dashboard primarily uses WebSocket events, and `pollStats()` is not called during startup.

### 5.7 `python/windows_compat.py`

Compatibility helpers for OS differences. It is not currently imported by `main.py`, but documents intended Windows/macOS/Linux differences.

Global flags:

| Name | Detail |
| --- | --- |
| `IS_WINDOWS` | `platform.system() == "Windows"`. |
| `IS_MACOS` | `platform.system() == "Darwin"`. |
| `IS_LINUX` | `platform.system() == "Linux"`. |

Functions:

| Function | Detail |
| --- | --- |
| `get_engine_lib_name()` | Returns `engine.dll` on Windows, `engine.dylib` on macOS, `engine.so` on Linux. |
| `get_webcam_backend()` | Returns `cv2.CAP_DSHOW` on Windows, otherwise `cv2.CAP_ANY`. |
| `check_admin_windows()` | Warns when Windows process is not running as Administrator. |
| `get_makefile_command()` | Returns `build_windows.bat` for Windows, otherwise `make`. |

### 5.8 `python/main.py`

Main application entrypoint.

Configuration constants:

| Constant | Default | Meaning |
| --- | --- | --- |
| `WEBCAM_IDX` | 0 | OpenCV camera index. |
| `PROCESS_EVERY_N` | 2 | Process every other frame, about 15 FPS. |
| `SHOW_CAMERA_WIN` | true | Show OpenCV HUD window. |
| `ENABLE_VOICE` | true | Start voice thread. |
| `ENABLE_DASHBOARD` | true | Start dashboard server. |
| `DASHBOARD_PORT` | 5050 | Dashboard port. |
| `ENGINE_PATH` | root `engine.so` | Native engine path. |
| `PROFILE_PATH` | `profiles/current.profile` | Profile path. |

Functions:

| Function | Detail |
| --- | --- |
| `get_screen_size()` | Reads `FREEFACE_SCREEN_SIZE` like `1920x1080`; falls back to `1920,1080`. |
| `draw_hud(frame, label, calib, calib_pct, fatigued, dwell_pct)` | Draws top status bar, calibration progress, dwell ring, fatigue warning, and key hints on camera frame. |
| `main()` | Full application setup, camera loop, action routing, dashboard updates, keyboard shortcuts, shutdown, and profile save. |

`main()` details:

1. Ensures `profiles/` exists.
2. Reads screen size.
3. Loads C++ engine; exits with a build hint if `engine.so` is missing.
4. Tries to load saved profile.
5. Starts calibration on every launch, even when profile load succeeds.
6. Creates OS controller and virtual keyboard.
7. Starts voice and dashboard if enabled.
8. Opens webcam and sets 640x480 at 30 FPS.
9. Creates `FaceMesh(process_every_n=2)`.
10. Runs capture loop:
    - Read frame.
    - Flip frame horizontally.
    - Process face landmarks.
    - Read calibration/dwell/fatigue stats.
    - Process landmarks through engine.
    - Push action/gaze/stats to dashboard.
    - Execute action or virtual keyboard behavior.
    - Draw HUD.
    - Handle `q`, `c`, `k`.
11. On exit, releases camera, closes windows/MediaPipe, saves profile.

Keyboard shortcuts:

| Key | Behavior |
| --- | --- |
| `q` | Quit. |
| `c` | Start calibration. |
| `k` | Toggle virtual keyboard. |

## 6. Frontend Dashboard

### `frontend/dashboard.html` and `frontend/dashboard-2.html`

These files are identical. They implement a browser monitor for FreeFace.

Main UI sections:

| Section | Detail |
| --- | --- |
| Header | Logo and connection state. |
| Frames card | Total processed frames. |
| Blinks card | Intentional blink count. |
| Dwell card | Dwell progress percentage. |
| Gaze map | 16:9 normalized screen map with cursor and trail. |
| Action log | Recent events. |
| Controller settings | Toggle buttons for gaze, blink, head, expression, dwell. |
| Eye strain monitor | Fatigue status bar. |
| Recalibrate button | Emits dashboard calibration request. |

Important JavaScript state/functions:

| Function/State | Detail |
| --- | --- |
| `state` | Holds frames, blinks, dwell, fatigue, feature toggles, connection flag. |
| `pollStats()` | Attempts to fetch `http://localhost:5050/stats`; currently unused and route does not exist in Python server. |
| `updateConnectionStatus()` | Updates status pill between live/offline. |
| `updateStats()` | Updates cards and fatigue UI. |
| `simulateGaze()` | Demo-mode gaze movement when engine offline. |
| `updateCursor(x, y)` | Moves gaze cursor and creates a fading trail. |
| `addLog(label, msg)` | Adds timestamped action log entries, keeping up to 30. |
| `toggle(key)` | Toggles local feature state and emits `toggle_feature` over Socket.IO if connected. |
| `calibrate()` | Logs calibration request and emits `calibrate` over Socket.IO. |
| `demoAction()` | Adds simulated actions while offline. |
| `connectWebSocket()` | Dynamically loads Socket.IO client from CDN, connects to `localhost:5050`, and wires events. |
| `actionDesc(type)` | Maps numeric action type to dashboard text. |
| `startDemo()` | Starts demo gaze/action timers. |

Socket.IO events consumed:

| Event | Behavior |
| --- | --- |
| `connect` | Marks live, logs connection, stops demo timers. |
| `disconnect` | Marks offline and restarts demo. |
| `gaze` | Updates cursor. |
| `action` | Adds action log. |
| `stats` | Updates frames/blinks/dwell/fatigue. |
| `calib_started` | Logs calibration started. |

Socket.IO events emitted:

| Event | Payload |
| --- | --- |
| `toggle_feature` | `{ feature, enabled }`. Server currently acknowledges only. |
| `calibrate` | `{}`. Server currently emits acknowledgement only. |

Technical notes:

- The dashboard loads Google Fonts and Socket.IO from the network/CDN.
- It has a complete offline demo mode, so it appears active even without the engine.
- Feature toggles currently affect dashboard visual state but do not reach the running engine because the server has no reference to the engine instance.

## 7. Tests

### `test.py`

This file is the component test runner. It adjusts `sys.path` to include `python/`, changes working directory to repo root, defines colored output labels, and exposes tests through the `TESTS` dictionary.

Global setup:

| Name | Detail |
| --- | --- |
| `ROOT` | Directory containing `test.py`. |
| `sys.path.insert(...)` | Allows imports from `python/`. |
| `os.chdir(ROOT)` | Ensures relative engine/profile paths work. |
| `PASS`, `FAIL`, `INFO` | ANSI-colored output strings. |

Test functions:

| Function | Detail |
| --- | --- |
| `test_engine()` | Verifies `engine.so` exists, loads `FreeFaceEngine`, processes 478 dummy landmarks, starts calibration, checks calibration flag, toggles blink off/on, prints frame count. |
| `test_camera()` | Opens webcam index 0 with OpenCV, reads one frame, prints resolution. |
| `test_mediapipe()` | Imports MediaPipe, creates `FaceMesh`, processes a blank frame, expects `None`, closes mesh. |
| `test_gaze_live()` | 10-second interactive camera test; starts calibration, processes live landmarks, draws crosshair for `MOUSE_MOVE`. |
| `test_blink_live()` | 15-second interactive blink test; starts calibration, counts `LEFT_CLICK`/`DOUBLE_CLICK` actions. |
| `test_voice()` | Uses SpeechRecognition microphone, adjusts ambient noise, listens, calls Google recognizer, prints heard text. |
| `test_os()` | Creates `OSController`, moves mouse in a small circle through `MOUSE_MOVE` actions, types a space key. |
| `test_keyboard()` | Shows `VirtualKeyboard` for 5 seconds then hides it. |

`TESTS` dictionary maps command names:

```text
engine, camera, mediapipe, gaze, blink, voice, os, keyboard
```

CLI behavior:

- No args: runs non-interactive tests `engine`, `camera`, `mediapipe`, and `os`; prints summary.
- One arg: runs the named test if available.
- Unknown arg: prints available test names.

## 8. Build and Setup

### `Makefile`

Variables:

| Variable | Value |
| --- | --- |
| `CXX` | `g++` |
| `CXXFLAGS` | `-std=c++17 -O2 -Wall -fPIC -Icpp/include` |
| `TARGET` | `engine.so` |
| `SRCS` | `Detectors.cpp`, `FreeFaceEngine.cpp`, `engine_api.cpp` |

Targets:

| Target | Behavior |
| --- | --- |
| `all` | Builds `engine.so` and prints ready message. |
| `engine.so` | Compiles all C++ sources as a shared library. |
| `test` | Builds engine then runs `python3 test.py`. |
| `test-engine` | Runs `python3 test.py engine`. |
| `test-camera` | Runs camera test. |
| `test-mediapipe` | Runs MediaPipe test. |
| `test-gaze` | Runs interactive gaze test. |
| `test-blink` | Runs interactive blink test. |
| `test-voice` | Runs voice test. |
| `test-keyboard` | Runs virtual keyboard test. |
| `test-os` | Runs OS control test. |
| `clean` | Removes `engine.so`. |

### `setup.sh`

One-command setup script.

Steps:

1. Exits on error with `set -e`.
2. Checks `python3`.
3. Checks `g++`.
4. Creates `venv` if missing.
5. Activates virtual environment.
6. Upgrades pip/setuptools/wheel with retries/timeouts.
7. Installs `requirements.txt`.
8. Tries to install optional `requirements-voice.txt`; failure only warns.
9. Builds C++ engine with `make`.
10. Creates `profiles/`.
11. Prints run instructions.

### Dependencies

`requirements.txt`:

| Package | Use |
| --- | --- |
| `mediapipe==0.10.21` | Face landmark extraction. |
| `opencv-contrib-python==4.11.0.86` | Webcam, image conversion, display, drawing. |
| `pynput>=1.7.6` | OS mouse/keyboard control. |
| `screeninfo>=0.8.1` | Listed dependency, not currently used in source. |
| `flask>=3.0.0` | Dashboard HTTP server. |
| `flask-socketio>=5.3.6` | Dashboard WebSocket server. |
| `SpeechRecognition>=3.10.0` | Voice recognition wrapper. |
| `numpy>=1.24.0` | Frame arrays and test blank image. |

`requirements-voice.txt`:

| Package | Use |
| --- | --- |
| `PyAudio>=0.2.13` | Microphone backend for SpeechRecognition. May need PortAudio system libs. |

## 9. Binary Files

### `engine.so`

`engine.so` is a Mach-O 64-bit arm64 dynamically linked shared library in this workspace. It exports the C API functions used by Python:

```text
ff_create
ff_destroy
ff_process
ff_start_calibration
ff_calibrating
ff_calib_progress
ff_calib_total
ff_load_profile
ff_save_profile
ff_set_gaze
ff_set_blink
ff_set_head
ff_set_expression
ff_set_dwell
ff_frame_count
ff_blink_count
ff_is_fatigued
ff_dwell_progress
```

It also contains compiled symbols for the detector and engine methods from the C++ source.

### `profiles/current.profile`

Binary profile file, currently 120 bytes. The first bytes decode to the string `default`, followed by raw boolean/float struct data. The observed file matches the `AccessibilityProfile` raw binary persistence model.

Because it is raw binary:

- It should be read/written by the same struct definition.
- Changing field order/types can invalidate old profiles.
- It is not human-editable without a dedicated decoder.

## 10. Existing Documentation Files

### `README.md`

Covers:

- User-facing purpose.
- Input/action table.
- File structure.
- Setup with `pip install`, `make`, and `python3 main.py`.
- Manual tests for calibration, gaze, blink, double click, scroll, virtual keyboard, voice, dwell, dashboard.
- OOP concepts demonstrated.
- Optimizations and hardware requirements.

### `TESTING.md`

Complete testing guide:

- `make test` and individual test commands.
- Detailed descriptions of all 8 tests.
- Expected output examples.
- Setup/build troubleshooting.
- Mermaid test flow.
- Debugging failed tests.
- Test result interpretation.
- How to add tests.

### `TESTING_QUICKREF.md`

Short version of test commands, default/interactive test matrix, quick troubleshooting, and links to the full guide.

### `SETUP_SUMMARY.md`

Documents the project reorganization, Makefile updates, test suite creation, documentation files, coverage matrix, setup commands, and verification checklist.

### `INDEX.md`

Navigation file pointing users to setup, tests, troubleshooting, component references, and common tasks.

## 11. Important Technical Notes and Mismatches

These are not necessarily failures, but they matter for future maintenance.

| Area | Note |
| --- | --- |
| Dashboard stats route | HTML defines `pollStats()` for `/stats`, but Flask server exposes `/snapshot`; `pollStats()` is currently unused. |
| Dashboard toggles | Toggle/calibrate messages are acknowledged by the server but do not affect the engine. |
| Profile calibration fields | `AccessibilityProfile` stores threshold/bounds fields, but detector calibration does not currently copy computed detector values into the profile fields. |
| Startup calibration | `main.py` starts calibration even after successfully loading a saved profile. |
| Landmark count | C++ expects 478 points. MediaPipe returns this with `refine_landmarks=True`; without it, iris indices would be unavailable. |
| `face_mesh.py` iris loop | `cx/cy` computation sits outside the bounds `if`; normal refined landmarks make it okay, but shorter landmark lists could behave incorrectly. |
| `ExpressionEngine::calibrated_` | Set during calibration but not checked in `process()`. |
| Static C output buffer | `engine_api.cpp` uses one static return buffer, safe for single-threaded use but not concurrent `ff_process()` calls. |
| Raw binary profile | Fast but version/architecture fragile. |
| `screeninfo` dependency | Installed but `main.py` uses env override/fallback instead of screeninfo. |
| Windows compatibility | Helper exists but is not integrated into main runtime. |
| Voice callbacks | `VoiceControl` accepts scroll callbacks but directly scrolls mouse instead. |

## 12. Suggested Mental Model

Think of FreeFace as four layers:

1. Sensor layer: OpenCV camera and MediaPipe landmarks.
2. Intent layer: C++ detectors convert geometry into normalized actions.
3. Routing layer: Python decides whether action goes to mouse, keyboard, virtual keyboard, dashboard, or voice flow.
4. Feedback layer: OpenCV HUD and browser dashboard show calibration, gaze, actions, fatigue, and dwell progress.

The most important contract is the action ABI between C++ and Python:

```text
MediaPipe landmarks
  -> Python list [[x,y,z], ...]
  -> flat ctypes float array
  -> ff_process()
  -> "TYPE|x|y|magnitude|label"
  -> Python Action
  -> OS/dashboard/UI behavior
```

If you change action values, landmark count, label format, or profile layout, update both sides of that contract together.
