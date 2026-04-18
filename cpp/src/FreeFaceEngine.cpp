#include "../include/FreeFaceEngine.h"
#include <fstream>
#include <cstring>
#include <stdexcept>

FreeFaceEngine::FreeFaceEngine()
    : gaze_ (std::make_unique<GazeTracker>())
    , blink_(std::make_unique<BlinkDetector>())
    , head_ (std::make_unique<HeadPoseEstimator>())
    , expr_ (std::make_unique<ExpressionEngine>())
    , dwell_(std::make_unique<DwellClicker>())
{}

// ─── Build LandmarkFrame from flat float array ───────────────────
LandmarkFrame FreeFaceEngine::buildFrame(const float* data, int count) const {
    LandmarkFrame f;
    int pts = count / 3;
    if (pts > LandmarkFrame::COUNT) pts = LandmarkFrame::COUNT;
    for (int i = 0; i < pts; i++)
        f.set(i, data[i*3], data[i*3+1], data[i*3+2]);
    return f;
}

// ─── Main per-frame processing ───────────────────────────────────
Action FreeFaceEngine::processFrame(const float* landmarks, int count) {
    if (!landmarks || count < 3) return {};

    LandmarkFrame frame;
    try {
        frame = buildFrame(landmarks, count);
    } catch (...) {
        return {};
    }

    frameCount_++;
    noBlinkFrames_++;

    // ── Calibration mode ─────────────────────────────────────────
    if (calibrating_) {
        doCalibrate(frame);
        return {ActionType::NONE, 0, 0, 0, "CALIBRATING"};
    }

    // ── Step 1: Get gaze position (always runs) ───────────────────
    Action gaze = gaze_->process(frame);

    // ── Step 2: Feed gaze into dwell tracker ─────────────────────
    if (gaze.type == ActionType::MOUSE_MOVE && profile_.dwellOn) {
        dwell_->feedGaze(gaze.x, gaze.y);
    }

    // ── Step 3: Check dwell first (highest priority click) ───────
    if (profile_.dwellOn) {
        Action dw = dwell_->process(frame);
        if (!dw.isNone()) return dw;
    }

    // ── Step 4: Blink detection ───────────────────────────────────
    if (profile_.blinkOn) {
        Action bl = blink_->process(frame);
        if (!bl.isNone()) {
            noBlinkFrames_ = 0;
            blinkCount_++;
            return bl;
        }
    }

    // ── Step 5: Expression detection ─────────────────────────────
    if (profile_.expressionOn) {
        Action ex = expr_->process(frame);
        if (!ex.isNone()) return ex;
    }

    // ── Step 6: Head pose ─────────────────────────────────────────
    if (profile_.headOn) {
        Action hp = head_->process(frame);
        if (!hp.isNone()) return hp;
    }

    // ── Step 7: Return gaze move (lowest priority, always sent) ──
    return gaze;
}

// ─── Calibration ─────────────────────────────────────────────────
void FreeFaceEngine::startCalibration() {
    calibrating_  = true;
    calibFrames_  = 0;
    gaze_->reset();
    blink_->reset();
    head_->reset();
    expr_->reset();
}

void FreeFaceEngine::doCalibrate(const LandmarkFrame& frame) {
    // Collect calibration samples from all detectors
    gaze_->calibrate(frame);
    blink_->calibrate(frame);
    head_->calibrate(frame);
    expr_->calibrate(frame);
    calibFrames_++;

    if (calibFrames_ >= CALIB_TOTAL) {
        calibrating_ = false;
        // Save calibration into profile
        saveProfile("profiles/current.profile");
    }
}

// ─── Profile ─────────────────────────────────────────────────────
void FreeFaceEngine::applyProfile() {
    gaze_->setEnabled(profile_.gazeOn);
    gaze_->setSensitivity(profile_.gazeSens);
    blink_->setEnabled(profile_.blinkOn);
    blink_->setSensitivity(profile_.blinkSens);
    head_->setEnabled(profile_.headOn);
    head_->setSensitivity(profile_.headSens);
    expr_->setEnabled(profile_.expressionOn);
    expr_->setSensitivity(profile_.exprSens);
    dwell_->setEnabled(profile_.dwellOn);
}

bool FreeFaceEngine::loadProfile(const char* path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return false;
    f.read(reinterpret_cast<char*>(&profile_), sizeof(profile_));
    applyProfile();
    return f.good();
}

bool FreeFaceEngine::saveProfile(const char* path) const {
    std::ofstream f(path, std::ios::binary);
    if (!f) return false;
    f.write(reinterpret_cast<const char*>(&profile_), sizeof(profile_));
    return f.good();
}

// ─── AccessibilityProfile save/load ──────────────────────────────
bool AccessibilityProfile::save(const char* path) const {
    std::ofstream f(path, std::ios::binary);
    if (!f) return false;
    f.write(reinterpret_cast<const char*>(this), sizeof(*this));
    return f.good();
}

bool AccessibilityProfile::load(const char* path) {
    std::ifstream f(path, std::ios::binary);
    if (!f) return false;
    f.read(reinterpret_cast<char*>(this), sizeof(*this));
    return f.good();
}
