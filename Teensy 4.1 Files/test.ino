#include <AccelStepper.h>

#define PAN_STEP 2
#define PAN_DIR 3

#define TILT_STEP 4
#define TILT_DIR 5

const int PAN_HALL_PIN = 9;
const int TILT_HALL_PIN = 10;

AccelStepper panStepper(AccelStepper::DRIVER, PAN_STEP, PAN_DIR);
AccelStepper tiltStepper(AccelStepper::DRIVER, TILT_STEP, TILT_DIR);

// -----------------------------
// motor / driver settings
// -----------------------------
const float MOTOR_FULL_STEPS_PER_REV = 200.0f;
const float MICROSTEPS = 16.0f;
const float STEPS_PER_REV = MOTOR_FULL_STEPS_PER_REV * MICROSTEPS;

// limits in RPM
const float MAX_SPEED_RPM = 300.0f;
const float ACCEL_RPM_PER_SEC = 400.0f;

// converted limits for AccelStepper
const float MAX_SPEED_STEPS_PER_SEC = (MAX_SPEED_RPM * STEPS_PER_REV) / 60.0f;
const float ACCEL_STEPS_PER_SEC2 = (ACCEL_RPM_PER_SEC * STEPS_PER_REV) / 60.0f;

// position units
const float POSITION_UNITS_TO_STEPS = STEPS_PER_REV;

// -----------------------------
// error -> velocity tuning
// units: RPM per pixel of error
// start small, then increase
// -----------------------------
float PAN_ERROR_TO_RPM = 0.7f;
float TILT_ERROR_TO_RPM = 0.7f;

// invert axis if needed
float PAN_DIRECTION_SIGN = 1.0f;
float TILT_DIRECTION_SIGN = 1.0f;

String inputBuffer = "";

enum ControlMode
{
    MODE_IDLE,
    MODE_VELOCITY,
    MODE_POSITION,
    MODE_ERROR
};

ControlMode mode = MODE_IDLE;

float commandedVelocityRPM = 0.0f;
float commandedPositionUnits = 0.0f;

float panError = 0.0f;
float tiltError = 0.0f;

float panCommandedRPM = 0.0f;
float tiltCommandedRPM = 0.0f;

unsigned long lastStatusPrint = 0;
const unsigned long STATUS_INTERVAL_MS = 200;

void setup()
{
    pinMode(PAN_HALL_PIN, INPUT_PULLUP);
    pinMode(TILT_HALL_PIN, INPUT_PULLUP);

    Serial.begin(115200);
    while (!Serial && millis() < 4000)
    {
    }

    panStepper.setMaxSpeed(MAX_SPEED_STEPS_PER_SEC);
    panStepper.setAcceleration(ACCEL_STEPS_PER_SEC2);
    panStepper.setMinPulseWidth(2);

    tiltStepper.setMaxSpeed(MAX_SPEED_STEPS_PER_SEC);
    tiltStepper.setAcceleration(ACCEL_STEPS_PER_SEC2);
    tiltStepper.setMinPulseWidth(2);

    findZeroPos(panStepper, PAN_HALL_PIN);
    findZeroPos(tiltStepper, TILT_HALL_PIN);

    Serial.println("[Teensy] Ready");
}

void loop()
{
    readSerialStream();

    switch (mode)
    {
    case MODE_VELOCITY:
        runVelocityMode();
        break;

    case MODE_POSITION:
        runPositionMode();
        break;

    case MODE_ERROR:
        runErrorMode();
        break;

    case MODE_IDLE:
    default:
        runIdleMode();
        break;
    }

    // printStatusPeriodically();
}

void readSerialStream()
{
    while (Serial.available() > 0)
    {
        char c = Serial.read();

        if (c == '\n')
        {
            inputBuffer.trim();

            if (inputBuffer.length() > 0)
            {
                parseCommand(inputBuffer);
            }

            inputBuffer = "";
        }
        else if (c != '\r')
        {
            inputBuffer += c;
        }
    }
}

void parseCommand(const String &cmd)
{
    if (cmd.startsWith("SET_VELOCITY:"))
    {
        handleSetVelocity(cmd);
    }
    else if (cmd.startsWith("SET_POSITION:"))
    {
        handleSetPosition(cmd);
    }
    else if (cmd.startsWith("TARGET:"))
    {
        handleTargetError(cmd);
    }
    else if (cmd == "STOP")
    {
        handleStop();
    }
    else if (cmd == "ZERO")
    {
        handleZero();
    }
    else if (cmd == "HEARTBEAT")
    {
        handleHeartbeat();
    }
    else
    {
        Serial.print("[Teensy] Unknown command: ");
        Serial.println(cmd);
    }
}

void handleSetVelocity(const String &cmd)
{
    const String prefix = "SET_VELOCITY:";
    String valueStr = cmd.substring(prefix.length());
    valueStr.trim();

    commandedVelocityRPM = valueStr.toFloat();
    commandedVelocityRPM = constrain(commandedVelocityRPM, -MAX_SPEED_RPM, MAX_SPEED_RPM);

    float speedStepsPerSec = rpmToStepsPerSec(commandedVelocityRPM);

    mode = MODE_VELOCITY;

    panStepper.setSpeed(speedStepsPerSec);
    tiltStepper.setSpeed(speedStepsPerSec);

    Serial.print("[Teensy] Velocity mode -> ");
    Serial.print(commandedVelocityRPM, 2);
    Serial.print(" RPM (");
    Serial.print(speedStepsPerSec, 1);
    Serial.println(" steps/s)");
}

