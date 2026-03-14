#ifndef MAC_CONNECTION_H
#define MAC_CONNECTION_H

#include <Arduino.h>

class MacConnection
{
private:
    unsigned long baudRate;
    bool connected;

public:
    MacConnection(unsigned long baud = 115200);

    void begin();
    void update();

    bool isConnected();
    bool checkConnection();

    void send(const String &msg);
    void sendLine(const String &msg);
    void sendFloat(const String &label, float value);
    void sendInt(const String &label, int value);

    void readStream();

    bool available();
    String readLine();
};

#endif