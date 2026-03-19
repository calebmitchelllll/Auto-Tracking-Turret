import cv2
import torch
from ultralytics import YOLO


class Detector:
    def __init__(self, model_path="YOLO/nano.pt", conf=0.60, min_area=500):
        self.model = YOLO(model_path)
        self.conf = conf
        self.min_area = min_area
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"

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
    
    def handleVisuals(self, visuals, frame):
        h, w = frame.shape[:2]
        center_x = w // 2
        center_y = h // 2

        smooth_cx = visuals["smooth_cx"]
        ...
        smooth_cx = visuals["smooth_cx"]
        smooth_cy = visuals["smooth_cy"]
        pred_x    = visuals["pred_x"]
        pred_y    = visuals["pred_y"]
        bbox      = visuals["bbox"]

        if visuals["had_real_detection"] and bbox is not None:
            x1, y1, x2, y2 = bbox
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)

        if smooth_cx is not None and smooth_cy is not None:
            cv2.circle(frame, (int(smooth_cx), int(smooth_cy)), 5, (255, 255, 0), -1)

        if pred_x is not None and pred_y is not None:
            cv2.circle(frame, (int(pred_x), int(pred_y)), 6, (0, 0, 255), -1)

        if smooth_cx is not None and smooth_cy is not None and pred_x is not None and pred_y is not None:
            cv2.arrowedLine(frame, (int(smooth_cx), int(smooth_cy)), (int(pred_x), int(pred_y)), (0, 255, 255), 2, tipLength=0.6)
            cv2.line(frame, (int(center_x), int(center_y)), (int(pred_x), int(pred_y)), (255, 0, 0), 2)