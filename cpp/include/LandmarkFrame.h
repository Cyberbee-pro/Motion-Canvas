#pragma once
#include <array>
#include <cmath>
#include <stdexcept>

// ─── Point3D ──────────────────────────────────────────────────────
struct Point3D {
    float x = 0, y = 0, z = 0;
    Point3D() = default;
    Point3D(float x, float y, float z) : x(x), y(y), z(z) {}

    Point3D  operator+(const Point3D& o) const { return {x+o.x, y+o.y, z+o.z}; }
    Point3D  operator-(const Point3D& o) const { return {x-o.x, y-o.y, z-o.z}; }
    Point3D  operator*(float s)          const { return {x*s,   y*s,   z*s};   }
    bool     operator==(const Point3D& o)const { return x==o.x&&y==o.y&&z==o.z;}
    float    norm()                      const { return std::sqrt(x*x+y*y+z*z);}
    float    dist(const Point3D& o)      const { return (*this - o).norm(); }
};

// ─── LandmarkFrame ────────────────────────────────────────────────
// Wraps one frame of 478 MediaPipe Face Mesh landmarks
class LandmarkFrame {
public:
    static constexpr int COUNT = 478;

private:
    std::array<Point3D, COUNT> pts;
    bool valid_ = false;

public:
    LandmarkFrame() = default;

    void set(int i, float x, float y, float z) {
        if (i < 0 || i >= COUNT) throw std::out_of_range("Landmark index out of range");
        pts[i] = {x, y, z};
        valid_ = true;
    }

    // operator[] for read access: frame[33] gives left eye outer corner
    const Point3D& operator[](int i) const {
        if (i < 0 || i >= COUNT) throw std::out_of_range("Landmark index out of range");
        return pts[i];
    }

    bool isValid()   const { return valid_; }
    void invalidate()      { valid_ = false; }

    // ── Key MediaPipe Face Mesh indices ──────────────────────────
    // Left eye
    static constexpr int L_EYE_TOP   = 159;
    static constexpr int L_EYE_BOT   = 145;
    static constexpr int L_EYE_IN    = 133;   // inner corner
    static constexpr int L_EYE_OUT   = 33;    // outer corner
    // Right eye
    static constexpr int R_EYE_TOP   = 386;
    static constexpr int R_EYE_BOT   = 374;
    static constexpr int R_EYE_IN    = 362;
    static constexpr int R_EYE_OUT   = 263;
    // Irises (MediaPipe iris refinement model)
    static constexpr int L_IRIS      = 468;
    static constexpr int R_IRIS      = 473;
    // Head geometry
    static constexpr int NOSE_TIP    = 1;
    static constexpr int FOREHEAD    = 10;
    static constexpr int CHIN        = 152;
    static constexpr int L_CHEEK     = 234;
    static constexpr int R_CHEEK     = 454;
    // Mouth
    static constexpr int MOUTH_TOP   = 13;
    static constexpr int MOUTH_BOT   = 14;
    static constexpr int MOUTH_L     = 61;
    static constexpr int MOUTH_R     = 291;
    // Eyebrows
    static constexpr int L_BROW      = 105;
    static constexpr int R_BROW      = 334;
};
