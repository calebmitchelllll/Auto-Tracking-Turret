import cv2
import threading
import time

from Camera import Camera
from Detector import Detector
from Webserver import Webserver
from KalmanFilter2D import KalmanFilter2D
from SerialController import SerialController


# -----------------------------
# serial controller init
# -----------------------------
serial_controller = SerialController(port="/dev/cu.usbmodem183380201", baudrate=115200)
serial_controller.connect()
serial_controller.start_reader()

# -----------------------------
# webserver init
# -----------------------------
server = Webserver(json_file="saved_data/gains.json", host="127.0.0.1", port=5000, serial=serial_controller)
threading.Thread(target=server.run, daemon=True).start()

# -----------------------------
# camera / detector / filter
# -----------------------------
cam = Camera()
det = Detector("YOLO/nano.pt")

kf = KalmanFilter2D(process_noise=300.0, measurement_noise=8.0, initial_uncertainty=500.0, max_dt=0.1, max_missed=10)

prev_time = time.time()
smoothed_fps = 0.0

deadband_x = 8
deadband_y = 8

prediction_time = 0.25
max_jump = 120

counter = 0

while True:

    now = time.time()
    dt = now - prev_time
    prev_time = now

    if dt > 0:
        instant_fps = 1.0 / dt
        smoothed_fps = 0.9 * smoothed_fps + 0.1 * instant_fps if smoothed_fps > 0 else instant_fps
        server.set_main_loop_fps(smoothed_fps)

    serial_controller.sendHeartbeat(counter) #send heartbeat every 10 frames

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

        if pred_x is not None and pred_y is not None:
            err_x = pred_x - center_x
            err_y = pred_y - center_y
        else:
            err_x = 0
            err_y = 0

        if abs(err_x) < deadband_x:
            err_x = 0

        if abs(err_y) < deadband_y:
            err_y = 0

        teensy_err_x = err_x
        teensy_err_y = err_y
    else:
        teensy_err_x = 0
        teensy_err_y = 0

    # -----------------------------
    # send target error to teensy
    # -----------------------------
    if serial_controller.isConnected():
        try:
            serial_controller.sendTargetError(teensy_err_x, teensy_err_y)
        except Exception as e:
            print(f"[Serial TX Error] {e}")

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

    cv2.imshow("camera", small)

    if cv2.pollKey() == 27:
        break

    counter += 1


serial_controller.updateVelocity(0)
cam.release()
cv2.destroyAllWindows()