import math
import time


def get_error_from_point(point_x, point_y, center_x, center_y):
    err_x = point_x - center_x
    err_y = point_y - center_y
    return err_x, err_y


def get_bbx_center(detection):
    cx, cy, x1, y1, x2, y2 = detection
    return cx, cy


def detection_area(detection):
    cx, cy, x1, y1, x2, y2 = detection
    return (x2 - x1) * (y2 - y1)


def is_jump_valid(err_x, err_y, last_err_x, last_err_y, max_jump=50):
    jump = math.sqrt((err_x - last_err_x) ** 2 + (err_y - last_err_y) ** 2)
    return jump <= max_jump


def smooth_value(value, filtered_value, alpha=0.2):
    return alpha * value + (1 - alpha) * filtered_value


def smooth_error(err_x, err_y, filtered_err_x, filtered_err_y, alpha=0.2):
    filtered_err_x = smooth_value(err_x, filtered_err_x, alpha)
    filtered_err_y = smooth_value(err_y, filtered_err_y, alpha)
    return filtered_err_x, filtered_err_y


class DetectionTracker:
    def __init__(
        self,
        smoothing_alpha=0.2,
        velocity_alpha=0.25,
        prediction_time=0.25,
        max_jump=120,
        reject_limit=10
    ):
        self.alpha = smoothing_alpha
        self.vel_alpha = velocity_alpha
        self.prediction_time = prediction_time
        self.max_jump = max_jump
        self.reject_limit = reject_limit

        self.last_err_x = 0
        self.last_err_y = 0

        self.filtered_err_x = 0
        self.filtered_err_y = 0

        self.last_filtered_err_x = 0
        self.last_filtered_err_y = 0

        self.vel_x = 0
        self.vel_y = 0

        self.has_target = False
        self.reject_count = 0
        self.last_detection_time = time.time()

    def reset(self):
        self.last_err_x = 0
        self.last_err_y = 0

        self.filtered_err_x = 0
        self.filtered_err_y = 0

        self.last_filtered_err_x = 0
        self.last_filtered_err_y = 0

        self.vel_x = 0
        self.vel_y = 0

        self.has_target = False
        self.reject_count = 0
        self.last_detection_time = time.time()

    def update(self, detections, frame_w, frame_h):
        center_x = frame_w / 2
        center_y = frame_h / 2

        result = {
            "detected": False,
            "raw_cx": None,
            "raw_cy": None,
            "x1": None,
            "y1": None,
            "x2": None,
            "y2": None,
            "filtered_x": None,
            "filtered_y": None,
            "pred_x": None,
            "pred_y": None,
            "err_x": 0,
            "err_y": 0,
            "vel_x": self.vel_x,
            "vel_y": self.vel_y,
            "center_x": center_x,
            "center_y": center_y,
        }

        if len(detections) == 0:
            self.has_target = False
            self.reject_count = 0
            self.vel_x = 0
            self.vel_y = 0
            return result

        detection = detections[0]
        cx, cy, x1, y1, x2, y2 = detection

        raw_err_x, raw_err_y = get_error_from_point(cx, cy, center_x, center_y)

        jump_valid = is_jump_valid(
            raw_err_x,
            raw_err_y,
            self.last_err_x,
            self.last_err_y,
            max_jump=self.max_jump
        )

        if (not self.has_target) or jump_valid or self.reject_count >= self.reject_limit:
            now_det = time.time()
            dt_det = now_det - self.last_detection_time
            if dt_det <= 0:
                dt_det = 1e-6

            self.filtered_err_x, self.filtered_err_y = smooth_error(
                raw_err_x,
                raw_err_y,
                self.filtered_err_x,
                self.filtered_err_y,
                alpha=self.alpha
            )

            new_vel_x = (self.filtered_err_x - self.last_filtered_err_x) / dt_det
            new_vel_y = (self.filtered_err_y - self.last_filtered_err_y) / dt_det

            self.vel_x = (1 - self.vel_alpha) * self.vel_x + self.vel_alpha * new_vel_x
            self.vel_y = (1 - self.vel_alpha) * self.vel_y + self.vel_alpha * new_vel_y

            self.last_filtered_err_x = self.filtered_err_x
            self.last_filtered_err_y = self.filtered_err_y
            self.last_detection_time = now_det

            self.last_err_x = raw_err_x
            self.last_err_y = raw_err_y

            filtered_x = center_x + self.filtered_err_x
            filtered_y = center_y + self.filtered_err_y

            # prediction drawn from RAW YOLO center
            pred_x = cx + self.vel_x * self.prediction_time
            pred_y = cy + self.vel_y * self.prediction_time

            pred_x = max(0, min(frame_w - 1, pred_x))
            pred_y = max(0, min(frame_h - 1, pred_y))

            pred_err_x, pred_err_y = get_error_from_point(pred_x, pred_y, center_x, center_y)

            self.has_target = True
            self.reject_count = 0

            result.update({
                "detected": True,
                "raw_cx": cx,
                "raw_cy": cy,
                "x1": x1,
                "y1": y1,
                "x2": x2,
                "y2": y2,
                "filtered_x": filtered_x,
                "filtered_y": filtered_y,
                "pred_x": pred_x,
                "pred_y": pred_y,
                "err_x": pred_err_x,
                "err_y": pred_err_y,
                "vel_x": self.vel_x,
                "vel_y": self.vel_y,
            })

            return result

        self.reject_count += 1
        return result