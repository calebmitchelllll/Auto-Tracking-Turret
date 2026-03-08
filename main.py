import cv2
import threading
from Camera import Camera
from Detector import Detector
from Webserver import Webserver

#initializations
server = Webserver(json_file="saved_data/gains.json", host="127.0.0.1", port=5000)
threading.Thread(target=server.run, daemon=True).start()

cam = Camera()
det = Detector("YOLO/nano.pt")


#main loop
while True:
    frame = cam.read()
    if frame is None:
        continue

    detections = det.detect(frame)
    gains = server.load_gains()

    pan_kp = gains["pan_kp"]
    tilt_kp = gains["tilt_kp"]

    h, w = frame.shape[:2]
    center_x = w / 2
    center_y = h / 2

    cv2.circle(frame, (int(center_x), int(center_y)), 5, (255, 255, 255), -1)

    for cx, cy, x1, y1, x2, y2 in detections:
        err_x = cx - center_x
        err_y = cy - center_y


        #TODO: send pan_error and tilt_error to pan/tilt controller instead of printing to console

        print(
            f"error: ({err_x:.1f}, {err_y:.1f})"
        )

        cv2.rectangle(
            frame,
            (int(x1), int(y1)),
            (int(x2), int(y2)),
            (0, 255, 0),
            2
        )

        cv2.circle(frame, (int(cx), int(cy)), 5, (0, 0, 255), -1)
        cv2.line(
            frame,
            (int(center_x), int(center_y)),
            (int(cx), int(cy)),
            (255, 0, 0),
            2
        )

    cv2.putText(
        frame,
        f"pan_kp: {pan_kp:.2f}  tilt_kp: {tilt_kp:.2f}",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (255, 255, 255),
        2
    )

    cv2.imshow("camera", frame)

    if cv2.waitKey(1) == 27:
        break

cam.release()
cv2.destroyAllWindows()