void handleSetPosition(const String &cmd)
{
    const String prefix = "SET_POSITION:";
    String valueStr = cmd.substring(prefix.length());
    valueStr.trim();

    commandedPositionUnits = valueStr.toFloat();

    long targetSteps = lround(commandedPositionUnits * POSITION_UNITS_TO_STEPS);

    mode = MODE_POSITION;

    panStepper.moveTo(targetSteps);
    tiltStepper.moveTo(targetSteps);

    Serial.print("[Teensy] Position mode -> ");
    Serial.print(commandedPositionUnits, 3);
    Serial.print(" rev (");
    Serial.print(targetSteps);
    Serial.println(" steps)");
}

void handleTargetError(const String &cmd)
{
    const String prefix = "TARGET:";
    String valueStr = cmd.substring(prefix.length());
    valueStr.trim();

    int commaIndex = valueStr.indexOf(',');
    if (commaIndex < 0)
    {
        Serial.println("[Teensy] TARGET parse fail");
        return;
    }

    String panErrStr = valueStr.substring(0, commaIndex);
    String tiltErrStr = valueStr.substring(commaIndex + 1);

    panErrStr.trim();
    tiltErrStr.trim();

    panError = panErrStr.toFloat();
    tiltError = tiltErrStr.toFloat();

    mode = MODE_ERROR;
}

void handleStop()
{
    stopMotors();
    mode = MODE_IDLE;

    panError = 0.0f;
    tiltError = 0.0f;
    panCommandedRPM = 0.0f;
    tiltCommandedRPM = 0.0f;

    Serial.println("[Teensy] STOP");
}

void handleZero()
{
    panStepper.setCurrentPosition(0);
    tiltStepper.setCurrentPosition(0);

    panStepper.moveTo(0);
    tiltStepper.moveTo(0);

    panStepper.setSpeed(0.0f);
    tiltStepper.setSpeed(0.0f);

    commandedVelocityRPM = 0.0f;
    commandedPositionUnits = 0.0f;
    panError = 0.0f;
    tiltError = 0.0f;
    panCommandedRPM = 0.0f;
    tiltCommandedRPM = 0.0f;

    mode = MODE_IDLE;

    Serial.println("[Teensy] ZERO");
}

void handleHeartbeat()
{
    Serial.print("[Teensy] HEARTBEAT_ACK");
    Serial.print(" millis=");
    Serial.println(millis());
}

void runVelocityMode()
{
    panStepper.runSpeed();
    tiltStepper.runSpeed();
}

void runPositionMode()
{
    panStepper.run();
    tiltStepper.run();
}

void runErrorMode()
{
    panCommandedRPM = PAN_DIRECTION_SIGN * panError * PAN_ERROR_TO_RPM;
    tiltCommandedRPM = TILT_DIRECTION_SIGN * tiltError * TILT_ERROR_TO_RPM;

    panCommandedRPM = constrain(panCommandedRPM, -MAX_SPEED_RPM, MAX_SPEED_RPM);
    tiltCommandedRPM = constrain(tiltCommandedRPM, -MAX_SPEED_RPM, MAX_SPEED_RPM);

    float panStepsPerSec = rpmToStepsPerSec(panCommandedRPM);
    float tiltStepsPerSec = rpmToStepsPerSec(tiltCommandedRPM);

    panStepper.setSpeed(panStepsPerSec);
    tiltStepper.setSpeed(tiltStepsPerSec);

    panStepper.runSpeed();
    tiltStepper.runSpeed();
}

void runIdleMode()
{
}

void stopMotors()
{
    panStepper.setSpeed(0.0f);
    tiltStepper.setSpeed(0.0f);

    long panNow = panStepper.currentPosition();
    long tiltNow = tiltStepper.currentPosition();

    panStepper.moveTo(panNow);
    tiltStepper.moveTo(tiltNow);
}

float rpmToStepsPerSec(float rpm)
{
    return (rpm * STEPS_PER_REV) / 60.0f;
}

void findZeroPos(AccelStepper &motor, int HALL_PIN)
{
    Serial.println("finding 0");

    const float SEARCH_SPEED = 400.0f;
    const float CREEP_SPEED = 80.0f;

    int startState = digitalRead(HALL_PIN);

    motor.setSpeed(SEARCH_SPEED);
    while (digitalRead(HALL_PIN) == startState)
    {
        motor.runSpeed();
    }

    int newState = digitalRead(HALL_PIN);

    motor.setSpeed(CREEP_SPEED);
    while (digitalRead(HALL_PIN) == newState)
    {
        motor.runSpeed();
    }

    motor.setSpeed(0);
    motor.setCurrentPosition(0);

    Serial.println("ZERO FOUND");
}