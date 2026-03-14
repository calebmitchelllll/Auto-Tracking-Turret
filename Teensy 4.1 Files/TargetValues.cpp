#include "TargetValues.h"

static TargetValues currentTarget = {0.0f, 0.0f};

TargetValues getTargetValues()
{
    return currentTarget;
}

void setTargetValues(TargetValues v)
{
    currentTarget = v;
}