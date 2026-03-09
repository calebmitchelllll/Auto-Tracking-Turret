from flask import Flask, request, jsonify, render_template_string
import json
import os


class Webserver:
    def __init__(self, json_file="saved_data/gains.json", host="127.0.0.1", port=5000):
        self.json_file = json_file
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        self.default_gains = {
            "pan_kp": 1.0,
            "pan_ki": 1.0,
            "pan_kd": 1.0,
            "tilt_kp": 1.0,
            "tilt_ki": 1.0,
            "tilt_kd": 1.0
        }
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
                    max-width: 600px;
                    margin: 40px auto;
                    padding: 20px;
                    background: #111;
                    color: white;
                }

                .card {
                    background: #1c1c1c;
                    padding: 20px;
                    border-radius: 12px;
                    margin-bottom: 20px;
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
            </style>
        </head>
        <body>
            <h1>Pan / Tilt PID Gain Tuning</h1>

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

            <div class="button-row">
                <button onclick="resetDefaults()">Reset to Default</button>
            </div>

            <div class="status" id="status">Ready</div>

            <script>
                const statusEl = document.getElementById("status");

                const sliderIds = [
                    "pan_kp", "pan_ki", "pan_kd",
                    "tilt_kp", "tilt_ki", "tilt_kd"
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
                        } catch (err) {
                            statusEl.textContent = "Save failed";
                        }
                    });
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

                        sliderIds.forEach((id) => {
                            const slider = document.getElementById(id);
                            const valueEl = document.getElementById(id + "_value");
                            slider.value = data.gains[id];
                            valueEl.textContent = data.gains[id];
                        });

                        statusEl.textContent = data.message;
                    } catch (err) {
                        statusEl.textContent = "Reset failed";
                    }
                }

                sliderIds.forEach(setupSlider);
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

            for key in incoming:
                if key in gains:
                    gains[key] = float(incoming[key])

            self.save_gains(gains)

            print(
                "[Webserver] Gains updated: "
                f"pan_kp:{gains['pan_kp']:.3f}, "
                f"pan_ki:{gains['pan_ki']:.3f}, "
                f"pan_kd:{gains['pan_kd']:.3f}, "
                f"tilt_kp:{gains['tilt_kp']:.3f}, "
                f"tilt_ki:{gains['tilt_ki']:.3f}, "
                f"tilt_kd:{gains['tilt_kd']:.3f}"
            )

            return jsonify({
                "success": True,
                "message": "Saved",
                "gains": gains
            })

        @self.app.route("/reset", methods=["POST"])
        def reset():
            gains = self.default_gains.copy()
            self.save_gains(gains)

            print(
                "[Webserver] Gains reset to default: "
                f"pan_kp:{gains['pan_kp']:.3f}, "
                f"pan_ki:{gains['pan_ki']:.3f}, "
                f"pan_kd:{gains['pan_kd']:.3f}, "
                f"tilt_kp:{gains['tilt_kp']:.3f}, "
                f"tilt_ki:{gains['tilt_ki']:.3f}, "
                f"tilt_kd:{gains['tilt_kd']:.3f}"
            )

            return jsonify({
                "success": True,
                "message": "Reset to defaults",
                "gains": gains
            })

        @self.app.route("/gains", methods=["GET"])
        def get_gains():
            return jsonify(self.load_gains())

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