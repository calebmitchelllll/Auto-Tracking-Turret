import cv2
import os

class Camera:
    def __init__(self, index=0, width=1280, height=800, target_fps=120,
                 infer_width=640, infer_height=400):

        index, arducam_found = self._find_high_fps_camera(index)

        self.cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)

        if not self.cap.isOpened():
            raise RuntimeError("[Camera] Could not open camera")

        # Request camera settings
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, target_fps)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        # Actual camera mode
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)

        # Inference resize resolution
        self.infer_width = infer_width
        self.infer_height = infer_height

        if arducam_found:
            print(f"[Camera] Arducam initialized: {self.width}x{self.height} @ {self.fps:.2f} FPS")
        else:
            print("[Camera] Arducam not found, fallback camera used")

        print(f"[Camera] Inference resolution: {self.infer_width}x{self.infer_height}")

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
            return None, None

        # Resize for inference
        small = cv2.resize(
            frame,
            (self.infer_width, self.infer_height),
            interpolation=cv2.INTER_LINEAR
        )

        return frame, small

    def release(self):
        self.cap.release()