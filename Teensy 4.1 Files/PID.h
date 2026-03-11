#pragma once
#include <Arduino.h>

class PID
{
public:
    PID(float kp, float ki, float kd, float min_out, float max_out);
    void setTunings(float kp, float ki, float kd);
    void reset();
    float compute(float setpoint, float measurement);

private:
    float Kp, Ki, Kd;
    float integral;
    float prev_error;
    float prev_derivative;
    float out_min, out_max;
    uint32_t last_time;
};