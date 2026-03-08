

class PID
{
public:
    PID(float kp, float ki, float kd, float min_out, float max_out)
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

    void setTunings(float kp, float ki, float kd)
    {
        Kp = kp;
        Ki = ki;
        Kd = kd;
    }

    void reset()
    {
        integral = 0;
        prev_error = 0;
        prev_derivative = 0;
        last_time = micros();
    }

    float compute(float setpoint, float measurement)
    {

        uint32_t now = micros();
        float dt = (now - last_time) * 1e-6f;
        last_time = now;

        if (dt <= 0)
            return 0;

        float error = setpoint - measurement;

        // ----- Integral -----
        integral += error * dt;

        // anti-windup
        if (integral > out_max)
            integral = out_max;
        if (integral < out_min)
            integral = out_min;

        // ----- Derivative -----
        float derivative = (error - prev_error) / dt;

        // optional derivative smoothing
        float alpha = 0.7;
        derivative = alpha * prev_derivative + (1 - alpha) * derivative;

        prev_derivative = derivative;
        prev_error = error;

        // ----- PID output -----
        float output =
            Kp * error +
            Ki * integral +
            Kd * derivative;

        // output clamp
        if (output > out_max)
            output = out_max;
        if (output < out_min)
            output = out_min;

        return output;
    }

private:
    float Kp;
    float Ki;
    float Kd;

    float integral;
    float prev_error;
    float prev_derivative;

    float out_min;
    float out_max;

    uint32_t last_time;
};