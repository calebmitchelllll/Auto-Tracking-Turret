#include <AccelStepper.h>

#define PAN_STEP 2
#define PAN_DIR 3

#define TILT_STEP 4
#define TILT_DIR 5

#define HALL_PIN 9

AccelStepper panStepper(AccelStepper::DRIVER, PAN_STEP, PAN_DIR);
AccelStepper tiltStepper(AccelStepper::DRIVER, TILT_STEP, TILT_DIR);

// -----------------------------
// motor / driver settings
// -----------------------------
const float MOTOR_FULL_STEPS_PER_REV = 200.0f;
const float MICROSTEPS = 16.0f; // change to match your driver
const float STEPS_PER_REV = MOTOR_FULL_STEPS_PER_REV * MICROSTEPS;

// limits now written in RPM
const float MAX_SPEED_RPM = 300.0f;
const float ACCEL_RPM_PER_SEC = 400.0f;

// converted limits for AccelStepper
const float MAX_SPEED_STEPS_PER_SEC = (MAX_SPEED_RPM * STEPS_PER_REV) / 60.0f;
const float ACCEL_STEPS_PER_SEC2 = (ACCEL_RPM_PER_SEC * STEPS_PER_REV) / 60.0f;

// position command units
// if you want SET_POSITION to mean revolutions, keep this 1 rev = STEPS_PER_REV
// if you want degrees later, we can change it
const float POSITION_UNITS_TO_STEPS = STEPS_PER_REV;

String inputBuffer = "";

enum ControlMode
{
    MODE_IDLE,
    MODE_VELOCITY,
    MODE_POSITION
};

ControlMode mode = MODE_IDLE;

float commandedVelocityRPM = 0.0f;
float commandedPositionUnits = 0.0f;

unsigned long lastStatusPrint = 0;
const unsigned long STATUS_INTERVAL_MS = 200;

void setup()
{
    pinMode(HALL_PIN, INPUT_PULLUP);

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

    panStepper.setCurrentPosition(0);
    tiltStepper.setCurrentPosition(0);

    Serial.println("[Teensy] Ready");
    Serial.println("[Teensy] Velocity units = RPM");
    Serial.println("[Teensy] Position units = revolutions");
    Serial.print("[Teensy] STEPS_PER_REV = ");
    Serial.println(STEPS_PER_REV, 1);
    Serial.println("[Teensy] Commands:");
    Serial.println("  SET_VELOCITY:x");
    Serial.println("  SET_POSITION:x");
    Serial.println("  STOP");
    Serial.println("  ZERO");
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

void handleStop()
{
    stopMotors();
    mode = MODE_IDLE;

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

void printStatusPeriodically()
{
    unsigned long now = millis();
    if (now - lastStatusPrint < STATUS_INTERVAL_MS)
    {
        return;
    }

    lastStatusPrint = now;

    Serial.print("[Status] mode=");
    switch (mode)
    {
    case MODE_VELOCITY:
        Serial.print("VEL");
        break;
    case MODE_POSITION:
        Serial.print("POS");
        break;
    default:
        Serial.print("IDLE");
        break;
    }

    Serial.print(" panPos=");
    Serial.print(panStepper.currentPosition());

    Serial.print(" tiltPos=");
    Serial.print(tiltStepper.currentPosition());

    Serial.print(" panSpeedSteps=");
    Serial.print(panStepper.speed(), 1);

    Serial.print(" velRPM=");
    Serial.print(commandedVelocityRPM, 2);

    if (mode == MODE_POSITION)
    {
        Serial.print(" panTarget=");
        Serial.print(panStepper.targetPosition());
    }

    Serial.print(" hall=");
    Serial.println(digitalRead(HALL_PIN));
} 