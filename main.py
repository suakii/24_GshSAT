import sys
import time
from PySide2 import QtWidgets, QtCore, QtGui
from PySide2.QtCore import QTimer
from PySide2.QtUiTools import QUiLoader
import serial.tools.list_ports
from communications import Communication
from bluetoothsearchthread import BluetoothSearchThread


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loader = QUiLoader()

        self.ui = loader.load("MainWindow.ui", None)
        self.setCentralWidget(self.ui)
        self.setFixedSize(self.ui.size())
        self.center_window()

        self.comPortComboBox = self.ui.findChild(QtWidgets.QComboBox, "comPortComboBox")

        self.refreshButton = self.ui.findChild(QtWidgets.QPushButton, "refreshButton")
        self.refreshButton.clicked.connect(self.setup_serial_ports)

        self.connectButton = self.ui.findChild(QtWidgets.QPushButton, "connectButton")
        self.connectButton.clicked.connect(self.on_connect_button_clicked)

        self.baudRateComboBox = self.ui.findChild(QtWidgets.QComboBox, "baudRateComboBox")

        self.logTextBrowser = self.ui.findChild(QtWidgets.QTextBrowser, "logTextBrowser")
        self.logTextBrowser.setReadOnly(True)

        # bt search
        self.btSearchButton = self.ui.findChild(QtWidgets.QPushButton, "btSearchButton")
        self.btSearchButton.clicked.connect(self.search_for_devices)

        self.communication = None

        self.bluetoothThread = None

        self.setup_serial_ports()

        self.ledOnButton = self.ui.findChild(QtWidgets.QPushButton, "ledOnButton")
        self.ledOffButton = self.ui.findChild(QtWidgets.QPushButton, "ledOffButton")
        self.ledOnButton.clicked.connect(self.turn_led_on)
        self.ledOffButton.clicked.connect(self.turn_led_off)

        # timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_data)


    def turn_led_on(self):
        if self.communication and not self.communication.dummy_mode():
            self.communication.send_data('1')
        else:
            self.log_message("Serial port is not open or dummy mode is active.")

    def turn_led_off(self):
        if self.communication and not self.communication.dummy_mode():
            self.communication.send_data('0')
        else:
            self.log_message("Serial port is not open or dummy mode is active.")

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

        if self.communication:
            self.communication.close()

        self.communication = Communication(selected_port, int(selected_baud_rate), self.log_message, True)

        if self.communication.is_open:
            self.log_message(f"{selected_port}에 성공적으로 연결되었습니다.")
        else:
            self.log_message(f"{selected_port}에 연결할 수 없습니다.")

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
        self.log_message("블루투스 장치 검색 중...")
        self.log_message("오래 걸릴 수 있으니 기다려주세요...")
        self.btSearchButton.setEnabled(False)
        self.bluetoothThread = BluetoothSearchThread(self.communication)
        self.bluetoothThread.devices_found.connect(self.on_devices_found)
        self.bluetoothThread.start()

    def on_devices_found(self, devices):
        if devices:
            self.log_message(f"{len(devices)}개의 장치가 검색되었습니다.")
            for address, name in devices:
                self.log_message(f"Device: {name}, Address: {address}")

            selected_device = self.show_device_selection_dialog(devices)
            if selected_device:
                self.connect_to_device(selected_device)
        else:
            self.log_message("장치를 찾을 수 없습니다.")

        self.btSearchButton.setEnabled(True)

    def show_device_selection_dialog(self, devices):
        items = [f"{name} ({address})" for address, name in devices]
        item, ok = QtWidgets.QInputDialog.getItem(self, "Bluetooth Devices", "Select a device to connect:", items, 0,
                                                  False)

        if ok and item:
            for address, name in devices:
                if name in item:
                    return address
        return None

    def connect_to_device(self, address):
        try:
            self.communication.send_data('+++\r\n')
            time.sleep(0.5)

            self.communication.read_until(b'\r\n')
            self.communication.read_until(b'\r\n')

            self.communication.send_data('ATH\r\n')
            time.sleep(0.5)

            self.communication.read_until(b'\r\n')
            self.communication.read_until(b'\r\n')

            command = f"ATD{address}\r\n"
            self.communication.send_data(command)
            time.sleep(0.5)

            ok_response = self.communication.read_until(b'OK\r\n').decode().strip()
            self.log_message("첫 번째 응답")
            self.log_message(ok_response)
            if ok_response == "OK":
                self.communication.read_until(b'\r\n')

                second_response = self.communication.read_until(b'\r\n').decode().strip()
                self.log_message("두 번째 응답")
                self.log_message(second_response)
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

    def start_data_updates(self, interval_ms):
        self.timer.start(interval_ms)

    def stop_data_updates(self):
        self.timer.stop()
    def update_data(self):
        if self.communication:
            data = self.communication.get_data()




if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    window.start_data_updates(500)
    sys.exit(app.exec_())
