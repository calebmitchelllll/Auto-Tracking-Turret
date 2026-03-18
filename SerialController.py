import time
import threading
import serial
import serial.tools.list_ports


class SerialController:
    def __init__(self, port="/dev/cu.usbmodem183380201", baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

        self.reader_thread = None
        self.reader_running = False

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            time.sleep(2)
            print(f"[Serial] Connected to {self.port} @ {self.baudrate}")
            return True
        except Exception as e:
            print(f"[Serial] Connection failed: {e}")
            self.ser = None
            return False

    def disconnect(self):
        self.stop_reader()

        if self.ser is not None:
            try:
                self.ser.close()
                print("[Serial] Disconnected")
            except Exception as e:
                print(f"[Serial] Disconnect error: {e}")

        self.ser = None

    def isConnected(self):
        return self.ser is not None and self.ser.is_open

    def sendLine(self, msg):
        if not self.isConnected():
            raise RuntimeError("Serial not connected")

        self.ser.write((msg + "\n").encode("utf-8"))
        self.ser.flush()
        print(f"[Sending] {msg}")

    def sendHeartbeat(self, counter):
        if counter % 10 == 0:
            self.sendLine("HEARTBEAT")

    def updateVelocity(self, value):
        self.sendLine(f"SET_VELOCITY:{value}")

    def updatePosition(self, value):
        self.sendLine(f"SET_POSITION:{value}")

    def sendTargetError(self, err_x, err_y):
        self.sendLine(f"TARGET:{err_x:.2f},{err_y:.2f}")

    def readLine(self):
        if not self.isConnected():
            return None

        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode("utf-8", errors="ignore").strip()
                if line:
                    print(f"[Reading] {line}")
                    return line
        except Exception as e:
            print(f"[Serial] Read error: {e}")

        return None

    def _reader_loop(self):
        while self.reader_running:
            try:
                self.readLine()
            except Exception as e:
                print(f"[Serial Reader] {e}")
            time.sleep(0.01)

    def start_reader(self):
        if self.reader_thread is not None and self.reader_thread.is_alive():
            print("[Serial] Reader already running")
            return

        self.reader_running = True
        self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.reader_thread.start()
        print("[Serial] Reader thread started")

    def stop_reader(self):
        self.reader_running = False

        if self.reader_thread is not None:
            self.reader_thread.join(timeout=1.0)
            self.reader_thread = None
            print("[Serial] Reader thread stopped")

    @staticmethod
    def list_ports():
        print("[Serial] Available ports:")
        for port in serial.tools.list_ports.comports():
            print(f"  {port.device} - {port.description}")