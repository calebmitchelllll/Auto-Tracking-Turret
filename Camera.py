import cv2
import os

class Camera:
    def __init__(self, index=0, width=640, height=360):
        index, arducam_found = self._find_high_fps_camera(index)

        self.cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.cap.set(cv2.CAP_PROP_FPS, 120)

        if not self.cap.isOpened():
            raise RuntimeError("[Camera] Could not open camera")

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        if arducam_found:
            print("[Camera] Arducam initialized")
        else:
            print("[Camera] Initialization failed. Fallback to Mac camera")

    def _find_high_fps_camera(self, fallback):
        for i in range(5):
            cap = self._silent_open(i)

            if cap is not None and cap.isOpened():
                cap.set(cv2.CAP_PROP_FPS, 120)
                fps = cap.get(cv2.CAP_PROP_FPS)
                cap.release()

                if fps >= 60:
                    return i, True

        return fallback, False

    def _silent_open(self, index):
        devnull_fd = os.open(os.devnull, os.O_WRONLY)
        saved_stderr_fd = os.dup(2)

        try:
            os.dup2(devnull_fd, 2)
            cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
        finally:
            os.dup2(saved_stderr_fd, 2)
            os.close(saved_stderr_fd)
            os.close(devnull_fd)

        return cap

    def read(self):
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def release(self):
        self.cap.release()