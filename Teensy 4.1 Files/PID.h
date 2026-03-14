#pragma once

struct PIDValues
{
    float pan_kp;
    float pan_ki;
    float pan_kd;

    float tilt_kp;
    float tilt_ki;
    float tilt_kd;
};

// this function exists somewhere else
PIDValues getPIDValues();

class PID
{
public:
    PID(float integral_limit, float output_limit, float derivative_alpha, float deadband);

    float updatePan(float target, float actual, float dt);
    float updateTilt(float target, float actual, float dt);

    void reset();

private:
    float pan_integral;
    float pan_prev_error;
    float pan_d;

    float tilt_integral;
    float tilt_prev_error;
    float tilt_d;

    float integral_limit;
    float output_limit;
    float derivative_alpha;
    float deadband;
};