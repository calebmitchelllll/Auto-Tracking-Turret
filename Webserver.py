from flask import Flask, request, jsonify, render_template_string
import json
import os
import threading


class Webserver:
    def __init__(self, json_file="./saved_data/gains.json", host="127.0.0.1", port=5000, serial=None):
        self.json_file = json_file
        self.host = host
        self.port = port
        self.serial = serial
        self.app = Flask(__name__)

        self.default_gains = {
            "mode": "idle",
            "pan_kp": 1.0,
            "pan_ki": 1.0,
            "pan_kd": 1.0,
            "tilt_kp": 1.0,
            "tilt_ki": 1.0,
            "tilt_kd": 1.0,
            "set_velocity": 0.0,
            "set_position": 0.0
        }

        # live status data
        self.main_loop_fps = 0.0
        self._status_lock = threading.Lock()

        self._setup_routes()

    def load_gains(self):
        if not os.path.exists(self.json_file):
            self.save_gains(self.default_gains)
            return self.default_gains.copy()

        try:
            with open(self.json_file, "r") as f:
                data = json.load(f)

            for key, value in self.default_gains.items():
                if key not in data:
                    data[key] = value

            return data
        except Exception:
            self.save_gains(self.default_gains)
            return self.default_gains.copy()

    def save_gains(self, data):
        dirpath = os.path.dirname(self.json_file)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

        with open(self.json_file, "w") as f:
            json.dump(data, f, indent=2)

    def set_main_loop_fps(self, fps):
        with self._status_lock:
            self.main_loop_fps = float(fps)

    def get_main_loop_fps(self):
        with self._status_lock:
            return self.main_loop_fps

    def get_mode(self):
        return self.load_gains().get("mode", self.default_gains["mode"])

    def _setup_routes(self):
        HTML = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Pan / Tilt PID Gains</title>
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 1100px;
                    margin: 40px auto;
                    padding: 20px;
                    background: #111;
                    color: white;
                }

                .top-bar {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 20px;
                    flex-wrap: wrap;
                    margin-bottom: 20px;
                }

                .fps-box {
                    background: #1c1c1c;
                    padding: 14px 18px;
                    border-radius: 12px;
                    min-width: 220px;
                }

                .fps-label {
                    color: #aaa;
                    font-size: 14px;
                    margin-bottom: 4px;
                }

                .fps-value {
                    font-size: 28px;
                    font-weight: bold;
                    color: #7CFC00;
                }

                .mode-box {
                    background: #1c1c1c;
                    padding: 14px 18px;
                    border-radius: 12px;
                }

                .mode-label {
                    color: #aaa;
                    font-size: 14px;
                    margin-bottom: 8px;
                }

                .mode-buttons {
                    display: flex;
                    gap: 8px;
                }

                .mode-btn {
                    background: #2d2d2d;
                    color: #aaa;
                    border: 2px solid transparent;
                    padding: 8px 16px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: bold;
                    transition: background 0.15s, color 0.15s, border-color 0.15s;
                }

                .mode-btn:hover {
                    background: #3a3a3a;
                    color: white;
                }

                .mode-btn.active {
                    background: #1a3a1a;
                    color: #7CFC00;
                    border-color: #7CFC00;
                }

                .card-container {
                    display: flex;
                    gap: 20px;
                    align-items: stretch;
                }

                .card {
                    flex: 1;
                    background: #1c1c1c;
                    padding: 20px;
                    border-radius: 12px;
                }

                @media (max-width: 900px) {
                    .card-container {
                        flex-direction: column;
                    }
                }

                h1, h2 {
                    margin-top: 0;
                }

                label {
                    display: block;
                    margin-bottom: 8px;
                    font-size: 18px;
                }

                input[type=range] {
                    width: 100%;
                }

                input[type=number] {
                    width: 100%;
                    padding: 10px;
                    border-radius: 8px;
                    border: none;
                    background: #2a2a2a;
                    color: white;
                    font-size: 16px;
                    box-sizing: border-box;
                }

                .value {
                    font-size: 16px;
                    margin-top: 8px;
                    color: #aaa;
                }

                .status {
                    margin-top: 20px;
                    color: #7CFC00;
                    font-size: 14px;
                }

                .button-row {
                    display: flex;
                    gap: 12px;
                    margin-top: 20px;
                    flex-wrap: wrap;
                }

                button {
                    background: #2d2d2d;
                    color: white;
                    border: none;
                    padding: 12px 18px;
                    border-radius: 10px;
                    cursor: pointer;
                    font-size: 15px;
                }

                button:hover {
                    background: #3a3a3a;
                }

                .number-row {
                    margin-bottom: 18px;
                }
            </style>
        </head>

        <body>

            <div class="top-bar">
                <h1>Pan / Tilt PID Gain Tuning</h1>

                <div class="mode-box">
                    <div class="mode-label">Mode</div>
                    <div class="mode-buttons">
                        <button class="mode-btn" data-mode="idle"   onclick="setMode('idle')">Idle</button>
                        <button class="mode-btn" data-mode="track"  onclick="setMode('track')">Track</button>
                        <button class="mode-btn" data-mode="manual" onclick="setMode('manual')">Manual</button>
                    </div>
                </div>

                <div class="fps-box">
                    <div class="fps-label">Main Loop FPS</div>
                    <div class="fps-value" id="main_loop_fps">0.00</div>
                </div>
            </div>

            <div class="card-container">

                <div class="card">
                    <h2>Pan</h2>

                    <label for="pan_kp">Pan Kp</label>
                    <input type="range" id="pan_kp" min="0" max="10" step="0.01" value="{{ pan_kp }}">
                    <div class="value">Value: <span id="pan_kp_value">{{ pan_kp }}</span></div>

                    <label for="pan_ki" style="margin-top:16px;">Pan Ki</label>
                    <input type="range" id="pan_ki" min="0" max="10" step="0.01" value="{{ pan_ki }}">
                    <div class="value">Value: <span id="pan_ki_value">{{ pan_ki }}</span></div>

                    <label for="pan_kd" style="margin-top:16px;">Pan Kd</label>
                    <input type="range" id="pan_kd" min="0" max="10" step="0.01" value="{{ pan_kd }}">
                    <div class="value">Value: <span id="pan_kd_value">{{ pan_kd }}</span></div>
                </div>

                <div class="card">
                    <h2>Tilt</h2>

                    <label for="tilt_kp">Tilt Kp</label>
                    <input type="range" id="tilt_kp" min="0" max="10" step="0.01" value="{{ tilt_kp }}">
                    <div class="value">Value: <span id="tilt_kp_value">{{ tilt_kp }}</span></div>

                    <label for="tilt_ki" style="margin-top:16px;">Tilt Ki</label>
                    <input type="range" id="tilt_ki" min="0" max="10" step="0.01" value="{{ tilt_ki }}">
                    <div class="value">Value: <span id="tilt_ki_value">{{ tilt_ki }}</span></div>

                    <label for="tilt_kd" style="margin-top:16px;">Tilt Kd</label>
                    <input type="range" id="tilt_kd" min="0" max="10" step="0.01" value="{{ tilt_kd }}">
                    <div class="value">Value: <span id="tilt_kd_value">{{ tilt_kd }}</span></div>
                </div>

                <div class="card">
                    <h2>Manual Commands</h2>

                    <div class="number-row">
                        <label for="set_velocity">Set Velocity</label>
                        <input type="number" id="set_velocity" step="any" value="{{ set_velocity }}">
                    </div>

                    <div class="number-row">
                        <label for="set_position">Set Position</label>
                        <input type="number" id="set_position" step="any" value="{{ set_position }}">
                    </div>

                    <div class="button-row">
                        <button onclick="saveNumberField('set_velocity')">Send Velocity</button>
                        <button onclick="saveNumberField('set_position')">Send Position</button>
                    </div>
                </div>

            </div>

            <div class="button-row">
                <button onclick="resetDefaults()">Reset to Default</button>
            </div>

            <div class="status" id="status">Ready</div>

            <script>
                const statusEl = document.getElementById("status");
                const fpsEl = document.getElementById("main_loop_fps");

                const sliderIds = [
                    "pan_kp","pan_ki","pan_kd",
                    "tilt_kp","tilt_ki","tilt_kd"
                ];

                const numberIds = [
                    "set_velocity",
                    "set_position"
                ];

                function setupSlider(sliderId) {
                    const slider = document.getElementById(sliderId);
                    const valueEl = document.getElementById(sliderId + "_value");

                    slider.addEventListener("input", () => {
                        valueEl.textContent = slider.value;
                        statusEl.textContent = "Editing...";
                    });

                    slider.addEventListener("change", async () => {
                        const body = {};
                        body[sliderId] = parseFloat(slider.value);

                        try {
                            const response = await fetch("/save", {
                                method: "POST",
                                headers: {
                                    "Content-Type": "application/json"
                                },
                                body: JSON.stringify(body)
                            });

                            const data = await response.json();
                            statusEl.textContent = data.message;
                        } catch {
                            statusEl.textContent = "Save failed";
                        }
                    });
                }

                async function saveNumberField(fieldId) {
                    const input = document.getElementById(fieldId);
                    const value = parseFloat(input.value);

                    if (Number.isNaN(value)) {
                        statusEl.textContent = "Invalid number";
                        return;
                    }

                    const body = {};
                    body[fieldId] = value;

                    try {
                        const response = await fetch("/save", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify(body)
                        });

                        const data = await response.json();
                        statusEl.textContent = data.message;
                    } catch {
                        statusEl.textContent = "Save failed";
                    }
                }

                async function resetDefaults() {
                    try {
                        const response = await fetch("/reset", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json"
                            }
                        });

                        const data = await response.json();

                        sliderIds.forEach(id => {
                            const slider = document.getElementById(id);
                            const valueEl = document.getElementById(id + "_value");

                            slider.value = data.gains[id];
                            valueEl.textContent = data.gains[id];
                        });

                        numberIds.forEach(id => {
                            const input = document.getElementById(id);
                            input.value = data.gains[id];
                        });

                        statusEl.textContent = data.message;
                    } catch {
                        statusEl.textContent = "Reset failed";
                    }
                }

                async function updateStatus() {
                    try {
                        const response = await fetch("/status");
                        const data = await response.json();
                        fpsEl.textContent = data.main_loop_fps.toFixed(2);
                    } catch {
                        fpsEl.textContent = "--";
                    }
                }

                async function setMode(mode) {
                    try {
                        const response = await fetch("/save", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ mode })
                        });
                        const data = await response.json();
                        statusEl.textContent = data.message;
                        updateModeButtons(mode);
                    } catch {
                        statusEl.textContent = "Mode save failed";
                    }
                }

                function updateModeButtons(activeMode) {
                    document.querySelectorAll(".mode-btn").forEach(btn => {
                        btn.classList.toggle("active", btn.dataset.mode === activeMode);
                    });
                }

                sliderIds.forEach(setupSlider);
                updateModeButtons("{{ mode }}");
                updateStatus();
                setInterval(updateStatus, 300);
            </script>

        </body>
        </html>
        """

        @self.app.route("/")
        def index():
            gains = self.load_gains()
            return render_template_string(HTML, **gains)

        @self.app.route("/save", methods=["POST"])
        def save():
            incoming = request.get_json()
            gains = self.load_gains()

            velocity_updated = False
            position_updated = False
            new_velocity = None
            new_position = None

            for key in incoming:
                if key in gains:
                    if key == "mode":
                        gains[key] = str(incoming[key])
                    else:
                        gains[key] = float(incoming[key])

                    if key == "set_velocity":
                        velocity_updated = True
                        new_velocity = gains[key]
                    elif key == "set_position":
                        position_updated = True
                        new_position = gains[key]

            self.save_gains(gains)

            if self.serial is not None:
                try:
                    if velocity_updated:
                        self.serial.updateVelocity(new_velocity)

                    if position_updated:
                        self.serial.updatePosition(new_position)

                except Exception as e:
                    return jsonify({
                        "success": False,
                        "message": f"Saved, but serial update failed: {e}",
                        "gains": gains
                    }), 500

            print(
                "[Webserver] Gains updated: "
                f"mode:{gains['mode']}, "
                f"pan_kp:{gains['pan_kp']:.3f}, "
                f"pan_ki:{gains['pan_ki']:.3f}, "
                f"pan_kd:{gains['pan_kd']:.3f}, "
                f"tilt_kp:{gains['tilt_kp']:.3f}, "
                f"tilt_ki:{gains['tilt_ki']:.3f}, "
                f"tilt_kd:{gains['tilt_kd']:.3f}, "
                f"set_velocity:{gains['set_velocity']:.3f}, "
                f"set_position:{gains['set_position']:.3f}"
            )

            return jsonify({"success": True, "message": "Saved", "gains": gains})

        @self.app.route("/reset", methods=["POST"])
        def reset():
            gains = self.default_gains.copy()
            self.save_gains(gains)

            print("[Webserver] Gains reset to default")

            return jsonify({"success": True, "message": "Reset to defaults", "gains": gains})

        @self.app.route("/gains", methods=["GET"])
        def get_gains():
            return jsonify(self.load_gains())

        @self.app.route("/status", methods=["GET"])
        def get_status():
            return jsonify({
                "main_loop_fps": self.get_main_loop_fps()
            })

    def run(self):
        import logging
        import flask.cli

        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)
        self.app.logger.disabled = True

        flask.cli.show_server_banner = lambda *args, **kwargs: None

        print(f"[Webserver] Initialized at http://{self.host}:{self.port}")

        self.app.run(
            host=self.host,
            port=self.port,
            debug=False,
            use_reloader=False
        )