#include <Arduino.h>
#include <Servo.h>
#include "MacConnection.h"

// ---------------- PINS ----------------
const int PAN_SERVO_PIN = 9;
const int TILT_SERVO_PIN = 10;

// ---------------- SERVO LIMITS ----------------
const int PAN_MIN_US = 1000;
const int PAN_MAX_US = 2000;
const int TILT_MIN_US = 1000;
const int TILT_MAX_US = 2000;

const int PAN_CENTER_US = 1500;
const int TILT_CENTER_US = 1500;

// ---------------- SERIAL ----------------
MacConnection mac(115200);

// ---------------- SERVOS ----------------
Servo panServo;
Servo tiltServo;

// ---------------- PID ----------------
PID panPID(1.0, 0.0, 0.0, -300.0, 300.0);
PID tiltPID(1.0, 0.0, 0.0, -300.0, 300.0);

// ---------------- TARGET / STATE ----------------
float errX = 0.0f;
float errY = 0.0f;

int panCmdUs = PAN_CENTER_US;
int tiltCmdUs = TILT_CENTER_US;

bool hasTarget = false;
elapsedMillis timeSinceLastTarget;

// ---------------- SETTINGS ----------------
const unsigned long TARGET_TIMEOUT_MS = 100;

// --------------------------------------------------
// Helpers
// --------------------------------------------------

void moveServos()
{
    panCmdUs = constrain(panCmdUs, PAN_MIN_US, PAN_MAX_US);
    tiltCmdUs = constrain(tiltCmdUs, TILT_MIN_US, TILT_MAX_US);

    panServo.writeMicroseconds(panCmdUs);
    tiltServo.writeMicroseconds(tiltCmdUs);
}

void resetControl()
{
    errX = 0.0f;
    errY = 0.0f;
    hasTarget = false;

    panPID.reset();
    tiltPID.reset();
}





void handleSerialLine(const String &msg)
{
    if (msg.length() == 0)
        return;

    float x, y;
    if (parseErrMessage(msg, x, y))
    {
        errX = x;
        errY = y;
        hasTarget = true;
        timeSinceLastTarget = 0;
        return;
    }

    float panKp, panKi, panKd, tiltKp, tiltKi, tiltKd;
    if (parseGainsMessage(msg, panKp, panKi, panKd, tiltKp, tiltKi, tiltKd))
    {
        panPID.setTunings(panKp, panKi, panKd);
        tiltPID.setTunings(tiltKp, tiltKi, tiltKd);
        return;
    }

    if (msg == "CENTER")
    {
        panCmdUs = PAN_CENTER_US;
        tiltCmdUs = TILT_CENTER_US;
        resetControl();
        moveServos();
        return;
    }

    if (msg == "STOP")
    {
        resetControl();
        return;
    }

    if (msg == "PING")
    {
        mac.sendLine("PONG");
        return;
    }
}

void updateControl()
{
    if (!hasTarget)
        return;

    // setpoint is 0 error
    float panOutput = panPID.compute(0.0f, errX);
    float tiltOutput = tiltPID.compute(0.0f, errY);

    // You may need to flip signs depending on servo direction
    panCmdUs += (int)panOutput;
    tiltCmdUs -= (int)tiltOutput;

    moveServos();
}

void checkTargetTimeout()
{
    if (hasTarget && timeSinceLastTarget > TARGET_TIMEOUT_MS)
    {
        resetControl();
    }
}

// --------------------------------------------------
// Arduino
// --------------------------------------------------

void setup()
{
    panServo.attach(PAN_SERVO_PIN);
    tiltServo.attach(TILT_SERVO_PIN);

    panCmdUs = PAN_CENTER_US;
    tiltCmdUs = TILT_CENTER_US;
    moveServos();

    mac.begin();
    mac.sendLine("[Teensy] setup complete");
}

void loop()
{
    mac.update();

    while (mac.available())
    {
        String msg = mac.readLine();
        handleSerialLine(msg);
    }

    checkTargetTimeout();
    updateControl();

    // optional debug at low rate
    static elapsedMillis debugTimer;
    if (debugTimer > 200)
    {
        debugTimer = 0;
        mac.send("[PAN_US] ");
        mac.sendLine(String(panCmdUs));

        mac.send("[TILT_US] ");
        mac.sendLine(String(tiltCmdUs));

        if (hasTarget)
        {
            mac.send("[ERR_X] ");
            mac.sendLine(String(errX, 2));

            mac.send("[ERR_Y] ");
            mac.sendLine(String(errY, 2));
        }
        else
        {
            mac.sendLine("[TARGET] none");
        }
    }

    delay(5);
}