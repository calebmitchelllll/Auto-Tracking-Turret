#pragma once

struct TargetValues
{
    float pan_target;
    float tilt_target;
};

TargetValues getTargetValues();
void setTargetValues(TargetValues v);