import cv2
import threading
import time
from Utils import print_fps

from DetectionUtils import DetectionTracker
from Camera import Camera
from Detector import Detector
from Webserver import Webserver

# initializations
server = Webserver(json_file="saved_data/gains.json", host="127.0.0.1", port=5000)
threading.Thread(target=server.run, daemon=True).start()

cam = Camera()
det = Detector("YOLO/nano.pt")
tracker = DetectionTracker(smoothing_alpha=0.2, velocity_alpha=0.25, prediction_time=0.25, max_jump=120, reject_limit=10)

prev_time = time.time()

while True:
    small = cam.read()
    if small is None:
        continue

    detections = det.detect(small)
    gains = server.load_gains()

    pan_kp = gains["pan_kp"]
    tilt_kp = gains["tilt_kp"]

    h, w = small.shape[:2]
    track = tracker.update(detections, w, h)

    detected = track["detected"]

    if detected:
        raw_cx = track["raw_cx"]
        raw_cy = track["raw_cy"]
        x1 = track["x1"]
        y1 = track["y1"]
        x2 = track["x2"]
        y2 = track["y2"]
        pred_x = track["pred_x"]
        pred_y = track["pred_y"]

        err_x = track["err_x"]
        err_y = track["err_y"]

        #TODO: sent these values to teensy
        teensy_err_x = err_x
        teensy_err_y = err_y

        cv2.rectangle(small, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

        cv2.arrowedLine(small, (int(raw_cx), int(raw_cy)), (int(pred_x), int(pred_y)), (0, 255, 255), 2, tipLength=0.6)

        cv2.line(small, (w // 2, h // 2), (int(pred_x), int(pred_y)), (255, 0, 0), 2)

    prev_time = print_fps(prev_time)

    if detected:
        print("\033[2K\r" + f"[TEENSY ERROR] ({teensy_err_x:6.1f}, {teensy_err_y:6.1f})")
    else:
        print("\033[2K\r[TEENSY ERROR] none")

    print("\033[F\033[F", end="")

    cv2.imshow("camera", small)

    if cv2.pollKey() == 27:
        break

cam.release()
cv2.destroyAllWindows()
