import sys
import time

from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtUiTools import QUiLoader
import serial
import serial.tools.list_ports


class BluetoothSearchThread(QtCore.QThread):
    devices_found = QtCore.Signal(list)

    def __init__(self, serial_port):
        super().__init__()
        self.serial_port = serial_port

    def run(self):
        try:
            # 블루투스 장치 검색 명령 실행
            self.serial_port.write(b'AT+BTINQ?\r\n')
            response = self.serial_port.read_until(b'OK\r\n').decode()

            # 검색된 장치 목록 파싱
            devices = self.parse_bluetooth_inquiry(response)
            self.devices_found.emit(devices)
        except serial.SerialException as e:
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


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loader = QUiLoader()

        # UI 파일 로드
        self.ui = loader.load("MainWindow.ui", None)
        self.setCentralWidget(self.ui)
        self.setFixedSize(self.ui.size())
        self.center_window()

        # comPort
        self.comPortComboBox = self.ui.findChild(QtWidgets.QComboBox, "comPortComboBox")

        # Refresh Button(comPort)
        self.refreshButton = self.ui.findChild(QtWidgets.QPushButton, "refreshButton")
        self.refreshButton.clicked.connect(self.setup_serial_ports)

        # Connect Button(comPort)
        self.connectButton = self.ui.findChild(QtWidgets.QPushButton, "connectButton")
        self.connectButton.clicked.connect(self.on_connect_button_clicked)

        # baudRate
        self.baudRateComboBox = self.ui.findChild(QtWidgets.QComboBox, "baudRateComboBox")

        # 로그
        self.logTextBrowser = self.ui.findChild(QtWidgets.QTextBrowser, "logTextBrowser")
        self.logTextBrowser.setReadOnly(True)  # 읽기 전용

        # bt search
        self.btSearchButton = self.ui.findChild(QtWidgets.QPushButton, "btSearchButton")
        self.btSearchButton.clicked.connect(self.search_for_devices)

        # bt search using thread
        self.bluetoothThread = None

        # Serial port
        self.serial_port = None
        self.setup_serial_ports()

        #led on off for test
        self.ledOnButton = self.ui.findChild(QtWidgets.QPushButton, "ledOnButton")
        self.ledOffButton = self.ui.findChild(QtWidgets.QPushButton, "ledOffButton")
        self.ledOnButton.clicked.connect(self.turn_led_on)
        self.ledOffButton.clicked.connect(self.turn_led_off)


        # timer test


    def turn_led_on(self):
        """LED를 켜기 위해 '1'을 Arduino에 전송"""
        self.serial_port.write(b'1')
        self.log_message("Sent: 1 (LED ON)")

    def turn_led_off(self):
        """LED를 끄기 위해 '0'을 Arduino에 전송"""
        self.serial_port.write(b'0')
        self.log_message("Sent: 0 (LED OFF)")

    def setup_serial_ports(self):
        self.comPortComboBox.clear()
        ports = serial.tools.list_ports.comports()
        for port in sorted(ports):
            self.comPortComboBox.addItem(port.device)

        self.log_message("COM 포트 목록이 갱신되었습니다.")

        baudrates = ["9600", "19200", "38400", "57600", "115200"]
        self.baudRateComboBox.addItems(baudrates)

    def on_connect_button_clicked(self):
        selected_port = self.comPortComboBox.currentText()
        selected_baud_rate = self.baudRateComboBox.currentText()
        self.log_message(f"시리얼 포트 {selected_port}에 연결 시도 중...")

        if self.serial_port:
            self.serial_port.close()

        try:
            self.serial_port = serial.Serial(selected_port, selected_baud_rate)
            self.log_message(f"{selected_port}에 성공적으로 연결되었습니다.")
        except serial.SerialException as e:
            self.log_message(f"연결 실패: {str(e)}")

    def center_window(self):
        screen = QtWidgets.QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        screen_center = screen_geometry.center()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen_center)
        self.move(window_geometry.topLeft())

    def log_message(self, message):
        self.logTextBrowser.append(message)
        self.logTextBrowser.moveCursor(QtGui.QTextCursor.End)
        self.logTextBrowser.ensureCursorVisible()

    def search_for_devices(self):
        """백그라운드 스레드를 통해 블루투스 장치 검색."""
        self.log_message("블루투스 장치 검색 중...")
        self.log_message("오래 걸릴 수 있으니 기다려주세요...")

        self.btSearchButton.setEnabled(False)  # 검색 중 버튼 비활성화

        # QThread 시작
        self.bluetoothThread = BluetoothSearchThread(self.serial_port)
        self.bluetoothThread.devices_found.connect(self.on_devices_found)
        self.bluetoothThread.start()

    def on_devices_found(self, devices):
        """스레드에서 장치 검색이 완료되었을 때 호출."""
        if devices:
            self.log_message(f"{len(devices)}개의 장치가 검색되었습니다.")
            for address, name in devices:
                self.log_message(f"Device: {name}, Address: {address}")

            # 장치 목록을 팝업 창에서 선택하도록 함
            selected_device = self.show_device_selection_dialog(devices)
            if selected_device:
                self.connect_to_device(selected_device)
        else:
            self.log_message("장치를 찾을 수 없습니다.")

        self.btSearchButton.setEnabled(True)  # 검색 완료 후 버튼 활성화

    def show_device_selection_dialog(self, devices):
        """팝업 창에서 검색된 블루투스 장치를 선택하도록 함."""
        items = [f"{name} ({address})" for address, name in devices]
        item, ok = QtWidgets.QInputDialog.getItem(self, "Bluetooth Devices", "Select a device to connect:", items, 0, False)

        if ok and item:
            # Extract address from the selected item
            for address, name in devices:
                if name in item:
                    return address
        return None

    def connect_to_device(self, address):
        """Connects to the selected Bluetooth device using the ATD command."""
        try:
            # '+++' 명령어로 모듈을 커맨드 모드로 전환
            self.serial_port.write(b'+++\r\n')
            time.sleep(0.5)  # 500ms 대기

            # '+++' 명령어에 대한 응답 읽기 (무시)
            self.serial_port.read_until(b'\r\n')  # 첫 번째 \r\n (빈 줄)
            self.serial_port.read_until(b'\r\n')  # OK 또는 ERROR (무시)

            # 'ATH' 명령어로 연결을 끊음 (기존 연결이 있을 경우)
            self.serial_port.write(b'ATH\r\n')
            time.sleep(0.5)  # 500ms 대기

            # 'ATH' 명령어에 대한 응답 읽기 (무시)
            self.serial_port.read_until(b'\r\n')  # 첫 번째 \r\n (빈 줄)
            self.serial_port.read_until(b'\r\n')  # OK 또는 ERROR (무시)

            # ATD 명령어로 장치에 연결 시도
            command = f"ATD{address}\r\n"
            self.serial_port.write(command.encode())
            time.sleep(0.5)

            # 첫 번째 응답: OK가 올 때까지 대기
            ok_response = self.serial_port.read_until(b'OK\r\n').decode().strip()
            self.log_message("첫 번째 응답")
            self.log_message(ok_response)
            # 첫 번째 응답이 OK인지 확인
            if ok_response == "OK":
                # 두 번째 응답: 빈 줄 (\r\n)을 읽음
                self.serial_port.read_until(b'\r\n')

                # 세 번째 응답: CONNECT 또는 ERROR가 올 때까지 대기
                second_response = self.serial_port.read_until(b'\r\n').decode().strip()
                self.log_message("두 번째 응답")
                self.log_message(second_response)
                # 두 번째 응답이 'CONNECT' 또는 'ERROR'인지 확인
                if "CONNECT" in second_response:
                    self.log_message(f"성공적으로 {address}에 연결되었습니다: {second_response}")
                elif "ERROR" in second_response:
                    self.log_message(f"{address} 연결 실패.")
                else:
                    self.log_message(f"예상치 못한 응답: {second_response}")
            else:
                self.log_message(f"첫 번째 응답에서 OK가 확인되지 않았습니다: {ok_response}")

        except serial.SerialException as e:
            self.log_message(f"연결 중 오류 발생: {e}")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
