#include "PIDValues.h"

static PIDValues currentPID =
    {
        0.25, 0.1, 0.0,
        0.25, 0.1, 0.0};

PIDValues getPIDValues()
{
    return currentPID;
}

void setPIDValues(PIDValues v)
{
    currentPID = v;
}