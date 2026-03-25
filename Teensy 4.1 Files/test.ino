#include <AccelStepper.h>

#define PAN_STEP 2
#define PAN_DIR 3

#define TILT_STEP 4
#define TILT_DIR 5

const int PAN_HALL_PIN = 9;
const int TILT_HALL_PIN = 10;

AccelStepper panStepper(AccelStepper::DRIVER, PAN_STEP, PAN_DIR);
AccelStepper tiltStepper(AccelStepper::DRIVER, TILT_STEP, TILT_DIR);

const float MOTOR_FULL_STEPS_PER_REV = 200.0f;
const float MICROSTEPS = 8.0f;
const float STEPS_PER_REV = MOTOR_FULL_STEPS_PER_REV * MICROSTEPS; // 1600

const float MAX_SPEED_RPM = 600.0f;
const float ACCEL_RPM_PER_SEC = 800.0f;

// Derived — everything flows from RPM * STEPS_PER_REV / 60
const float MAX_SPEED_STEPS_PER_SEC = (MAX_SPEED_RPM * STEPS_PER_REV) / 60.0f;  // 8000 steps/s
const float ACCEL_STEPS_PER_SEC2 = (ACCEL_RPM_PER_SEC * STEPS_PER_REV) / 60.0f; // 10666 steps/s²

const float POSITION_UNITS_TO_STEPS = STEPS_PER_REV;

float PAN_DIRECTION_SIGN = 1.0f;
float TILT_DIRECTION_SIGN = 1.0f;

// PID gains (updated via SET_GAINS:)
float panKp = 0.7f;
float panKi = 0.0f;
float panKd = 0.0f;

float tiltKp = 0.7f;
float tiltKi = 0.0f;
float tiltKd = 0.0f;

// PID state
float panIntegral = 0.0f;
float tiltIntegral = 0.0f;
float panPrevError = 0.0f;
float tiltPrevError = 0.0f;

const float INTEGRAL_MAX_RPM = 50.0f;

unsigned long lastPidTime = 0;

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

bool panWithinLimits(float speed)
{
    long pos = panStepper.currentPosition();
    if (speed > 0 && pos >= PAN_MAX_STEPS)
        return false;
    if (speed < 0 && pos <= PAN_MIN_STEPS)
        return false;
    return true;
}

bool tiltWithinLimits(float speed)
{
    long pos = tiltStepper.currentPosition();
    if (speed > 0 && pos >= TILT_MAX_STEPS)
        return false;
    if (speed < 0 && pos <= TILT_MIN_STEPS)
        return false;
    return true;
}

// Clamp a target step count to the legal range
long clampPanTarget(long target) { return constrain(target, PAN_MIN_STEPS, PAN_MAX_STEPS); }
long clampTiltTarget(long target) { return constrain(target, TILT_MIN_STEPS, TILT_MAX_STEPS); }

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

    lastPidTime = micros();

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
                parseCommand(inputBuffer);
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
        handleSetVelocity(cmd);
    else if (cmd.startsWith("SET_POSITION:"))
        handleSetPosition(cmd);
    else if (cmd.startsWith("TARGET:"))
        handleTargetError(cmd);
    else if (cmd.startsWith("SET_GAINS:"))
        handleSetGains(cmd);
    else if (cmd == "STOP")
        handleStop();
    else if (cmd == "ZERO")
        handleZero();
    else if (cmd == "HEARTBEAT")
        handleHeartbeat();
    else
    {
        Serial.print("[Teensy] Unknown command: ");
        Serial.println(cmd);
    }
}

void handleSetVelocity(const String &cmd)
{
    String valueStr = cmd.substring(strlen("SET_VELOCITY:"));
    valueStr.trim();
    commandedVelocityRPM = constrain(valueStr.toFloat(), -MAX_SPEED_RPM, MAX_SPEED_RPM);
    float spd = rpmToStepsPerSec(commandedVelocityRPM);
    mode = MODE_VELOCITY;
    panStepper.setSpeed(spd);
    tiltStepper.setSpeed(spd);
    Serial.print("[Teensy] Velocity -> ");
    Serial.print(commandedVelocityRPM, 2);
    Serial.println(" RPM");
}

void handleSetPosition(const String &cmd)
{
    String valueStr = cmd.substring(strlen("SET_POSITION:"));
    valueStr.trim();
    commandedPositionUnits = valueStr.toFloat();
    long targetSteps = lround(commandedPositionUnits * POSITION_UNITS_TO_STEPS);
    mode = MODE_POSITION;
    panStepper.moveTo(targetSteps);
    tiltStepper.moveTo(targetSteps);
    Serial.print("[Teensy] Position -> ");
    Serial.print(commandedPositionUnits, 3);
    Serial.println(" rev");
}

void handleTargetError(const String &cmd)
{
    String valueStr = cmd.substring(strlen("TARGET:"));
    valueStr.trim();
    int commaIndex = valueStr.indexOf(',');
    if (commaIndex < 0)
    {
        Serial.println("[Teensy] TARGET parse fail");
        return;
    }
    panError = valueStr.substring(0, commaIndex).toFloat();
    tiltError = valueStr.substring(commaIndex + 1).toFloat();
    mode = MODE_ERROR;
}

