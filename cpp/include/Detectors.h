#pragma once
#include "LandmarkFrame.h"
#include "Filters.h"
#include <string>
#include <cmath>

// ─── Action ───────────────────────────────────────────────────────
// What the engine outputs each frame

enum class ActionType : int {
    NONE         = 0,
    MOUSE_MOVE   = 1,
    LEFT_CLICK   = 2,
    RIGHT_CLICK  = 3,
    DOUBLE_CLICK = 4,
    SCROLL_UP    = 5,
    SCROLL_DOWN  = 6,
    KEY_ENTER    = 7,
    KEY_ESCAPE   = 8,
    KEY_SPACE    = 9,
    DWELL_CLICK  = 10,
    OPEN_KB      = 11   // open virtual keyboard
};

struct Action {
    ActionType  type      = ActionType::NONE;
    float       x         = 0.0f;   // screen x, 0-1 normalized
    float       y         = 0.0f;   // screen y, 0-1 normalized
    float       magnitude = 0.0f;   // scroll amount
    const char* label     = "NONE"; // for HUD display

    bool isNone() const { return type == ActionType::NONE; }
};

// ─── FaceController (Abstract Base) ───────────────────────────────
// Every detector inherits from this.
// Pure virtual: process(), getName(), calibrate(), reset()

class FaceController {
protected:
    bool  enabled_     = true;
    float sensitivity_ = 1.0f;

public:
    virtual ~FaceController() = default;

    // Pure virtual interface — must implement in each derived class
    virtual Action      process(const LandmarkFrame& frame) = 0;
    virtual const char* getName() const = 0;
    virtual void        calibrate(const LandmarkFrame& frame) = 0;
    virtual void        reset() = 0;

    // Common setters/getters
    void  setEnabled(bool e)      { enabled_     = e; }
    void  setSensitivity(float s) { sensitivity_ = s; }
    bool  isEnabled()       const { return enabled_; }
    float getSensitivity()  const { return sensitivity_; }

    // Operator overload: describe controller pipeline
    std::string operator+(const FaceController& o) const {
        return std::string(getName()) + " → " + o.getName();
    }
};

// ─── GazeTracker ──────────────────────────────────────────────────
// Maps average iris position to normalized screen coordinates
// Output: MOUSE_MOVE with x,y in [0,1]

class GazeTracker : public FaceController {
    KalmanFilter<float> kx_{1e-3f, 4e-2f};
    KalmanFilter<float> ky_{1e-3f, 4e-2f};

    // Calibration bounds (set during calibrate())
    float xMin_ = 0.33f, xMax_ = 0.67f;
    float yMin_ = 0.33f, yMax_ = 0.67f;

    float mapAxis(float v, float lo, float hi) const;

public:
    Action      process(const LandmarkFrame& f) override;
    const char* getName()                  const override { return "GazeTracker"; }
    void        calibrate(const LandmarkFrame& f)  override;
    void        reset()                            override;

    float lastX() const { return kx_.value(); }
    float lastY() const { return ky_.value(); }
};

// ─── BlinkDetector ────────────────────────────────────────────────
// Eye Aspect Ratio (EAR) based blink detection
// Single slow blink  → LEFT_CLICK
// Two blinks < 600ms → DOUBLE_CLICK
// Eyes closed > 2s   → ignored (natural fatigue close)

class BlinkDetector : public FaceController {
    CircularBuffer<float, 8> earBuf_;
    float threshold_  = 0.22f;   // EAR below this = closed
    float baseline_   = 0.30f;   // calibrated open-eye EAR

    bool  closed_     = false;
    int   closedFor_  = 0;       // frames eye has been closed
    int   sinceClick_ = 999;     // frames since last click (for double detect)

    float ear(const LandmarkFrame& f, bool left) const;

public:
    Action      process(const LandmarkFrame& f) override;
    const char* getName()                  const override { return "BlinkDetector"; }
    void        calibrate(const LandmarkFrame& f)  override;
    void        reset()                            override;
};

// ─── HeadPoseEstimator ────────────────────────────────────────────
// Estimates pitch (up/down nod) and yaw (left/right shake)
// from facial geometry ratios — no PnP solver needed
// Nod down  → SCROLL_DOWN
// Nod up    → SCROLL_UP
// Shake L/R → ENTER / ESCAPE

class HeadPoseEstimator : public FaceController {
    KalmanFilter<float> pitchK_{1e-3f, 6e-2f};
    KalmanFilter<float> yawK_  {1e-3f, 6e-2f};

    float basePitch_ = 0, baseYaw_ = 0;
    bool  calibrated_ = false;

    CircularBuffer<int, 10> actionBuf_; // debounce output

    float pitch(const LandmarkFrame& f) const;
    float yaw  (const LandmarkFrame& f) const;

public:
    Action      process(const LandmarkFrame& f) override;
    const char* getName()                  const override { return "HeadPoseEstimator"; }
    void        calibrate(const LandmarkFrame& f)  override;
    void        reset()                            override;
};

// ─── ExpressionEngine ─────────────────────────────────────────────
// Detects mouth open → OPEN_KB (virtual keyboard)
// Eyebrow raise     → RIGHT_CLICK
// Uses CircularBuffer majority vote to debounce

class ExpressionEngine : public FaceController {
    float baseMouth_   = 0.12f;
    float baseBrow_    = 0.06f;
    bool  calibrated_  = false;

    CircularBuffer<int, 8> exprBuf_;

    float mouthRatio (const LandmarkFrame& f) const;
    float browRaise  (const LandmarkFrame& f) const;

public:
    Action      process(const LandmarkFrame& f) override;
    const char* getName()                  const override { return "ExpressionEngine"; }
    void        calibrate(const LandmarkFrame& f)  override;
    void        reset()                            override;
};

// ─── DwellClicker ─────────────────────────────────────────────────
// If gaze remains within a small radius for DWELL_FRAMES → auto click
// Alternative for users who cannot blink (e.g. locked-in syndrome)
// Enabled via profile setting

class DwellClicker : public FaceController {
    static constexpr int   DWELL_FRAMES  = 40;   // ~2.7s at 15fps
    static constexpr float DWELL_RADIUS  = 0.025f;

    float cx_ = -1, cy_ = -1;   // current dwell center
    int   count_ = 0;

public:
    // Call this with gaze output BEFORE calling process()
    void  feedGaze(float x, float y);

    Action      process(const LandmarkFrame& f) override;
    const char* getName()                  const override { return "DwellClicker"; }
    void        calibrate(const LandmarkFrame&)    override {}
    void        reset()                            override;

    float progress() const { return float(count_) / DWELL_FRAMES; }
};
