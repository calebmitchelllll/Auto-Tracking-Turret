import serial
import serial.tools.list_ports
import time


class USBConnection:
    def __init__(self, port=None, baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None

    def list_devices(self):
        """Return a list of available serial USB devices."""
        ports = serial.tools.list_ports.comports()
        devices = []
        for p in ports:
            devices.append({
                "device": p.device,
                "description": p.description,
                "hwid": p.hwid
            })
        return devices

    def find_device(self, keyword=None):
        """
        Find a device automatically.
        If keyword is given, looks for it in the port description.
        """
        ports = serial.tools.list_ports.comports()
        for p in ports:
            if keyword is None:
                return p.device
            if keyword.lower() in p.description.lower():
                return p.device
        return None

    def connect(self, port=None):
        """Open the serial connection."""
        if port is not None:
            self.port = port

        if self.port is None:
            raise ValueError("No port specified")

        if self.is_connected():
            print(f"[USB] Already connected to {self.port}")
            return True

        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            time.sleep(2)  # let device initialize
            print(f"[USB] Connected to {self.port}")
            return True
        except Exception as e:
            print(f"[USB] Connection failed: {e}")
            self.ser = None
            return False

    def disconnect(self):
        """Close the serial connection."""
        if self.ser is not None and self.ser.is_open:
            self.ser.close()
            print(f"[USB] Disconnected from {self.port}")
        self.ser = None

    def is_connected(self):
        """Check if serial connection is currently open."""
        return self.ser is not None and self.ser.is_open

    def check_connection(self):
        """Print and return connection status."""
        status = self.is_connected()
        if status:
            print(f"[USB] Connected to {self.port}")
        else:
            print("[USB] Not connected")
        return status

    def reconnect(self):
        """Reconnect using the current port."""
        print("[USB] Reconnecting...")
        self.disconnect()
        time.sleep(1)
        return self.connect()

    def send(self, data):
        """Send data over USB."""
        if not self.is_connected():
            raise RuntimeError("USB not connected")

        if isinstance(data, str):
            data = data.encode()

        self.ser.write(data)

    def read_line(self):
        """Read one line from USB."""
        if not self.is_connected():
            raise RuntimeError("USB not connected")

        return self.ser.readline().decode(errors="ignore").strip()