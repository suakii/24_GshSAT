from PySide2 import QtCore


class BluetoothSearchThread(QtCore.QThread):
    devices_found = QtCore.Signal(list)

    def __init__(self, communication):
        super().__init__()
        self.communication = communication

    def run(self):
        try:
            self.communication.send_data('AT+BTINQ?\r\n')
            response = self.communication.read_until(b'OK\r\n').decode()
            devices = self.parse_bluetooth_inquiry(response)
            self.devices_found.emit(devices)
        except Exception as e:
            self.devices_found.emit([])

    def parse_bluetooth_inquiry(self, response):
        devices = []
        lines = response.splitlines()
        for line in lines:
            if "," in line:
                address, name, _ = line.split(",")
                devices.append((address.strip(), name.strip()))
        return devices
