#include "../include/Detectors.h"
#include <algorithm>
#include <cmath>

// ══════════════════════════════════════════════════════════════════
//  GazeTracker
// ══════════════════════════════════════════════════════════════════

float GazeTracker::mapAxis(float v, float lo, float hi) const {
    if (hi <= lo) return 0.5f;
    return std::clamp((v - lo) / (hi - lo), 0.0f, 1.0f);
}

Action GazeTracker::process(const LandmarkFrame& f) {
    if (!enabled_ || !f.isValid()) return {};

    // Average both irises for stability
    float gx = (f[LandmarkFrame::L_IRIS].x + f[LandmarkFrame::R_IRIS].x) * 0.5f;
    float gy = (f[LandmarkFrame::L_IRIS].y + f[LandmarkFrame::R_IRIS].y) * 0.5f;

    float sx = mapAxis(gx, xMin_, xMax_);
    float sy = mapAxis(gy, yMin_, yMax_);

    // Sensitivity pivot around screen center
    sx = 0.5f + (sx - 0.5f) * sensitivity_;
    sy = 0.5f + (sy - 0.5f) * sensitivity_;

    sx = kx_.update(std::clamp(sx, 0.0f, 1.0f));
    sy = ky_.update(std::clamp(sy, 0.0f, 1.0f));

    return {ActionType::MOUSE_MOVE, sx, sy, 0.0f, "GAZE_MOVE"};
}

void GazeTracker::calibrate(const LandmarkFrame& f) {
    if (!f.isValid()) return;
    // Use eye corners to define the gaze mapping space
    float lOut = f[LandmarkFrame::L_EYE_OUT].x;
    float rOut = f[LandmarkFrame::R_EYE_OUT].x;
    float lIn  = f[LandmarkFrame::L_EYE_IN].x;
    float rIn  = f[LandmarkFrame::R_EYE_IN].x;
    xMin_ = std::min(lOut, rOut) - 0.04f;
    xMax_ = std::max(lIn,  rIn)  + 0.04f;
    yMin_ = f[LandmarkFrame::L_EYE_TOP].y - 0.07f;
    yMax_ = f[LandmarkFrame::L_EYE_BOT].y + 0.10f;
}

void GazeTracker::reset() {
    kx_.reset(); ky_.reset();
    xMin_ = 0.33f; xMax_ = 0.67f;
    yMin_ = 0.33f; yMax_ = 0.67f;
}

// ══════════════════════════════════════════════════════════════════
//  BlinkDetector
// ══════════════════════════════════════════════════════════════════

// Eye Aspect Ratio = vertical_distance / horizontal_distance
// Open eye: ~0.28-0.35. Closed: drops below ~0.20
float BlinkDetector::ear(const LandmarkFrame& f, bool left) const {
    int t = left ? LandmarkFrame::L_EYE_TOP : LandmarkFrame::R_EYE_TOP;
    int b = left ? LandmarkFrame::L_EYE_BOT : LandmarkFrame::R_EYE_BOT;
    int i = left ? LandmarkFrame::L_EYE_IN  : LandmarkFrame::R_EYE_IN;
    int o = left ? LandmarkFrame::L_EYE_OUT : LandmarkFrame::R_EYE_OUT;
    float v = std::abs(f[t].y - f[b].y);
    float h = std::abs(f[i].x - f[o].x);
    return (h > 1e-5f) ? v / h : 0.0f;
}

Action BlinkDetector::process(const LandmarkFrame& f) {
    if (!enabled_ || !f.isValid()) return {};

    float e = (ear(f, true) + ear(f, false)) * 0.5f;
    earBuf_.push(e);
    sinceClick_++;

    float smooth = earBuf_.full() ? earBuf_.average() : e;
    bool  isNowClosed = smooth < threshold_;

    Action out;

    if (isNowClosed && !closed_) {
        // Transition: open → closed
        closed_    = true;
        closedFor_ = 1;

    } else if (isNowClosed && closed_) {
        closedFor_++;
        // Closed too long (>25 frames ≈ 1.7s): user is just tired — ignore
        if (closedFor_ > 25) {
            closed_ = false; closedFor_ = 0;
        }

    } else if (!isNowClosed && closed_) {
        // Transition: closed → open = blink complete
        closed_ = false;
        if (closedFor_ >= 2 && closedFor_ <= 25) {
            if (sinceClick_ < 18) {
                out = {ActionType::DOUBLE_CLICK, 0, 0, 0, "DOUBLE_CLICK"};
            } else {
                out = {ActionType::LEFT_CLICK,   0, 0, 0, "LEFT_CLICK"};
            }
            sinceClick_ = 0;
        }
        closedFor_ = 0;
    }

    return out;
}

void BlinkDetector::calibrate(const LandmarkFrame& f) {
    if (!f.isValid()) return;
    float e = (ear(f, true) + ear(f, false)) * 0.5f;
    earBuf_.push(e);
    if (earBuf_.full()) {
        baseline_  = earBuf_.average();
        threshold_ = baseline_ * 0.72f;
    }
}

void BlinkDetector::reset() {
    earBuf_.clear(); closed_ = false;
    closedFor_ = 0; sinceClick_ = 999;
}

// ══════════════════════════════════════════════════════════════════
//  HeadPoseEstimator
// ══════════════════════════════════════════════════════════════════

