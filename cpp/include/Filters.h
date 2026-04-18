#pragma once
#include <array>

// ─── KalmanFilter<T> ──────────────────────────────────────────────
// 1D discrete Kalman filter — smooths noisy measurements
// Used for: gaze x/y coordinates, head pitch/yaw, EAR values
//
// How it works:
//   Predict: errorCov += processNoise
//   Update:  gain = errorCov / (errorCov + measureNoise)
//            estimate += gain * (measurement - estimate)
//            errorCov  = (1 - gain) * errorCov
//
// processNoise (Q): how much the true value can change per step
//   → higher Q = faster to follow sudden changes
// measureNoise (R): how much we distrust sensor readings
//   → higher R = more smoothing, more lag

template<typename T = float>
class KalmanFilter {
    T estimate_   = T(0);
    T errorCov_   = T(1);
    T processNoise_;   // Q
    T measureNoise_;   // R
    bool init_    = false;

public:
    explicit KalmanFilter(T Q = T(1e-3), T R = T(5e-2))
        : processNoise_(Q), measureNoise_(R) {}

    T update(T measurement) {
        if (!init_) {
            estimate_ = measurement;
            init_     = true;
            return estimate_;
        }
        // Predict
        errorCov_ += processNoise_;
        // Kalman gain
        T gain     = errorCov_ / (errorCov_ + measureNoise_);
        // Update estimate
        estimate_  = estimate_ + gain * (measurement - estimate_);
        errorCov_  = (T(1) - gain) * errorCov_;
        return estimate_;
    }

    T   value() const { return estimate_; }
    void reset()      { init_ = false; errorCov_ = T(1); }
    void setNoise(T Q, T R) { processNoise_ = Q; measureNoise_ = R; }
};

// ─── CircularBuffer<T, N> ─────────────────────────────────────────
// Fixed-size ring buffer — zero heap allocation
// Used for: debounce queues, majority voting, rolling average
//
// All accessors are newest-first: buf[0] = most recent

template<typename T, int N>
class CircularBuffer {
    std::array<T, N> data_ = {};
    int  head_  = 0;
    int  count_ = 0;

public:
    void push(const T& v) {
        data_[head_] = v;
        head_ = (head_ + 1) % N;
        if (count_ < N) count_++;
    }

    // buf[0] = newest, buf[count-1] = oldest
    const T& operator[](int i) const {
        return data_[(head_ - 1 - i + N) % N];
    }

    int  size()  const { return count_; }
    bool full()  const { return count_ == N; }
    bool empty() const { return count_ == 0; }
    void clear()       { head_ = 0; count_ = 0; }

    // Returns most frequent element (for enum/int debouncing)
    T majority() const {
        if (count_ == 0) return T{};
        T best = (*this)[0];
        int bestN = 0;
        for (int i = 0; i < count_; i++) {
            int c = 0;
            const T& v = (*this)[i];
            for (int j = 0; j < count_; j++)
                if ((*this)[j] == v) c++;
            if (c > bestN) { bestN = c; best = v; }
        }
        return best;
    }

    // Rolling average (numeric types only)
    T average() const {
        if (count_ == 0) return T{};
        T sum = T{};
        for (int i = 0; i < count_; i++) sum = sum + (*this)[i];
        return sum * (T(1) / T(count_));
    }

    // Check if all values satisfy a condition
    template<typename Pred>
    bool all(Pred p) const {
        for (int i = 0; i < count_; i++)
            if (!p((*this)[i])) return false;
        return count_ > 0;
    }
};
