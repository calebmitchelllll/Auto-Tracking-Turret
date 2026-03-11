#include "PID.h"

PID::PID(float kp, float ki, float kd, float min_out, float max_out)
{
    Kp = kp;
    Ki = ki;
    Kd = kd;

    out_min = min_out;
    out_max = max_out;

    integral = 0;
    prev_error = 0;
    prev_derivative = 0;
    last_time = micros();
}

void PID::setTunings(float kp, float ki, float kd)
{
    Kp = kp;
    Ki = ki;
    Kd = kd;
}

void PID::reset()
{
    integral = 0;
    prev_error = 0;
    prev_derivative = 0;
    last_time = micros();
}

float PID::compute(float setpoint, float measurement)
{
    uint32_t now = micros();
    float dt = (now - last_time) * 1e-6f;
    last_time = now;

    if (dt <= 0)
        return 0;

    float error = setpoint - measurement;

    integral += error * dt;

    if (integral > out_max)
        integral = out_max;
    if (integral < out_min)
        integral = out_min;

    float derivative = (error - prev_error) / dt;

    float alpha = 0.7;
    derivative = alpha * prev_derivative + (1 - alpha) * derivative;

    prev_derivative = derivative;
    prev_error = error;

    float output =
        Kp * error +
        Ki * integral +
        Kd * derivative;

    if (output > out_max)
        output = out_max;
    if (output < out_min)
        output = out_min;

    return output;
}