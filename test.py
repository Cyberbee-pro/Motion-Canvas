"""
test.py — FreeFace component tester
Run this BEFORE main.py to verify each piece works on your machine.

Usage:
  python3 test.py            # runs all tests
  python3 test.py engine     # test C++ engine only
  python3 test.py camera     # test webcam only
  python3 test.py gaze       # test gaze tracking live
  python3 test.py blink      # test blink detection live
  python3 test.py voice      # test voice recognition
  python3 test.py keyboard   # test virtual keyboard
  python3 test.py os         # test OS mouse/keyboard control
"""
import sys, os, time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "python"))
os.chdir(ROOT)

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
INFO = "\033[94m  →\033[0m"

# ─────────────────────────────────────────────────────────────────
def test_engine():
    print("\n── Test: C++ Engine ─────────────────────────────")
    engine_path = os.path.join(ROOT, "engine.so")
    if not os.path.exists(engine_path):
        print(f"{FAIL}  engine.so not found at {engine_path}")
        print(f"{INFO}  Run: make   (in project root)")
        return False

    try:
        from python.engine_bridge import FreeFaceEngine, ActionType
        engine = FreeFaceEngine(lib_path=engine_path)
        print(f"{PASS}  Engine loaded")

        # Feed dummy landmarks (478 points of zeros)
        dummy = [[0.5, 0.5, 0.0]] * 478
        action = engine.process(dummy)
        print(f"{PASS}  processFrame() returned: {action.label}")

        # Test calibration
        engine.start_calibration()
        assert engine.is_calibrating(), "Should be calibrating"
        print(f"{PASS}  Calibration mode works")

        # Test toggles
        engine.set_blink(False)
        engine.set_blink(True)
        print(f"{PASS}  Feature toggles work")

        print(f"{PASS}  Frame count: {engine.frame_count}")
        return True
    except Exception as e:
        print(f"{FAIL}  Engine error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
def test_camera():
    print("\n── Test: Webcam ─────────────────────────────────")
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print(f"{FAIL}  Webcam index 0 not found. Try changing WEBCAM_IDX in main.py")
            return False
        ret, frame = cap.read()
        if not ret or frame is None:
            print(f"{FAIL}  Could not read frame")
            cap.release()
            return False
        h, w = frame.shape[:2]
        print(f"{PASS}  Webcam opened: {w}x{h}")
        cap.release()
        return True
    except Exception as e:
        print(f"{FAIL}  Camera error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
def test_mediapipe():
    print("\n── Test: MediaPipe FaceMesh ─────────────────────")
    try:
        import mediapipe as mp
        print(f"{PASS}  MediaPipe imported (version: {mp.__version__})")

        from python.face_mesh import FaceMesh
        import cv2, numpy as np
        mesh = FaceMesh()
        # Test with a black frame (no face — should return None)
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        lm, _ = mesh.process(blank)
        assert lm is None, "Should return None for blank frame"
        print(f"{PASS}  FaceMesh processes blank frame correctly (no face detected)")
        mesh.close()
        return True
    except Exception as e:
        print(f"{FAIL}  MediaPipe error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
def test_gaze_live():
    """Interactive: shows live gaze tracking for 10 seconds."""
    print("\n── Test: Live Gaze Tracking (10 seconds) ────────")
    print(f"{INFO}  A camera window will open. Move your eyes around.")
    print(f"{INFO}  The crosshair should follow your gaze. Press Q to stop early.")

    try:
        import cv2
        from python.face_mesh     import FaceMesh
        from python.engine_bridge import FreeFaceEngine, ActionType

        engine = FreeFaceEngine(lib_path=os.path.join(ROOT, "engine.so"))
        engine.start_calibration()
        mesh = FaceMesh()
        cap  = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        start = time.time()
        while time.time() - start < 10:
            ret, raw = cap.read()
            if not ret: break
            frame = cv2.flip(raw, 1)
            lm, annotated = mesh.process(frame)

            if lm:
                action = engine.process(lm)
                if action.type == ActionType.MOUSE_MOVE:
                    h, w = frame.shape[:2]
                    px, py = int(action.x * w), int(action.y * h)
                    cv2.circle(annotated, (px, py), 12, (0, 255, 120), 3)
                    cv2.line(annotated, (px-20, py), (px+20, py), (0,255,120), 1)
                    cv2.line(annotated, (px, py-20), (px, py+20), (0,255,120), 1)
                    cv2.putText(annotated, f"GAZE ({action.x:.2f}, {action.y:.2f})",
                                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0,255,120), 2)

            remaining = int(10 - (time.time() - start))
            cv2.putText(annotated, f"Closing in {remaining}s  |  Q=stop",
                        (10, annotated.shape[0]-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100,100,120), 1)
            cv2.imshow("Gaze Test", annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        mesh.close()
        print(f"{PASS}  Gaze test complete")
        return True
    except Exception as e:
        print(f"{FAIL}  Gaze test error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
def test_blink_live():
    """Interactive: counts blinks for 15 seconds."""
    print("\n── Test: Blink Detection (15 seconds) ───────────")
    print(f"{INFO}  Blink slowly and deliberately. Count should increment.")
    try:
        import cv2
        from python.face_mesh     import FaceMesh
        from python.engine_bridge import FreeFaceEngine, ActionType

        engine = FreeFaceEngine(lib_path=os.path.join(ROOT, "engine.so"))
        # Calibrate first
        print(f"{INFO}  Calibrating for 2 seconds — keep eyes open normally...")
        mesh = FaceMesh()
        cap  = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        engine.start_calibration()

        blinks = 0
        start  = time.time()
        while time.time() - start < 15:
            ret, raw = cap.read()
            if not ret: break
            frame = cv2.flip(raw, 1)
            lm, annotated = mesh.process(frame)

            if lm:
                action = engine.process(lm)
                if action.type in (ActionType.LEFT_CLICK, ActionType.DOUBLE_CLICK):
                    blinks += 1
                    print(f"  → Blink detected! Total: {blinks}  ({action.label})")

            remaining = int(15 - (time.time() - start))
            cv2.putText(annotated, f"Blinks: {blinks}  |  {remaining}s remaining",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 200, 120), 2)
            cv2.imshow("Blink Test  |  Q=stop", annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
        mesh.close()
        if blinks > 0:
            print(f"{PASS}  Detected {blinks} blink(s)")
        else:
            print(f"{FAIL}  No blinks detected. Check lighting and recalibrate.")
        return blinks > 0
    except Exception as e:
        print(f"{FAIL}  Blink test error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
def test_voice():
    print("\n── Test: Voice Recognition (10 seconds) ─────────")
    print(f"{INFO}  Say something clearly. It should be printed below.")
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print(f"{INFO}  Adjusting for ambient noise...")
            r.adjust_for_ambient_noise(source, duration=1)
            print(f"{INFO}  Listening... speak now!")
            try:
                audio = r.listen(source, timeout=8, phrase_time_limit=5)
                text  = r.recognize_google(audio)
                print(f"{PASS}  Heard: \"{text}\"")
                return True
            except sr.WaitTimeoutError:
                print(f"{FAIL}  No speech detected (timeout)")
            except sr.UnknownValueError:
                print(f"{FAIL}  Speech detected but could not understand it")
    except Exception as e:
        print(f"{FAIL}  Voice error: {e}")
        print(f"{INFO}  Install: pip install SpeechRecognition pyaudio")
    return False


# ─────────────────────────────────────────────────────────────────
def test_os():
    print("\n── Test: OS Mouse/Keyboard Control ──────────────")
    print(f"{INFO}  Watch your mouse — it will move in a circle, then click.")
    try:
        import math
        from python.engine_bridge import Action, ActionType
        from python.os_control    import OSController
        ctrl = OSController(1920, 1080)

        print(f"{INFO}  Moving mouse in a small circle...")
        for i in range(20):
            angle = (i / 20) * 2 * math.pi
            x = 0.5 + math.cos(angle) * 0.05
            y = 0.5 + math.sin(angle) * 0.05
            a = Action(type=ActionType.MOUSE_MOVE, x=x, y=y)
            ctrl.execute(a)
            time.sleep(0.05)

        print(f"{PASS}  Mouse movement works")
        print(f"{INFO}  Testing keyboard (will type a space)...")
        ctrl.type_special(__import__('pynput').keyboard.Key.space)
        print(f"{PASS}  Keyboard works")
        return True
    except Exception as e:
        print(f"{FAIL}  OS control error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
def test_keyboard():
    print("\n── Test: Virtual Keyboard ───────────────────────")
    print(f"{INFO}  A keyboard window will open for 5 seconds.")
    try:
        from python.virtual_keyboard import VirtualKeyboard
        vkb = VirtualKeyboard()
        vkb.show()
        time.sleep(5)
        vkb.hide()
        print(f"{PASS}  Virtual keyboard opened and closed")
        return True
    except Exception as e:
        print(f"{FAIL}  Keyboard error: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
TESTS = {
    "engine"  : test_engine,
    "camera"  : test_camera,
    "mediapipe": test_mediapipe,
    "gaze"    : test_gaze_live,
    "blink"   : test_blink_live,
    "voice"   : test_voice,
    "os"      : test_os,
    "keyboard": test_keyboard,
}

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        # Run non-interactive tests by default
        print("╔══════════════════════════════════════════╗")
        print("║   FreeFace — Component Test Suite        ║")
        print("╚══════════════════════════════════════════╝")
        results = {}
        for name in ["engine", "camera", "mediapipe", "os"]:
            results[name] = TESTS[name]()

        print("\n── Summary ──────────────────────────────────")
        for name, ok in results.items():
            status = PASS if ok else FAIL
            print(f"  {status}  {name}")

        all_ok = all(results.values())
        if all_ok:
            print(f"\n{PASS}  All core components working!")
            print(f"     Run: cd python && python3 main.py")
        else:
            print(f"\n{FAIL}  Fix the failing components above first.")
        print()

    else:
        name = args[0].lower()
        if name in TESTS:
            TESTS[name]()
        else:
            print(f"Unknown test: {name}")
            print(f"Available: {', '.join(TESTS.keys())}")
