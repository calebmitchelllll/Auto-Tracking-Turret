#pragma once

struct PIDValues
{
    float pan_kp;
    float pan_ki;
    float pan_kd;

    float tilt_kp;
    float tilt_ki;
    float tilt_kd;
};

PIDValues getPIDValues();
void setPIDValues(PIDValues v);