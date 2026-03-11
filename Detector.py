import torch
from ultralytics import YOLO


class Detector:
    def __init__(self, model_path="YOLO/nano.pt", conf=0.60, min_area=500):
        self.model = YOLO(model_path)
        self.conf = conf
        self.min_area = min_area

        if torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"

        print("[Detector] Initialized using:", self.device)

    def detect(self, frame):
        best_detection = None
        best_area = 0

        with torch.no_grad():
            results = self.model(
                frame,
                conf=self.conf,
                device=self.device,
                verbose=False
            )

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                area = (x2 - x1) * (y2 - y1)
                if area < self.min_area:
                    continue

                if area > best_area:
                    best_area = area
                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2
                    best_detection = (cx, cy, x1, y1, x2, y2)

        if best_detection is None:
            return []

        return [best_detection]