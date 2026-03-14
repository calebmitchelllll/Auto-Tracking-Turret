#include "PID.h"
#include <math.h>

PID::PID(float integral_limit_,
         float output_limit_,
         float derivative_alpha_,
         float deadband_)
{
    integral_limit = integral_limit_;
    output_limit = output_limit_;
    derivative_alpha = derivative_alpha_;
    deadband = deadband_;

    reset();
}

void PID::reset()
{
    pan_integral = 0;
    pan_prev_error = 0;
    pan_d = 0;

    tilt_integral = 0;
    tilt_prev_error = 0;
    tilt_d = 0;
}

float PID::updatePan(float target, float actual, float dt)
{
    PIDValues gains = getPIDValues();

    float error = target - actual;

    if (fabs(error) < deadband)
        return 0;

    // integral
    pan_integral += error * dt;

    if (pan_integral > integral_limit)
        pan_integral = integral_limit;
    if (pan_integral < -integral_limit)
        pan_integral = -integral_limit;

    // derivative (filtered)
    float raw_d = (error - pan_prev_error) / dt;
    pan_d = derivative_alpha * pan_d + (1 - derivative_alpha) * raw_d;

    pan_prev_error = error;

    float out =
        -(gains.pan_kp * error +
          gains.pan_ki * pan_integral +
          gains.pan_kd * pan_d);

    if (out > output_limit)
        out = output_limit;
    if (out < -output_limit)
        out = -output_limit;

    return out;
}

float PID::updateTilt(float target, float actual, float dt)
{
    PIDValues gains = getPIDValues();

    float error = target - actual;

    if (fabs(error) < deadband)
        return 0;

    // integral
    tilt_integral += error * dt;

    if (tilt_integral > integral_limit)
        tilt_integral = integral_limit;
    if (tilt_integral < -integral_limit)
        tilt_integral = -integral_limit;

    // derivative (filtered)
    float raw_d = (error - tilt_prev_error) / dt;
    tilt_d = derivative_alpha * tilt_d + (1 - derivative_alpha) * raw_d;

    tilt_prev_error = error;

    float out =
        -(gains.tilt_kp * error +
          gains.tilt_ki * tilt_integral +
          gains.tilt_kd * tilt_d);

    if (out > output_limit)
        out = output_limit;
    if (out < -output_limit)
        out = -output_limit;

    return out;
}