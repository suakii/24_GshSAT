import random
import serial
import serial.tools.list_ports


class Communication(serial.Serial):
    def __init__(self, port_name, baudrate=9600, log_message=None):
        # 부모 클래스(serial.Serial)의 초기화
        super().__init__(port_name, baudrate)  # 타임아웃 1초 설정
        self.log_message = log_message  # 메인에서 전달받은 log_message 함수
        self.dummyPlug = False  # 더미 모드 여부

        try:
            if self.log_message:
                self.log_message(f"Serial port {port_name} opened successfully.")
        except serial.serialutil.SerialException:
            self.dummyPlug = True
            if self.log_message:
                self.log_message(f"Can't open {port_name}. Dummy mode activated.")

    def send_data(self, data):
        """데이터 전송 (더미 모드에서는 전송 대신 시뮬레이션)"""
        if not self.dummyPlug:
            self.write(data.encode())  # 부모 클래스의 write() 메서드 사용
            if self.log_message:
                self.log_message(f"Sent: {data}")
        else:
            if self.log_message:
                self.log_message(f"Dummy send: {data}")

    # def get_data(self):
    #     """단일 데이터를 수신 (더미 모드에서는 무작위 데이터 생성)"""
    #     if not self.dummyPlug:
    #         value = self.readline()  # 부모 클래스의 readline() 메서드 사용
    #         decoded_bytes = value.decode("utf-8").strip()
    #         return decoded_bytes
    #     else:
    #         dummy_data = f"Dummy data: {random.randint(0, 100)}"
    #         if self.log_message:
    #             self.log_message(dummy_data)
    #         return dummy_data



    def dummy_mode(self):
        return self.dummyPlug
