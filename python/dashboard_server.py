"""
dashboard_server.py
Real-time WebSocket server that pushes live data to dashboard.html.
Replaces the polling approach — dashboard gets gaze + action updates
at ~15fps instead of every 500ms.

Uses Flask-SocketIO (works with the same Flask install).
"""
import threading
from flask import Flask, send_from_directory
from flask_socketio import SocketIO
import os, time

app    = Flask(__name__)
io     = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ── Shared state pushed by main.py ────────────────────────────────
_state = {
    "gaze_x"  : 0.5,
    "gaze_y"  : 0.5,
    "action"  : "NONE",
    "label"   : "NONE",
    "frames"  : 0,
    "blinks"  : 0,
    "dwell"   : 0.0,
    "fatigued": False,
    "calib"   : False,
    "calib_pct": 0.0,
}
_lock = threading.Lock()

def update(key: str, value):
    with _lock:
        _state[key] = value

def update_all(**kwargs):
    with _lock:
        _state.update(kwargs)

def push_gaze(x: float, y: float):
    """Call from main.py every frame with current gaze position."""
    update_all(gaze_x=x, gaze_y=y)
    io.emit("gaze", {"x": round(x, 4), "y": round(y, 4)})

def push_action(label: str, action_type: int):
    """Call from main.py when a non-NONE action fires."""
    update_all(action=action_type, label=label)
    io.emit("action", {"label": label, "type": action_type})

def push_stats(frames: int, blinks: int, dwell: float,
               fatigued: bool, calib: bool, calib_pct: float):
    """Call from main.py every ~30 frames with stats."""
    update_all(frames=frames, blinks=blinks, dwell=dwell,
               fatigued=fatigued, calib=calib, calib_pct=calib_pct)
    io.emit("stats", {
        "frames"   : frames,
        "blinks"   : blinks,
        "dwell"    : round(dwell * 100),
        "fatigued" : fatigued,
        "calib"    : calib,
        "calib_pct": round(calib_pct * 100),
    })

# ── HTTP routes ───────────────────────────────────────────────────
@app.route("/")
def index():
    """Serve dashboard directly from Flask."""
    dashboard_path = os.path.join(os.path.dirname(__file__),
                                  "..", "frontend")
    return send_from_directory(dashboard_path, "dashboard.html")

@app.route("/snapshot")
def snapshot():
    """REST fallback — returns current state as JSON."""
    from flask import jsonify
    with _lock:
        return jsonify(dict(_state))

@io.on("connect")
def on_connect():
    """Send full state to newly connected client."""
    with _lock:
        io.emit("stats", {
            "frames"   : _state["frames"],
            "blinks"   : _state["blinks"],
            "dwell"    : round(_state["dwell"] * 100),
            "fatigued" : _state["fatigued"],
            "calib"    : _state["calib"],
            "calib_pct": round(_state["calib_pct"] * 100),
        })

@io.on("toggle_feature")
def on_toggle(data):
    """Dashboard can toggle features via WebSocket."""
    # data = {"feature": "blink", "enabled": True}
    # In a full integration, this would call engine.set_blink(enabled)
    io.emit("feature_ack", data)

@io.on("calibrate")
def on_calibrate(data):
    """Dashboard requested calibration."""
    io.emit("calib_started", {})

def start(port: int = 5050):
    """Start server in background daemon thread."""
    t = threading.Thread(
        target=lambda: io.run(app, port=port, debug=False,
                              use_reloader=False, allow_unsafe_werkzeug=True),
        daemon=True
    )
    t.start()
    print(f"[Dashboard] http://localhost:{port}/")
    return t
