class Motor
{
public:
    Motor(int pwmPin, int dirPin);

    void begin();
    void setVelocity(float cmd);
    void stop();

    void update();

    float getAngle();
    float getVelocity();

private:
    int pwmPin;
    int dirPin;

    float angle;
    float velocity;
};