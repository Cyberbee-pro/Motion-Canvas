// engine_api.cpp
// Thin C wrapper around FreeFaceEngine so Python ctypes can call it.
// No pybind11, no swig — just plain C function pointers.
//
// Python loads this as: ctypes.CDLL("./engine.so")

#include "FreeFaceEngine.h"
#include <cstring>
#include <cstdio>

// One static string buffer for return values (thread-safe enough for single caller)
static char s_outBuf[128];

// Encode Action to a compact pipe string: "TYPE|x|y|magnitude|label"
static const char* encodeAction(const Action& a) {
    std::snprintf(s_outBuf, sizeof(s_outBuf),
        "%d|%.4f|%.4f|%.4f|%s",
        static_cast<int>(a.type), a.x, a.y, a.magnitude,
        a.label ? a.label : "NONE");
    return s_outBuf;
}

extern "C" {

// ── Lifecycle ────────────────────────────────────────────────────
void* ff_create() {
    return new FreeFaceEngine();
}

void ff_destroy(void* eng) {
    delete static_cast<FreeFaceEngine*>(eng);
}

// ── Main call (Python sends flat float array each frame) ─────────
// Returns: "TYPE|x|y|magnitude|label\0"
// Python parses this string to know what OS action to perform.
const char* ff_process(void* eng, float* landmarks, int count) {
    auto* e = static_cast<FreeFaceEngine*>(eng);
    Action a = e->processFrame(landmarks, count);
    return encodeAction(a);
}

// ── Calibration ──────────────────────────────────────────────────
void ff_start_calibration(void* eng) {
    static_cast<FreeFaceEngine*>(eng)->startCalibration();
}

int ff_calibrating(void* eng) {
    return static_cast<FreeFaceEngine*>(eng)->calibrating() ? 1 : 0;
}

int ff_calib_progress(void* eng) {
    return static_cast<FreeFaceEngine*>(eng)->calibProgress();
}

int ff_calib_total(void* eng) {
    return static_cast<FreeFaceEngine*>(eng)->calibTotal();
}

// ── Profile ──────────────────────────────────────────────────────
int ff_load_profile(void* eng, const char* path) {
    return static_cast<FreeFaceEngine*>(eng)->loadProfile(path) ? 1 : 0;
}

int ff_save_profile(void* eng, const char* path) {
    return static_cast<FreeFaceEngine*>(eng)->saveProfile(path) ? 1 : 0;
}

// ── Feature toggles (called from dashboard settings) ─────────────
void ff_set_gaze      (void* eng, int on) { static_cast<FreeFaceEngine*>(eng)->setGaze(on); }
void ff_set_blink     (void* eng, int on) { static_cast<FreeFaceEngine*>(eng)->setBlink(on); }
void ff_set_head      (void* eng, int on) { static_cast<FreeFaceEngine*>(eng)->setHead(on); }
void ff_set_expression(void* eng, int on) { static_cast<FreeFaceEngine*>(eng)->setExpression(on); }
void ff_set_dwell     (void* eng, int on) { static_cast<FreeFaceEngine*>(eng)->setDwell(on); }

// ── Stats ─────────────────────────────────────────────────────────
int   ff_frame_count   (void* eng) { return static_cast<FreeFaceEngine*>(eng)->frameCount(); }
int   ff_blink_count   (void* eng) { return static_cast<FreeFaceEngine*>(eng)->blinkCount(); }
int   ff_is_fatigued   (void* eng) { return static_cast<FreeFaceEngine*>(eng)->isFatigued() ? 1 : 0; }
float ff_dwell_progress(void* eng) { return static_cast<FreeFaceEngine*>(eng)->dwellProgress(); }

} // extern "C"
