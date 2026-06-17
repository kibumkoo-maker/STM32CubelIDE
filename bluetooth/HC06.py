import serial
import time

class HC06Bluetooth:
    """HC-06 블루투스 모듈 초기화 및 설정 클래스"""
    
    def __init__(self, port, baudrate=9600, timeout=1):
        """
        HC-06 모듈 초기화
        
        Args:
            port: 시리얼 포트 (예: 'COM3' 또는 '/dev/ttyUSB0')
            baudrate: 통신 속도 (기본값: 9600)
            timeout: 타임아웃 시간 (초)
        """
        try:
            self.serial = serial.Serial(port, baudrate, timeout=timeout)
            time.sleep(2)  # 연결 안정화 대기
            print(f"HC-06 모듈이 {port}에 연결되었습니다.")
        except serial.SerialException as e:
            print(f"시리얼 포트 연결 실패: {e}")
            raise
    
    def send_command(self, command, wait_time=0.5):
        """
        HC-06에 AT 명령어 전송
        
        Args:
            command: 전송할 AT 명령어
            wait_time: 응답 대기 시간 (초)
        
        Returns:
            응답 문자열
        """
        self.serial.write(command.encode())
        time.sleep(wait_time)
        
        response = ""
        if self.serial.in_waiting > 0:
            response = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
        
        return response.strip()
    
    def test_connection(self):
        """연결 테스트"""
        print("\n=== 연결 테스트 ===")
        response = self.send_command("AT")
        if response:
            print(f"응답: {response}")
            return True
        else:
            print("응답 없음. 연결을 확인하세요.")
            return False
    
    def set_name(self, name):
        """
        블루투스 이름 설정
        
        Args:
            name: 설정할 이름 (최대 20자)
        """
        print(f"\n=== 블루투스 이름 설정: {name} ===")
        command = f"AT+NAME{name}"
        response = self.send_command(command)
        print(f"응답: {response}")
        return response
    
    def set_pin(self, pin):
        """
        PIN 코드 설정
        
        Args:
            pin: 4자리 PIN 코드
        """
        print(f"\n=== PIN 코드 설정: {pin} ===")
        command = f"AT+PIN{pin}"
        response = self.send_command(command)
        print(f"응답: {response}")
        return response
    
    def set_baudrate(self, baudrate_code):
        """
        통신 속도 설정
        
        Args:
            baudrate_code: 
                1: 1200
                2: 2400
                3: 4800
                4: 9600 (기본값)
                5: 19200
                6: 38400
                7: 57600
                8: 115200
        """
        print(f"\n=== 통신 속도 설정 (코드: {baudrate_code}) ===")
        command = f"AT+BAUD{baudrate_code}"
        response = self.send_command(command)
        print(f"응답: {response}")
        return response
    
    def get_version(self):
        """펌웨어 버전 확인"""
        print("\n=== 펌웨어 버전 확인 ===")
        response = self.send_command("AT+VERSION")
        print(f"버전: {response}")
        return response
    
    def close(self):
        """시리얼 연결 종료"""
        if self.serial.is_open:
            self.serial.close()
            print("\n시리얼 연결이 종료되었습니다.")


def main():
    """HC-06 모듈 설정 예제"""
    
    # 시리얼 포트 설정 (사용 환경에 맞게 수정)
    PORT = 'COM8'  # Windows: 'COM3', Linux: '/dev/ttyUSB0', Mac: '/dev/tty.usbserial'
    BAUDRATE = 9600  # HC-06 기본 통신 속도
    
    try:
        # HC-06 모듈 연결
        hc06 = HC06Bluetooth(PORT, BAUDRATE)
        
        # 연결 테스트
        if not hc06.test_connection():
            print("\n주의: AT 명령에 응답이 없습니다.")
            print("- HC-06 모듈이 페어링되지 않은 상태인지 확인하세요.")
            print("- 배선과 전원을 확인하세요.")
        
        # 펌웨어 버전 확인
        hc06.get_version()
        
        # 블루투스 이름 변경
        hc06.set_name("MyHC06")
        
        # PIN 코드 변경
        hc06.set_pin("1234")
        
        # 통신 속도를 115200으로 변경
        print("\n=== 통신 속도를 115200으로 변경합니다 ===")
        hc06.set_baudrate(8)  # 8 = 115200 bps
        
        print("\n=== 설정 완료 ===")
        print("통신 속도가 115200으로 변경되었습니다.")
        print("다음 연결부터는 BAUDRATE = 115200으로 설정하세요.")
        print("블루투스 장치를 다시 검색하세요.")
        
        # 연결 종료
        hc06.close()
        
    except Exception as e:
        print(f"오류 발생: {e}")


if __name__ == "__main__":
    main()