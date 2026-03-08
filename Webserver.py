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
            "tilt_kp": 1.0
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
        os.makedirs(os.path.dirname(self.json_file), exist_ok=True)

        with open(self.json_file, "w") as f:
            json.dump(data, f, indent=2)

    def _setup_routes(self):
        HTML = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Pan / Tilt Gains</title>
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 500px;
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
            </style>
        </head>
        <body>
            <h1>Pan / Tilt Gain Tuning</h1>

            <div class="card">
                <label for="pan_kp">Pan Kp</label>
                <input type="range" id="pan_kp" min="0" max="10" step="0.01" value="{{ pan_kp }}">
                <div class="value">Value: <span id="pan_kp_value">{{ pan_kp }}</span></div>
            </div>

            <div class="card">
                <label for="tilt_kp">Tilt Kp</label>
                <input type="range" id="tilt_kp" min="0" max="10" step="0.01" value="{{ tilt_kp }}">
                <div class="value">Value: <span id="tilt_kp_value">{{ tilt_kp }}</span></div>
            </div>

            <div class="status" id="status">Ready</div>

            <script>
                const statusEl = document.getElementById("status");

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

                setupSlider("pan_kp");
                setupSlider("tilt_kp");
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
            # ---- log update ----
            print(f"[Webserver] Gains updated: pan_kp:{gains['pan_kp']:.3f}, tilt_kp:{gains['tilt_kp']:.3f}")

            return jsonify({
                "success": True,
                "message": f"Saved: {gains}"
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