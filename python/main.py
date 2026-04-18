"""
main.py — FreeFace entry point

Threading model:
  Thread 1 (main) : webcam capture + OpenCV display loop
  Thread 2 (daemon): Voice recognition
  Thread 3 (daemon): Flask-SocketIO dashboard server

Press Q in camera window to quit.
Press C to recalibrate.
Press K to toggle virtual keyboard.
"""
import cv2, sys, os, time, threading
import numpy as np

# ── Resolve paths relative to this file ───────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "python"))

from face_mesh        import FaceMesh
from engine_bridge    import FreeFaceEngine, ActionType
from os_control       import OSController
from voice_control    import VoiceControl
from virtual_keyboard import VirtualKeyboard
import dashboard_server as dash

# ─────────────────────────────────────────────────────────────────
#  CONFIG — edit these if needed
# ─────────────────────────────────────────────────────────────────
WEBCAM_IDX       = 0       # 0 = default webcam; try 1 if that fails
PROCESS_EVERY_N  = 2       # 1=30fps, 2=15fps (recommended)
SHOW_CAMERA_WIN  = True    # False = run headless (no cv2 window)
ENABLE_VOICE     = True    # False = skip microphone
ENABLE_DASHBOARD = True    # False = skip Flask server
DASHBOARD_PORT   = 5050
ENGINE_PATH      = os.path.join(ROOT, "engine.so")
PROFILE_PATH     = os.path.join(ROOT, "profiles", "current.profile")
# ─────────────────────────────────────────────────────────────────

def get_screen_size() -> tuple[int, int]:
    try:
        from screeninfo import get_monitors
        m = get_monitors()[0]
        return m.width, m.height
    except Exception:
        return 1920, 1080


def draw_hud(frame, label, calib, calib_pct, fatigued, dwell_pct):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 40), (12, 14, 26), -1)
    cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

    color = (80, 200, 120) if not calib else (80, 180, 255)
    cv2.putText(frame, f"[ {label} ]", (10, 27),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)

    if calib:
        bar = int(w * calib_pct)
        cv2.rectangle(frame, (0, 36), (bar, 40), (80, 180, 255), -1)
        cv2.putText(frame, f"CALIBRATING {int(calib_pct*100)}% — look at screen center",
                    (w//2 - 180, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 180, 255), 1)

    if dwell_pct > 0.01:
        cx, cy, r = w - 36, 36, 22
        cv2.circle(frame, (cx, cy), r, (30, 30, 50), 2)
        cv2.ellipse(frame, (cx, cy), (r, r), -90, 0,
                    int(360 * dwell_pct), (80, 160, 255), 3)

    if fatigued:
        cv2.rectangle(frame, (0, h-38), (w, h), (20, 0, 120), -1)
        cv2.putText(frame, "  EYE STRAIN — Rest your eyes",
                    (8, h-12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 160, 255), 2)

    cv2.putText(frame, "Q=quit  C=calibrate  K=keyboard",
                (w - 270, h - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (60, 60, 80), 1)
    return frame


def main():
    os.makedirs(os.path.join(ROOT, "profiles"), exist_ok=True)

    sw, sh = get_screen_size()
    print(f"[FreeFace] Screen: {sw}x{sh}")

    print("[FreeFace] Loading C++ engine...")
    try:
        engine = FreeFaceEngine(lib_path=ENGINE_PATH)
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        print("Did you run:  make  (in the project root)?")
        sys.exit(1)

    if engine.load_profile(PROFILE_PATH):
        print("[FreeFace] Saved profile loaded")
    else:
        print("[FreeFace] No profile — starting calibration")
        engine.start_calibration()

    os_ctrl = OSController(sw, sh)
    vkb     = VirtualKeyboard()

    if ENABLE_VOICE:
        voice = VoiceControl()
        try:
            voice.start()
        except Exception as e:
            print(f"[Voice] Could not start: {e}")

    if ENABLE_DASHBOARD:
        try:
            dash.start(port=DASHBOARD_PORT)
        except Exception as e:
            print(f"[Dashboard] Could not start: {e}")

    cap = cv2.VideoCapture(WEBCAM_IDX)
    if not cap.isOpened():
        print(f"ERROR: Cannot open webcam (index {WEBCAM_IDX})")
        sys.exit(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    mesh       = FaceMesh(process_every_n=PROCESS_EVERY_N)
    last_label = "STARTING"
    frame_ctr  = 0

    print("\n[FreeFace] Running")
    print("  Q = quit | C = recalibrate | K = keyboard toggle\n")

    while True:
        ret, raw = cap.read()
        if not ret:
            break

        frame_ctr += 1
        frame = cv2.flip(raw, 1)
        landmarks, annotated = mesh.process(frame)

        calib     = engine.is_calibrating()
        prog, tot = engine.calib_progress()
        calib_pct = prog / tot if tot > 0 else 0.0
        dwell_pct = engine.dwell_progress
        fatigued  = engine.is_fatigued

        if landmarks:
            action = engine.process(landmarks)
            if not action.is_none():
                last_label = action.label
                if ENABLE_DASHBOARD:
                    dash.push_action(action.label, int(action.type))

                if action.type == ActionType.MOUSE_MOVE:
                    vkb.update_gaze(int(action.x * sw), int(action.y * sh))
                    if ENABLE_DASHBOARD:
                        dash.push_gaze(action.x, action.y)
                    os_ctrl.execute(action)
                elif action.type == ActionType.OPEN_KB:
                    vkb.toggle()
                elif action.type in (ActionType.LEFT_CLICK,
                                     ActionType.DWELL_CLICK) and vkb._visible:
                    vkb.click_current()
                else:
                    os_ctrl.execute(action)

        if frame_ctr % 30 == 0 and ENABLE_DASHBOARD:
            dash.push_stats(engine.frame_count, engine.blink_count,
                            dwell_pct, fatigued, calib, calib_pct)

        if SHOW_CAMERA_WIN:
            display = draw_hud(annotated, last_label,
                               calib, calib_pct, fatigued, dwell_pct)
            cv2.imshow("FreeFace  |  Q=quit  C=calibrate", display)

        key = cv2.waitKey(1) & 0xFF
        if   key == ord('q'): break
        elif key == ord('c'):
            engine.start_calibration()
            print("[FreeFace] Recalibrating...")
        elif key == ord('k'):
            vkb.toggle()

    cap.release()
    cv2.destroyAllWindows()
    mesh.close()
    engine.save_profile(PROFILE_PATH)
    print("[FreeFace] Profile saved. Goodbye.")


if __name__ == "__main__":
    main()
