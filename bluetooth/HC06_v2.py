import serial
import time

class HC06Bluetooth:
    """HC-06/HC-05 블루투스 모듈 초기화 및 설정 클래스 (다중 펌웨어 지원)"""
    
    # 지원하는 baudrate 목록
    BAUDRATES = [9600, 38400, 19200, 57600, 115200, 4800, 2400, 1200]
    
    # 명령어 형식 (펌웨어 버전별)
    COMMAND_FORMATS = {
        'v1': {  # 구형 펌웨어 (AT 명령어만)
            'test': ['AT'],
            'version': ['AT+VERSION'],
            'name': ['AT+NAME{}'],
            'pin': ['AT+PIN{}', 'AT+PSWD{}'],
            'baud': ['AT+BAUD{}', 'AT+UART={},0,0']
        },
        'v2': {  # 신형 펌웨어 (AT+명령어)
            'test': ['AT'],
            'version': ['AT+VERSION?', 'AT+VERSION'],
            'name': ['AT+NAME={}', 'AT+NAME{}'],
            'pin': ['AT+PSWD={}', 'AT+PIN={}', 'AT+PSWD{}', 'AT+PIN{}'],
            'baud': ['AT+UART={},0,0', 'AT+BAUD{}']
        }
    }
    
    # Baudrate 코드 매핑 (AT+BAUD 명령용)
    BAUD_CODES = {
        1200: '1', 2400: '2', 4800: '3', 9600: '4',
        19200: '5', 38400: '6', 57600: '7', 115200: '8'
    }
    
    def __init__(self, port, timeout=1):
        """
        HC-06 모듈 초기화 (자동 baudrate 탐지)
        
        Args:
            port: 시리얼 포트 (예: 'COM3' 또는 '/dev/ttyUSB0')
            timeout: 타임아웃 시간 (초)
        """
        self.port = port
        self.timeout = timeout
        self.serial = None
        self.current_baudrate = None
        self.command_format = None
        
        print("HC-06/HC-05 모듈 연결 시도 중...")
        
        # 자동으로 baudrate 탐지
        if not self.auto_detect_baudrate():
            raise Exception("모듈을 찾을 수 없습니다. 연결을 확인하세요.")
    
    def auto_detect_baudrate(self):
        """자동으로 올바른 baudrate를 탐지"""
        print(f"\n{'='*50}")
        print("자동 Baudrate 탐지 시작...")
        print(f"{'='*50}")
        
        for baudrate in self.BAUDRATES:
            print(f"\n[시도] Baudrate: {baudrate}...", end=' ')
            
            try:
                if self.serial and self.serial.is_open:
                    self.serial.close()
                    time.sleep(0.3)
                
                self.serial = serial.Serial(self.port, baudrate, timeout=self.timeout)
                time.sleep(0.5)  # 안정화 대기
                
                # 버퍼 클리어
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
                
                # 여러 명령어 형식 시도
                for format_name, commands in self.COMMAND_FORMATS.items():
                    for test_cmd in commands['test']:
                        response = self._send_raw_command(test_cmd, wait_time=0.3)
                        
                        if response and ('OK' in response or 'ok' in response.lower()):
                            self.current_baudrate = baudrate
                            self.command_format = format_name
                            print(f"✓ 성공!")
                            print(f"\n{'='*50}")
                            print(f"모듈 발견!")
                            print(f"  - Baudrate: {baudrate}")
                            print(f"  - 명령어 형식: {format_name}")
                            print(f"  - 응답: {response}")
                            print(f"{'='*50}\n")
                            return True
                
                print("✗ 응답 없음")
                
            except serial.SerialException as e:
                print(f"✗ 오류: {e}")
                continue
            except Exception as e:
                print(f"✗ 예외: {e}")
                continue
        
        print("\n모든 baudrate에서 응답이 없습니다.")
        return False
    
    def _send_raw_command(self, command, wait_time=0.5):
        """원시 명령어 전송 (내부 사용)"""
        if not self.serial or not self.serial.is_open:
            return ""
        
        try:
            # 버퍼 클리어
            self.serial.reset_input_buffer()
            
            # 명령어 전송 (CR/LF 없이, 있는 버전도 시도)
            self.serial.write(command.encode())
            time.sleep(wait_time)
            
            response = ""
            if self.serial.in_waiting > 0:
                response = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            
            return response.strip()
        except Exception as e:
            return ""
    
    def send_command(self, cmd_type, *args, wait_time=0.5):
        """
        명령어 전송 (자동으로 여러 형식 시도)
        
        Args:
            cmd_type: 명령어 타입 ('test', 'version', 'name', 'pin', 'baud')
            *args: 명령어 인자
            wait_time: 응답 대기 시간
        
        Returns:
            (성공여부, 응답)
        """
        if not self.command_format:
            return False, "모듈이 초기화되지 않았습니다."
        
        commands = self.COMMAND_FORMATS[self.command_format].get(cmd_type, [])
        
        for cmd_template in commands:
            # 명령어 생성
            if '{}' in cmd_template:
                command = cmd_template.format(*args)
            else:
                command = cmd_template
            
            print(f"  [전송] {command}...", end=' ')
            response = self._send_raw_command(command, wait_time)
            
            if response:
                print(f"응답: {response}")
                if 'OK' in response or 'ok' in response.lower():
                    return True, response
                return True, response  # 응답이 있으면 성공으로 간주
            else:
                print("응답 없음")
        
        # 모든 형식 실패 시 다른 형식도 시도
        for format_name, format_cmds in self.COMMAND_FORMATS.items():
            if format_name == self.command_format:
                continue
            
            commands = format_cmds.get(cmd_type, [])
            for cmd_template in commands:
                if '{}' in cmd_template:
                    command = cmd_template.format(*args)
                else:
                    command = cmd_template
                
                print(f"  [대체 시도] {command}...", end=' ')
                response = self._send_raw_command(command, wait_time)
                
                if response:
                    print(f"응답: {response}")
                    if 'OK' in response or 'ok' in response.lower():
                        return True, response
                    return True, response
                else:
                    print("응답 없음")
        
        return False, "모든 명령어 형식에서 응답 없음"
    
    def test_connection(self):
        """연결 테스트"""
        print("\n=== 연결 테스트 ===")
        success, response = self.send_command('test')
        if success:
            print(f"✓ 연결 성공!")
            return True
        else:
            print(f"✗ 연결 실패: {response}")
            return False
    
    def get_version(self):
        """펌웨어 버전 확인"""
        print("\n=== 펌웨어 버전 확인 ===")
        success, response = self.send_command('version')
        if success:
            print(f"버전 정보: {response}")
        else:
            print(f"버전 확인 실패 (일부 모듈은 지원하지 않음)")
        return response
    
    def set_name(self, name):
        """블루투스 이름 설정"""
        print(f"\n=== 블루투스 이름 설정: {name} ===")
        success, response = self.send_command('name', name, wait_time=1.0)
        if success:
            print(f"✓ 이름 설정 성공!")
        else:
            print(f"✗ 이름 설정 실패")
        return success
    
    def set_pin(self, pin):
        """PIN 코드 설정"""
        print(f"\n=== PIN 코드 설정: {pin} ===")
        success, response = self.send_command('pin', pin, wait_time=1.0)
        if success:
            print(f"✓ PIN 설정 성공!")
        else:
            print(f"✗ PIN 설정 실패")
        return success
    
    def set_baudrate(self, target_baudrate):
        """
        통신 속도 설정
        
        Args:
            target_baudrate: 목표 baudrate (예: 115200)
        """
        print(f"\n=== 통신 속도 설정: {target_baudrate} ===")
        
        # AT+UART 형식 시도 (HC-05 및 일부 HC-06)
        success, response = self.send_command('baud', target_baudrate, wait_time=1.0)
        
        if not success and target_baudrate in self.BAUD_CODES:
            # AT+BAUD 코드 형식 시도 (구형 HC-06)
            baud_code = self.BAUD_CODES[target_baudrate]
            success, response = self.send_command('baud', baud_code, wait_time=1.0)
        
        if success:
            print(f"✓ 통신 속도 설정 성공!")
            print(f"⚠ 모듈 전원을 껐다 켜면 {target_baudrate}로 변경됩니다.")
        else:
            print(f"✗ 통신 속도 설정 실패")
        
        return success
    
    def reset_module(self):
        """모듈 소프트 리셋 시도 (일부 펌웨어만 지원)"""
        print("\n=== 모듈 리셋 시도 ===")
        reset_commands = ['AT+RESET', 'AT+RST']
        
        for cmd in reset_commands:
            print(f"  [전송] {cmd}...", end=' ')
            response = self._send_raw_command(cmd, wait_time=1.0)
            if response:
                print(f"응답: {response}")
                time.sleep(2)  # 리셋 대기
                return True
            else:
                print("응답 없음")
        
        print("리셋 명령어가 지원되지 않습니다. 수동으로 전원을 껐다 켜세요.")
        return False
    
    def close(self):
        """시리얼 연결 종료"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("\n시리얼 연결이 종료되었습니다.")


def main():
    """HC-06 모듈 설정 예제"""
    
    # 시리얼 포트 설정
    PORT = 'COM8'  # 사용자 환경에 맞게 수정
    
    try:
        # HC-06 모듈 연결 (자동 baudrate 탐지)
        hc06 = HC06Bluetooth(PORT)
        
        # 연결 테스트
        hc06.test_connection()
        
        # 펌웨어 버전 확인
        hc06.get_version()
        
        # 블루투스 이름 변경
        hc06.set_name("MyHC06-011")
        
        # PIN 코드 변경
        hc06.set_pin("1234")
        
        # 통신 속도를 115200으로 변경
        hc06.set_baudrate(115200)
        
        print("\n" + "="*50)
        print("설정 완료!")
        print("="*50)
        print("⚠ 중요: 모듈의 전원을 껐다 켜야 새 설정이 적용됩니다.")
        print("전원 재시작 후 다음 설정으로 연결하세요:")
        print(f"  - Baudrate: 115200")
        print(f"  - 이름: MyHC06")
        print(f"  - PIN: 1234")
        print("="*50)
        
        # 연결 종료
        hc06.close()
        
    except Exception as e:
        print(f"\n오류 발생: {e}")
        print("\n문제 해결 방법:")
        print("1. HC-06 모듈이 페어링되지 않은 상태인지 확인")
        print("2. 배선 확인: TX-RX, RX-TX 교차 연결")
        print("3. 전원 확인: VCC(3.3V 또는 5V), GND")
        print("4. 다른 프로그램이 COM 포트를 사용 중인지 확인")


if __name__ == "__main__":
    main()