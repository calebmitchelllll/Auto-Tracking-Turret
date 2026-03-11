import math


def get_error(detection, center_x, center_y):
    cx, cy, x1, y1, x2, y2 = detection
    err_x = cx - center_x
    err_y = cy - center_y
    return err_x, err_y


def detection_area(detection):
    cx, cy, x1, y1, x2, y2 = detection
    return (x2 - x1) * (y2 - y1)


def is_jump_valid(err_x, err_y, last_err_x, last_err_y, max_jump=50):
    jump = math.sqrt((err_x - last_err_x) ** 2 + (err_y - last_err_y) ** 2)
    return jump <= max_jump


def smooth_error(err_x, err_y, filtered_err_x, filtered_err_y, alpha=0.2):
    filtered_err_x = alpha * err_x + (1 - alpha) * filtered_err_x
    filtered_err_y = alpha * err_y + (1 - alpha) * filtered_err_y
    return filtered_err_x, filtered_err_y