// Expected format: SET_GAINS:pan_kp,pan_ki,pan_kd,tilt_kp,tilt_ki,tilt_kd
void handleSetGains(const String &cmd)
{
    String valueStr = cmd.substring(strlen("SET_GAINS:"));
    valueStr.trim();

    float vals[6];
    int count = 0, startIdx = 0;

    for (int i = 0; i <= (int)valueStr.length() && count < 6; i++)
    {
        if (i == (int)valueStr.length() || valueStr[i] == ',')
        {
            String token = valueStr.substring(startIdx, i);
            token.trim();
            vals[count++] = token.toFloat();
            startIdx = i + 1;
        }
    }

    if (count != 6)
    {
        Serial.println("[Teensy] SET_GAINS parse fail — expected 6 values");
        return;
    }

    panKp = vals[0];
    panKi = vals[1];
    panKd = vals[2];
    tiltKp = vals[3];
    tiltKi = vals[4];
    tiltKd = vals[5];

    resetPidState();

    Serial.print("[Teensy] Gains updated -> pan(");
    Serial.print(panKp, 3);
    Serial.print(",");
    Serial.print(panKi, 3);
    Serial.print(",");
    Serial.print(panKd, 3);
    Serial.print(") tilt(");
    Serial.print(tiltKp, 3);
    Serial.print(",");
    Serial.print(tiltKi, 3);
    Serial.print(",");
    Serial.print(tiltKd, 3);
    Serial.println(")");
}

void handleStop()
{
    stopMotors();
    mode = MODE_IDLE;
    panError = tiltError = 0.0f;
    resetPidState();
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
    commandedVelocityRPM = commandedPositionUnits = 0.0f;
    panError = tiltError = 0.0f;
    resetPidState();
    mode = MODE_IDLE;
    Serial.println("[Teensy] ZERO");
}

void handleHeartbeat()
{
    Serial.print("[Teensy] HEARTBEAT_ACK millis=");
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
    unsigned long now = micros();
    float dt = (now - lastPidTime) / 1e6f;
    lastPidTime = now;
    if (dt <= 0.0f || dt > 0.5f)
        dt = 0.001f;

    // --- Pan PID ---
    float pe = PAN_DIRECTION_SIGN * panError;
    panIntegral += pe * dt;
    panIntegral = constrain(panIntegral, -INTEGRAL_MAX_RPM / max(panKi, 1e-6f),
                            INTEGRAL_MAX_RPM / max(panKi, 1e-6f));
    float pd = (pe - panPrevError) / dt;
    panPrevError = pe;
    panCommandedRPM = constrain(panKp * pe + panKi * panIntegral + panKd * pd, -MAX_SPEED_RPM, MAX_SPEED_RPM);

    // --- Tilt PID ---
    float te = TILT_DIRECTION_SIGN * tiltError;
    tiltIntegral += te * dt;
    tiltIntegral = constrain(tiltIntegral, -INTEGRAL_MAX_RPM / max(tiltKi, 1e-6f),
                             INTEGRAL_MAX_RPM / max(tiltKi, 1e-6f));
    float td = (te - tiltPrevError) / dt;
    tiltPrevError = te;
    tiltCommandedRPM = constrain(tiltKp * te + tiltKi * tiltIntegral + tiltKd * td, -MAX_SPEED_RPM, MAX_SPEED_RPM);

        // Suppress motion toward a limit that has already been reached
    if (!panWithinLimits(panStepsPerSec))   panStepsPerSec  = 0.0f;
    if (!tiltWithinLimits(tiltStepsPerSec)) tiltStepsPerSec = 0.0f;

    panStepper.setSpeed(rpmToStepsPerSec(panCommandedRPM));
    tiltStepper.setSpeed(rpmToStepsPerSec(tiltCommandedRPM));
    panStepper.runSpeed();
    tiltStepper.runSpeed();
}

void runIdleMode() {}

void resetPidState()
{
    panIntegral = tiltIntegral = 0.0f;
    panPrevError = tiltPrevError = 0.0f;
    panCommandedRPM = tiltCommandedRPM = 0.0f;
    lastPidTime = micros();
}

void stopMotors()
{
    panStepper.setSpeed(0.0f);
    tiltStepper.setSpeed(0.0f);
    panStepper.moveTo(panStepper.currentPosition());
    tiltStepper.moveTo(tiltStepper.currentPosition());
}

float rpmToStepsPerSec(float rpm)
{
    return (rpm * STEPS_PER_REV) / 60.0f;
}

void findZeroPos(AccelStepper &motor, int HALL_PIN)
{
    Serial.println("finding 0");
    int startState = digitalRead(HALL_PIN);
    motor.setSpeed(400.0f);
    while (digitalRead(HALL_PIN) == startState)
        motor.runSpeed();
    int newState = digitalRead(HALL_PIN);
    motor.setSpeed(80.0f);
    while (digitalRead(HALL_PIN) == newState)
        motor.runSpeed();
    motor.setSpeed(0);
    motor.setCurrentPosition(0);
    Serial.println("ZERO FOUND");
}