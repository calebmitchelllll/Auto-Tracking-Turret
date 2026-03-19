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
prev_mode = None
counter = 0

VALID_MODES = ("idle", "track", "manual")

while True:

    mode = server.get_mode()
    if mode not in VALID_MODES:
        mode = "idle"

    # reset filter only on transition away from track
    if prev_mode != mode:
        print(f"[Mode] {prev_mode} -> {mode}")
        if mode != "track":
            kf.reset()
        prev_mode = mode

    now = time.time()
    dt = now - prev_time
    prev_time = now

    if dt > 0:
        instant_fps = 1.0 / dt
        smoothed_fps = 0.9 * smoothed_fps + 0.1 * instant_fps if smoothed_fps > 0 else instant_fps
        server.set_main_loop_fps(smoothed_fps)

    small = cam.read()
    if small is None:
        continue

    h, w = small.shape[:2]
    center_x = w / 2
    center_y = h / 2
    # -----------------------------
    # idle
    # -----------------------------
    if mode == "idle":
        serial_controller.updateVelocity(0)

    # -----------------------------
    # track — run kalman, send error
    # -----------------------------
    if mode == "track":
        raw_detections = det.detect(small)

        err_x, err_y, visuals = kf.process_frame(raw_detections, center_x, center_y, deadband_x=8, deadband_y=8, prediction_time=0.25, max_jump=120)

        if serial_controller.isConnected():
            try:
                serial_controller.sendTargetError(err_x, err_y)
            except Exception as e:
                print(f"[Serial TX Error] {e}")

        smooth_cx = visuals["smooth_cx"]
        smooth_cy = visuals["smooth_cy"]
        pred_x    = visuals["pred_x"]
        pred_y    = visuals["pred_y"]
        bbox      = visuals["bbox"]

        if visuals["had_real_detection"] and bbox is not None:
            x1, y1, x2, y2 = bbox
            cv2.rectangle(small, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

        if smooth_cx is not None and smooth_cy is not None:
            cv2.circle(small, (int(smooth_cx), int(smooth_cy)), 5, (255, 255, 0), -1)

        if pred_x is not None and pred_y is not None:
            cv2.circle(small, (int(pred_x), int(pred_y)), 6, (0, 0, 255), -1)

        if smooth_cx is not None and smooth_cy is not None and pred_x is not None and pred_y is not None:
            cv2.arrowedLine(small, (int(smooth_cx), int(smooth_cy)), (int(pred_x), int(pred_y)), (0, 255, 255), 2, tipLength=0.6)
            cv2.line(small, (int(center_x), int(center_y)), (int(pred_x), int(pred_y)), (255, 0, 0), 2)

    # -----------------------------
    # manual — velocity from gains, no tracking
    # -----------------------------
    elif mode == "manual":
        gains = server.load_gains()

        if serial_controller.isConnected():
            try:
                serial_controller.updateVelocity(gains["set_velocity"])
            except Exception as e:
                print(f"[Serial Manual TX Error] {e}")

    # -----------------------------
    # always draw frame center and mode label
    # -----------------------------
    cv2.circle(small, (int(center_x), int(center_y)), 4, (255, 255, 255), -1)
    cv2.putText(small, mode.upper(), (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    cv2.imshow("camera", small)

    if cv2.pollKey() == 27:
        break

    counter += 1


serial_controller.updateVelocity(0)
cam.release()
cv2.destroyAllWindows()