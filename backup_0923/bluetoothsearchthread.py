# BluetoothSearchThread.py

from PySide2 import QtCore

class BluetoothSearchThread(QtCore.QThread):
    devices_found = QtCore.Signal(list)

    def __init__(self, communication):
        super().__init__()
        self.communication = communication

    def run(self):
        try:
            # 블루투스 장치 검색 명령 실행
            self.communication.send_data('AT+BTINQ?\r\n')
            time.sleep(2)
            response = self.communication.read_until('OK\r\n')

            # 검색된 장치 목록 파싱
            devices = self.parse_bluetooth_inquiry(response)
            self.devices_found.emit(devices)
        except Exception as e:
            print("error: ", e)
            self.devices_found.emit([])  # 에러가 발생하면 빈 목록을 반환

    def parse_bluetooth_inquiry(self, response):
        """AT+BTINQ? 응답을 파싱하여 블루투스 장치 목록 추출."""
        devices = []
        lines = response.splitlines()
        for line in lines:
            if "," in line:
                address, name, _ = line.split(",")
                devices.append((address.strip(), name.strip()))
        return devices