// Pitch: normalized nose position within forehead-to-chin range
// Positive = head down, Negative = head up
float HeadPoseEstimator::pitch(const LandmarkFrame& f) const {
    float fy = f[LandmarkFrame::FOREHEAD].y;
    float cy = f[LandmarkFrame::CHIN].y;
    float ny = f[LandmarkFrame::NOSE_TIP].y;
    float h  = std::abs(cy - fy);
    return (h > 1e-5f) ? (ny - fy) / h : 0.5f;
}

// Yaw: nose horizontal offset from face midpoint
float HeadPoseEstimator::yaw(const LandmarkFrame& f) const {
    float lx = f[LandmarkFrame::L_CHEEK].x;
    float rx = f[LandmarkFrame::R_CHEEK].x;
    float nx = f[LandmarkFrame::NOSE_TIP].x;
    float w  = std::abs(rx - lx);
    float mid = (lx + rx) * 0.5f;
    return (w > 1e-5f) ? (nx - mid) / w : 0.0f;
}

Action HeadPoseEstimator::process(const LandmarkFrame& f) {
    if (!enabled_ || !f.isValid() || !calibrated_) return {};

    float p = pitchK_.update(pitch(f));
    float y = yawK_.update(yaw(f));

    float dp = p - basePitch_;
    float dy = y - baseYaw_;

    float nT = 0.07f / sensitivity_;
    float sT = 0.07f / sensitivity_;

    int code = 0;
    if      (dp >  nT)  code = 1;   // nod down
    else if (dp < -nT)  code = 2;   // nod up
    else if (dy >  sT)  code = 3;   // turn right → escape
    else if (dy < -sT)  code = 4;   // turn left  → enter

    actionBuf_.push(code);
    int dom = actionBuf_.majority();

    switch (dom) {
        case 1: return {ActionType::SCROLL_DOWN, 0, 0, std::abs(dp)*4.0f, "NOD_DOWN"};
        case 2: return {ActionType::SCROLL_UP,   0, 0, std::abs(dp)*4.0f, "NOD_UP"};
        case 3: return {ActionType::KEY_ESCAPE,  0, 0, 0, "HEAD_RIGHT"};
        case 4: return {ActionType::KEY_ENTER,   0, 0, 0, "HEAD_LEFT"};
        default: return {};
    }
}

void HeadPoseEstimator::calibrate(const LandmarkFrame& f) {
    if (!f.isValid()) return;
    basePitch_   = pitchK_.update(pitch(f));
    baseYaw_     = yawK_.update(yaw(f));
    calibrated_  = true;
}

void HeadPoseEstimator::reset() {
    pitchK_.reset(); yawK_.reset();
    actionBuf_.clear(); calibrated_ = false;
}

// ══════════════════════════════════════════════════════════════════
//  ExpressionEngine
// ══════════════════════════════════════════════════════════════════

float ExpressionEngine::mouthRatio(const LandmarkFrame& f) const {
    float v = std::abs(f[LandmarkFrame::MOUTH_TOP].y - f[LandmarkFrame::MOUTH_BOT].y);
    float h = std::abs(f[LandmarkFrame::MOUTH_L].x   - f[LandmarkFrame::MOUTH_R].x);
    return (h > 1e-5f) ? v / h : 0.0f;
}

float ExpressionEngine::browRaise(const LandmarkFrame& f) const {
    // Distance between brow midpoint and eye top — larger when raised
    float lb = f[LandmarkFrame::L_BROW].y;
    float rb = f[LandmarkFrame::R_BROW].y;
    float le = f[LandmarkFrame::L_EYE_TOP].y;
    float re = f[LandmarkFrame::R_EYE_TOP].y;
    return std::abs(((le - lb) + (re - rb)) * 0.5f);
}

Action ExpressionEngine::process(const LandmarkFrame& f) {
    if (!enabled_ || !f.isValid()) return {};

    float mr = mouthRatio(f);
    float br = browRaise(f);

    float mT = (baseMouth_ + 0.20f) / sensitivity_;
    float bT = (baseBrow_  + 0.02f) * sensitivity_;

    int code = 0;
    if      (mr > mT)       code = 1;  // mouth open → virtual keyboard
    else if (br > bT)       code = 2;  // brow raise → right click

    exprBuf_.push(code);
    int dom = exprBuf_.majority();

    switch (dom) {
        case 1: return {ActionType::OPEN_KB,     0,0,0, "MOUTH_OPEN→KB"};
        case 2: return {ActionType::RIGHT_CLICK,  0,0,0, "BROW_RAISE→RC"};
        default: return {};
    }
}

void ExpressionEngine::calibrate(const LandmarkFrame& f) {
    if (!f.isValid()) return;
    baseMouth_  = mouthRatio(f);
    baseBrow_   = browRaise(f);
    calibrated_ = true;
}

void ExpressionEngine::reset() { exprBuf_.clear(); }

// ══════════════════════════════════════════════════════════════════
//  DwellClicker
// ══════════════════════════════════════════════════════════════════

void DwellClicker::feedGaze(float x, float y) {
    if (cx_ < 0) { cx_ = x; cy_ = y; return; }
    float d = std::sqrt((x-cx_)*(x-cx_) + (y-cy_)*(y-cy_));
    if (d < DWELL_RADIUS) {
        count_++;
    } else {
        count_ = 0;
        cx_ = x; cy_ = y;
    }
}

Action DwellClicker::process(const LandmarkFrame&) {
    if (!enabled_) return {};
    if (count_ >= DWELL_FRAMES) {
        count_ = 0;
        return {ActionType::DWELL_CLICK, cx_, cy_, 0.0f, "DWELL_CLICK"};
    }
    return {};
}

void DwellClicker::reset() { count_ = 0; cx_ = -1; cy_ = -1; }
