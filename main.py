import cv2
import threading
import time
from DetectionUtils import *

from Camera import Camera
from Detector import Detector
from Webserver import Webserver

#initializations
server = Webserver(json_file="saved_data/gains.json", host="127.0.0.1", port=5000)
threading.Thread(target=server.run, daemon=True).start()

cam = Camera()
det = Detector("YOLO/nano.pt")

prev_time = time.time()

last_err_x = 0
last_err_y = 0
filtered_err_x = 0
filtered_err_y = 0
has_target = False

reject_count = 0
reject_limit = 10

#main loop
while True:
    frame, small = cam.read()
    if small is None:
        continue

    detections = det.detect(small)
    gains = server.load_gains()

    pan_kp = gains["pan_kp"]
    tilt_kp = gains["tilt_kp"]

    h, w = small.shape[:2]
    center_x = w / 2
    center_y = h / 2

    cv2.circle(small, (int(center_x), int(center_y)), 5, (255, 255, 255), -1)

    detected = False

    for cx, cy, x1, y1, x2, y2 in detections:

        raw_err_x, raw_err_y = get_error((cx, cy, x1, y1, x2, y2), center_x, center_y)

        jump_valid = is_jump_valid(raw_err_x, raw_err_y, last_err_x, last_err_y, max_jump=120)

        if (not has_target) or jump_valid or reject_count >= reject_limit:

            filtered_err_x, filtered_err_y = smooth_error(
                raw_err_x,
                raw_err_y,
                filtered_err_x,
                filtered_err_y,
                alpha=0.2
            )

            last_err_x = raw_err_x
            last_err_y = raw_err_y

            err_x = filtered_err_x
            err_y = filtered_err_y

            detected = True
            has_target = True
            reject_count = 0

            cv2.rectangle(
                small,
                (int(x1), int(y1)),
                (int(x2), int(y2)),
                (0, 255, 0),
                2
            )

            cv2.circle(small, (int(cx), int(cy)), 5, (0, 0, 255), -1)

            cv2.line(
                small,
                (int(center_x), int(center_y)),
                (int(cx), int(cy)),
                (255, 0, 0),
                2
            )

        else:
            reject_count += 1
            detected = False

    if len(detections) == 0:
        has_target = False
        reject_count = 0

    # Print FPS
    now = time.time()
    fps = 1.0 / (now - prev_time)
    prev_time = now

    print("\033[2K\r" + f"[FPS] {fps:6.1f}")

    if detected:
        print("\033[2K\r" + f"[ERROR] ({err_x:6.1f}, {err_y:6.1f})")
    else:
        print("\033[2K\r[ERROR] none")

    print("\033[F\033[F", end="")

    cv2.imshow("camera", small)

    if cv2.waitKey(1) == 27:
        break

cam.release()
cv2.destroyAllWindows()