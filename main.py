import cv2
import threading
import time

from Utils import print_fps

from Camera import Camera
from Detector import Detector
from Webserver import Webserver
from KalmanFilter2D import KalmanFilter2D


# initializations
server = Webserver(json_file="saved_data/gains.json", host="127.0.0.1", port=5000)
threading.Thread(target=server.run, daemon=True).start()

cam = Camera()
det = Detector("YOLO/nano.pt")

kf = KalmanFilter2D(
    process_noise=300.0,
    measurement_noise=8.0,
    initial_uncertainty=500.0,
    max_dt=0.1,
    max_missed=10
)

prev_time = time.time()

deadband_x = 8
deadband_y = 8

prediction_time = 0.25
max_jump = 120

while True:
    small = cam.read()
    if small is None:
        continue

    raw_detections = det.detect(small)
    gains = server.load_gains()

    pan_kp = gains["pan_kp"]
    tilt_kp = gains["tilt_kp"]

    h, w = small.shape[:2]
    center_x = w / 2
    center_y = h / 2

    smooth_cx = None
    smooth_cy = None
    pred_x = None
    pred_y = None
    x1 = y1 = x2 = y2 = None
    had_real_detection = False

    # predict once per frame if filter is alive
    if kf.initialized:
        kf.predict()

    # choose the best matching detection
    best_detection = kf.choose_best_detection(raw_detections)

    if best_detection is not None:
        raw_cx, raw_cy, x1, y1, x2, y2 = best_detection

        if kf.is_measurement_reasonable(raw_cx, raw_cy, max_jump=max_jump):
            smooth_cx, smooth_cy = kf.update(raw_cx, raw_cy)
            had_real_detection = True
        else:
            # reject wild jump
            kf.mark_missed()
    else:
        kf.mark_missed()

    # use filter state if still active
    if kf.initialized:
        state = kf.get_state()
        smooth_cx = state["x"]
        smooth_cy = state["y"]

        future = kf.predict_ahead(prediction_time)
        if future is not None:
            pred_x, pred_y = future

        err_x = pred_x - center_x
        err_y = pred_y - center_y

        if abs(err_x) < deadband_x:
            err_x = 0

        if abs(err_y) < deadband_y:
            err_y = 0

        teensy_err_x = err_x
        teensy_err_y = err_y
    else:
        teensy_err_x = 0
        teensy_err_y = 0

    # draw selected bbox only if a real detection was used this frame
    if had_real_detection and x1 is not None:
        cv2.rectangle(small, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

    # draw frame center
    cv2.circle(small, (int(center_x), int(center_y)), 4, (255, 255, 255), -1)

    # draw smoothed current point
    if smooth_cx is not None and smooth_cy is not None:
        cv2.circle(small, (int(smooth_cx), int(smooth_cy)), 5, (255, 255, 0), -1)

    # draw predicted future point
    if pred_x is not None and pred_y is not None:
        cv2.circle(small, (int(pred_x), int(pred_y)), 6, (0, 0, 255), -1)

    # draw arrow from smoothed point to predicted point
    if smooth_cx is not None and smooth_cy is not None and pred_x is not None and pred_y is not None:
        cv2.arrowedLine(
            small,
            (int(smooth_cx), int(smooth_cy)),
            (int(pred_x), int(pred_y)),
            (0, 255, 255),
            2,
            tipLength=0.6
        )

    # draw center to predicted point
    if pred_x is not None and pred_y is not None:
        cv2.line(
            small,
            (int(center_x), int(center_y)),
            (int(pred_x), int(pred_y)),
            (255, 0, 0),
            2
        )

    prev_time = print_fps(prev_time)

    if kf.initialized:
        print("\033[2K\r" + f"[TEENSY ERROR] ({teensy_err_x:6.1f}, {teensy_err_y:6.1f})")
    else:
        print("\033[2K\r[TEENSY ERROR] none")

    print("\033[F\033[F", end="")

    cv2.imshow("camera", small)

    if cv2.pollKey() == 27:
        break

cam.release()
cv2.destroyAllWindows()