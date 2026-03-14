#include "Motor.h"
#include <Arduino.h>
#include <math.h>

Motor::Motor(int pwmPin_, int dirPin_)
{
    pwmPin = pwmPin_;
    dirPin = dirPin_;

    angle = 0.0f;
    velocity = 0.0f;
    commandedVelocity = 0.0f;
}

void Motor::begin()
{
    pinMode(pwmPin, OUTPUT);
    pinMode(dirPin, OUTPUT);

    analogWrite(pwmPin, 0);
    digitalWrite(dirPin, LOW);
}

void Motor::setVelocity(float cmd)
{
    commandedVelocity = cmd;
}

void Motor::stop()
{
    commandedVelocity = 0.0f;
    velocity = 0.0f;
    analogWrite(pwmPin, 0);
}

void Motor::update()
{
    float cmd = commandedVelocity;

    if (cmd > 255.0f)
        cmd = 255.0f;
    if (cmd < -255.0f)
        cmd = -255.0f;

    if (fabs(cmd) < 1.0f)
    {
        analogWrite(pwmPin, 0);
        velocity = 0.0f;
        return;
    }

    if (cmd >= 0.0f)
    {
        digitalWrite(dirPin, HIGH);
        analogWrite(pwmPin, (int)cmd);
    }
    else
    {
        digitalWrite(dirPin, LOW);
        analogWrite(pwmPin, (int)(-cmd));
    }

    velocity = cmd;
}

float Motor::getAngle()
{
    return angle;
}

float Motor::getVelocity()
{
    return velocity;
}