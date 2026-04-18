#pragma once
#include "Detectors.h"
#include <vector>
#include <memory>
#include <string>

// ─── AccessibilityProfile ─────────────────────────────────────────
// Per-user settings saved to disk so calibration persists

struct AccessibilityProfile {
    char   name[64]         = "default";

    // Feature toggles
    bool   gazeOn           = true;
    bool   blinkOn          = true;
    bool   headOn           = true;
    bool   expressionOn     = true;
    bool   dwellOn          = false;   // disabled by default; enable for severe cases
    bool   voiceOn          = true;

    // Sensitivity (0.5 = reduced, 1.0 = normal, 2.0 = amplified)
    float  gazeSens         = 1.0f;
    float  blinkSens        = 1.0f;
    float  headSens         = 1.0f;
    float  exprSens         = 1.0f;

    // Calibration values (written by calibrate())
    float  earThreshold     = 0.22f;
    float  nodThreshold     = 0.06f;
    float  mouthThreshold   = 0.35f;
    float  browThreshold    = 0.04f;
    float  gazeXmin         = 0.33f;
    float  gazeXmax         = 0.67f;
    float  gazeYmin         = 0.33f;
    float  gazeYmax         = 0.67f;

    bool save(const char* path) const;
    bool load(const char* path);
};

// ─── FreeFaceEngine ───────────────────────────────────────────────
// Owns all detectors, runs them in priority order each frame,
// returns the highest-priority non-NONE action.
//
// Priority: Dwell > Blink > Gaze+Expression > Head
// (Dwell overrides blink to prevent conflict)

class FreeFaceEngine {
    // Detector pipeline — owned via unique_ptr
    std::unique_ptr<GazeTracker>       gaze_;
    std::unique_ptr<BlinkDetector>     blink_;
    std::unique_ptr<HeadPoseEstimator> head_;
    std::unique_ptr<ExpressionEngine>  expr_;
    std::unique_ptr<DwellClicker>      dwell_;

    AccessibilityProfile profile_;

    // Fatigue tracking
    int frameCount_    = 0;
    int blinkCount_    = 0;
    int noBlinkFrames_ = 0;   // frames without any blink (eye strain monitor)

    // Calibration state
    bool  calibrating_    = false;
    int   calibFrames_    = 0;
    static constexpr int CALIB_TOTAL = 45;   // 3 seconds at 15fps

public:
    FreeFaceEngine();

    // ── Main entry point ─────────────────────────────────────────
    // Called by Python every processed frame.
    // landmarks: flat array of [x0,y0,z0, x1,y1,z1, ... x477,y477,z477]
    // Returns Action with result.
    Action processFrame(const float* landmarks, int count);

    // ── Calibration ──────────────────────────────────────────────
    void startCalibration();
    bool calibrating()     const { return calibrating_; }
    int  calibProgress()   const { return calibFrames_; }
    int  calibTotal()      const { return CALIB_TOTAL; }

    // ── Profile ──────────────────────────────────────────────────
    bool loadProfile(const char* path);
    bool saveProfile(const char* path) const;
    void applyProfile();

    // ── Runtime toggles ──────────────────────────────────────────
    void setGaze      (bool on) { gaze_->setEnabled(on);  profile_.gazeOn = on; }
    void setBlink     (bool on) { blink_->setEnabled(on); profile_.blinkOn = on; }
    void setHead      (bool on) { head_->setEnabled(on);  profile_.headOn = on; }
    void setExpression(bool on) { expr_->setEnabled(on);  profile_.expressionOn = on; }
    void setDwell     (bool on) { dwell_->setEnabled(on); profile_.dwellOn = on; }

    // ── Stats (for HUD) ──────────────────────────────────────────
    int  frameCount()  const { return frameCount_; }
    int  blinkCount()  const { return blinkCount_; }
    bool isFatigued()  const { return noBlinkFrames_ > 300; } // 20s no blink
    float dwellProgress() const { return dwell_->progress(); }

private:
    LandmarkFrame buildFrame(const float* data, int count) const;
    void          doCalibrate(const LandmarkFrame& frame);
};
