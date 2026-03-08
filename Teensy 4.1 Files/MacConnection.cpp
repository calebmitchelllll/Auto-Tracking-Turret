#include "MacConnection.h"

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