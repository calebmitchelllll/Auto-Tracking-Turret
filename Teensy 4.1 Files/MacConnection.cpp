#include "MacConnection.h"
#include "PIDValues.h"
#include "TargetValues.h"

MacConnection::MacConnection(unsigned long baud)
{
    baudRate = baud;
    connected = false;
}

void MacConnection::begin()
{
    Serial.begin(baudRate);

    while (!Serial && millis() < 4000)
    {
        // wait a little for Mac serial monitor / python app
    }

    connected = Serial ? true : false;

    if (connected)
    {
        Serial.println("[Teensy] USB serial started");
    }
}

void MacConnection::update()
{
    connected = Serial ? true : false;
}

bool MacConnection::isConnected()
{
    return connected;
}

bool MacConnection::checkConnection()
{
    update();
    if (connected)
    {
        Serial.println("[Teensy] Mac connected");
        return true;
    }
    else
    {
        return false;
    }
}

void MacConnection::send(const String &msg)
{
    if (Serial)
    {
        Serial.print(msg);
    }
}

void MacConnection::sendLine(const String &msg)
{
    if (Serial)
    {
        Serial.println(msg);
    }
}

void MacConnection::sendFloat(const String &label, float value)
{
    if (Serial)
    {
        Serial.print(label);
        Serial.print(": ");
        Serial.println(value, 4);
    }
}

void MacConnection::sendInt(const String &label, int value)
{
    if (Serial)
    {
        Serial.print(label);
        Serial.print(": ");
        Serial.println(value);
    }
}
#include "PIDValues.h"

void MacConnection::readStream()
{
    if (!available())
        return;

    String msg = readLine();

    if (msg.length() == 0)
        return;

    // ---------------- PID update ----------------
    if (msg.startsWith("UpdatePID:"))
    {
        msg.remove(0, 10); // remove "UpdatePID:"

        PIDValues v;

        int i1 = msg.indexOf(',');
        int i2 = msg.indexOf(',', i1 + 1);
        int i3 = msg.indexOf(',', i2 + 1);
        int i4 = msg.indexOf(',', i3 + 1);
        int i5 = msg.indexOf(',', i4 + 1);

        if (i1 < 0 || i2 < 0 || i3 < 0 || i4 < 0 || i5 < 0)
        {
            sendLine("[Teensy] PID parse error");
            return;
        }

        v.pan_kp = msg.substring(0, i1).toFloat();
        v.pan_ki = msg.substring(i1 + 1, i2).toFloat();
        v.pan_kd = msg.substring(i2 + 1, i3).toFloat();
        v.tilt_kp = msg.substring(i3 + 1, i4).toFloat();
        v.tilt_ki = msg.substring(i4 + 1, i5).toFloat();
        v.tilt_kd = msg.substring(i5 + 1).toFloat();

        setPIDValues(v);
        sendLine("[Teensy] PID updated");
        return;
    }

    // ---------------- target update ----------------
    if (msg.startsWith("Target:") || msg.startsWith("target:"))
    {
        if (msg.startsWith("Target:"))
            msg.remove(0, 7); // remove "Target:"
        else
            msg.remove(0, 7); // remove "target:"

        int commaIndex = msg.indexOf(',');

        if (commaIndex < 0)
        {
            sendLine("[Teensy] Target parse error");
            return;
        }

        TargetValues t;
        t.pan_target = msg.substring(0, commaIndex).toFloat();
        t.tilt_target = msg.substring(commaIndex + 1).toFloat();

        setTargetValues(t);
        sendLine("[Teensy] Target updated");
        return;
    }
}

bool MacConnection::available()
{
    return Serial.available() > 0;
}

String MacConnection::readLine()
{
    String msg = "";

    while (Serial.available() > 0)
    {
        char c = Serial.read();

        if (c == '\n')
        {
            break;
        }

        if (c != '\r')
        {
            msg += c;
        }
    }

    return msg;
}