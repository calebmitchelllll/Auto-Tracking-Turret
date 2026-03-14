import numpy as np
import time


class KalmanFilter2D:
    def __init__(
        self,
        process_noise=1.0,
        measurement_noise=20.0,
        initial_uncertainty=500.0,
        max_dt=0.1,
        max_missed=10
    ):
        # state: [x, y, vx, vy]^T
        self.x = np.zeros((4, 1), dtype=np.float32)

        # covariance
        self.P = np.eye(4, dtype=np.float32) * initial_uncertainty

        # measurement model: we directly observe x and y
        self.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ], dtype=np.float32)

        # measurement noise
        self.R = np.array([
            [measurement_noise, 0],
            [0, measurement_noise]
        ], dtype=np.float32)

        self.process_noise = process_noise
        self.max_dt = max_dt
        self.max_missed = max_missed

        self.last_time = None
        self.initialized = False
        self.missed_count = 0

    def _build_F(self, dt):
        return np.array([
            [1, 0, dt, 0],
            [0, 1, 0, dt],
            [0, 0, 1,  0],
            [0, 0, 0,  1]
        ], dtype=np.float32)

    def _build_Q(self, dt):
        # constant-velocity model process noise
        dt2 = dt * dt
        dt3 = dt2 * dt
        dt4 = dt3 * dt
        q = self.process_noise

        return q * np.array([
            [dt4 / 4, 0,       dt3 / 2, 0],
            [0,       dt4 / 4, 0,       dt3 / 2],
            [dt3 / 2, 0,       dt2,     0],
            [0,       dt3 / 2, 0,       dt2]
        ], dtype=np.float32)

    def reset(self):
        self.x[:] = 0
        self.P[:] = np.eye(4, dtype=np.float32) * 500.0
        self.last_time = None
        self.initialized = False
        self.missed_count = 0

    def initialize(self, meas_x, meas_y):
        self.x = np.array([
            [meas_x],
            [meas_y],
            [0],
            [0]
        ], dtype=np.float32)

        self.P = np.eye(4, dtype=np.float32) * 500.0
        self.last_time = time.time()
        self.initialized = True
        self.missed_count = 0

    def predict(self):
        if not self.initialized:
            return None

        now = time.time()
        if self.last_time is None:
            dt = 1 / 60.0
        else:
            dt = now - self.last_time

        dt = max(1e-3, min(dt, self.max_dt))
        self.last_time = now

        F = self._build_F(dt)
        Q = self._build_Q(dt)

        self.x = F @ self.x
        self.P = F @ self.P @ F.T + Q

        return float(self.x[0, 0]), float(self.x[1, 0])

    def update(self, meas_x, meas_y):
        if not self.initialized:
            self.initialize(meas_x, meas_y)
            return float(meas_x), float(meas_y)

        z = np.array([
            [meas_x],
            [meas_y]
        ], dtype=np.float32)

        y = z - (self.H @ self.x)
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)

        self.x = self.x + (K @ y)

        I = np.eye(4, dtype=np.float32)
        self.P = (I - K @ self.H) @ self.P

        self.missed_count = 0
        return float(self.x[0, 0]), float(self.x[1, 0])

    def mark_missed(self):
        if not self.initialized:
            return None

        self.missed_count += 1
        if self.missed_count > self.max_missed:
            self.reset()
            return None

        return float(self.x[0, 0]), float(self.x[1, 0])

    def get_state(self):
        if not self.initialized:
            return None

        return {
            "x": float(self.x[0, 0]),
            "y": float(self.x[1, 0]),
            "vx": float(self.x[2, 0]),
            "vy": float(self.x[3, 0]),
        }
    def predict_ahead(self, dt_ahead):
        if not self.initialized:
            return None

        F = np.array([
            [1, 0, dt_ahead, 0],
            [0, 1, 0, dt_ahead],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ], dtype=np.float32)
        future_x = F @ self.x
        return float(future_x[0, 0]), float(future_x[1, 0])

    def is_measurement_reasonable(self, meas_x, meas_y, max_jump=120):
        if not self.initialized:
            return True

        pred_x = float(self.x[0, 0])
        pred_y = float(self.x[1, 0])

        dx = meas_x - pred_x
        dy = meas_y - pred_y

        return (dx * dx + dy * dy) <= (max_jump * max_jump)
    
    def choose_best_detection(self, detections):
        """
        Choose the detection that best matches the current Kalman track.
        If Kalman is not initialized yet, return the first detection.
        """
        if len(detections) == 0:
            return None

        if not self.initialized:
            return detections[0]

        state = self.get_state()
        pred_x = state["x"]
        pred_y = state["y"]

        best_det = None
        best_dist2 = float("inf")

        for det in detections:
            cx, cy, x1, y1, x2, y2 = det
            dx = cx - pred_x
            dy = cy - pred_y
            dist2 = dx * dx + dy * dy
            if dist2 < best_dist2:
                best_dist2 = dist2
                best_det = det

        return best_det