import serial
import time

class HC06Bluetooth:
    """HC-06/HC-05 블루투스 모듈 초기화 및 설정 클래스 (다중 펌웨어 지원)"""
    
    # 지원하는 baudrate 목록
    BAUDRATES = [9600, 38400, 19200, 57600, 115200, 4800, 2400, 1200]
    
    # 명령어 형식 (펌웨어 버전별)
    COMMAND_FORMATS = {
        'hc06_no_crlf': {  # HC-06 표준 (CR/LF 없음)
            'line_ending': '',
            'test': ['AT'],
            'version': ['AT+VERSION'],
            'name': ['AT+NAME{}'],
            'pin': ['AT+PIN{}'],
            'baud': ['AT+BAUD{}'],
            'reset': ['AT+ORGL']
        },
        'hc06_with_pswd': {  # HC-06 변형 (PSWD 사용)
            'line_ending': '',
            'test': ['AT'],
            'version': ['AT+VERSION'],
            'name': ['AT+NAME{}'],
            'pin': ['AT+PSWD:"{}"', 'AT+PSWD{}', 'AT+PIN{}'],
            'baud': ['AT+UART={},0,0', 'AT+BAUD{}'],
            'reset': ['AT+ORGL']
        },
        'hc05_crlf': {  # HC-05 표준 (CR/LF 필요)
            'line_ending': '\r\n',
            'test': ['AT'],
            'version': ['AT+VERSION?', 'AT+VERSION'],
            'name': ['AT+NAME={}', 'AT+NAME?', 'AT+NAME{}'],
            'pin': ['AT+PSWD={}', 'AT+PSWD?', 'AT+PIN={}', 'AT+PSWD{}'],
            'baud': ['AT+UART={},0,0', 'AT+BAUD{}'],
            'reset': ['AT+ORGL', 'AT+RESET']
        },
        'mixed': {  # 혼합형 (모든 변형 시도)
            'line_ending': '',  # 먼저 없이 시도
            'test': ['AT'],
            'version': ['AT+VERSION', 'AT+VERSION?'],
            'name': ['AT+NAME{}', 'AT+NAME={}'],
            'pin': ['AT+PIN{}', 'AT+PSWD{}', 'AT+PSWD:"{}"', 'AT+PSWD={}', 'AT+PIN={}'],
            'baud': ['AT+BAUD{}', 'AT+UART={},0,0'],
            'reset': ['AT+ORGL', 'AT+RESET', 'AT+RST']
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
        self.line_ending = ''
        
        print("HC-06/HC-05 모듈 연결 시도 중...")
        
        # 자동으로 baudrate 탐지
        if not self.auto_detect_baudrate():
            raise Exception("모듈을 찾을 수 없습니다. 연결을 확인하세요.")
    
    def auto_detect_baudrate(self):
        """자동으로 올바른 baudrate와 명령어 형식을 탐지"""
        print(f"\n{'='*60}")
        print("자동 Baudrate 및 명령어 형식 탐지 시작...")
        print(f"{'='*60}")
        
        for baudrate in self.BAUDRATES:
            print(f"\n[시도] Baudrate: {baudrate}...")
            
            try:
                if self.serial and self.serial.is_open:
                    self.serial.close()
                    time.sleep(0.3)
                
                self.serial = serial.Serial(self.port, baudrate, timeout=self.timeout)
                time.sleep(0.5)  # 안정화 대기
                
                # 버퍼 클리어
                self.serial.reset_input_buffer()
                self.serial.reset_output_buffer()
                time.sleep(0.1)
                
                # 각 명령어 형식과 line ending 조합 시도
                for format_name, cmd_set in self.COMMAND_FORMATS.items():
                    # CR/LF 있는 버전과 없는 버전 모두 시도
                    line_endings = ['', '\r\n'] if cmd_set['line_ending'] == '' else ['\r\n', '']
                    
                    for line_ending in line_endings:
                        for test_cmd in cmd_set['test']:
                            full_cmd = test_cmd + line_ending
                            print(f"  [{format_name}] '{test_cmd}' + {repr(line_ending)}...", end=' ')
                            
                            response = self._send_raw_command(full_cmd, wait_time=0.5)
                            
                            if response and ('OK' in response or 'ok' in response.lower()):
                                self.current_baudrate = baudrate
                                self.command_format = format_name
                                self.line_ending = line_ending
                                print(f"✓ 성공!")
                                print(f"\n{'='*60}")
                                print(f"모듈 발견!")
                                print(f"  - Baudrate: {baudrate}")
                                print(f"  - 명령어 형식: {format_name}")
                                print(f"  - Line Ending: {repr(line_ending)}")
                                print(f"  - 응답: {response}")
                                print(f"{'='*60}\n")
                                return True
                            else:
                                print(f"응답: {repr(response)[:50]}")
                
                print("  → 이 baudrate에서는 응답 없음")
                
            except serial.SerialException as e:
                print(f"  ✗ 시리얼 오류: {e}")
                continue
            except Exception as e:
                print(f"  ✗ 예외: {e}")
                continue
        
        print("\n모든 baudrate에서 응답이 없습니다.")
        print("\n디버깅 정보:")
        print("  - LED가 깜빡이나요? (빠른 깜빡임 = 페어링 대기, 느린 깜빡임 = 페어링됨)")
        print("  - 배선: TX ↔ RX 교차 연결 확인")
        print("  - 전원: VCC에 3.3V~6V 공급 확인")
        print("  - 다른 프로그램이 포트를 사용중인지 확인")
        return False
    
    def _send_raw_command(self, command, wait_time=0.5):
        """원시 명령어 전송 (내부 사용)"""
        if not self.serial or not self.serial.is_open:
            return ""
        
        try:
            # 버퍼 클리어
            self.serial.reset_input_buffer()
            time.sleep(0.05)
            
            # 명령어 전송
            self.serial.write(command.encode('utf-8'))
            self.serial.flush()
            time.sleep(wait_time)
            
            # 응답 읽기
            response = ""
            if self.serial.in_waiting > 0:
                response = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
            
            return response.strip()
        except Exception as e:
            print(f"\n  [오류] {e}")
            return ""
    
    def send_command(self, cmd_type, *args, wait_time=1.0):
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
        
        # 먼저 감지된 형식으로 시도
        for cmd_template in commands:
            # 명령어 생성
            if '{}' in cmd_template:
                command = cmd_template.format(*args)
            else:
                command = cmd_template
            
            full_cmd = command + self.line_ending
            print(f"  [전송] {command} + {repr(self.line_ending)}...", end=' ')
            response = self._send_raw_command(full_cmd, wait_time)
            
            if response:
                print(f"✓ 응답: {response}")
                return True, response
            else:
                print("응답 없음")
        
        # 감지된 형식에서 실패하면 다른 형식도 시도
        print("  [대체 형식 시도 중...]")
        for format_name, format_cmds in self.COMMAND_FORMATS.items():
            if format_name == self.command_format:
                continue
            
            commands = format_cmds.get(cmd_type, [])
            alt_line_ending = format_cmds.get('line_ending', '')
            
            for cmd_template in commands:
                if '{}' in cmd_template:
                    command = cmd_template.format(*args)
                else:
                    command = cmd_template
                
                # 원래 line_ending과 대체 line_ending 모두 시도
                for le in [self.line_ending, alt_line_ending, '', '\r\n']:
                    if le in [self.line_ending, alt_line_ending]:  # 이미 시도한 조합은 제외
                        continue
                    
                    full_cmd = command + le
                    print(f"  [{format_name}] {command} + {repr(le)}...", end=' ')
                    response = self._send_raw_command(full_cmd, wait_time)
                    
                    if response:
                        print(f"✓ 응답: {response}")
                        # 성공한 line_ending 업데이트
                        self.line_ending = le
                        return True, response
                    else:
                        print("✗")
        
        return False, "모든 명령어 형식에서 응답 없음"
    
    def test_connection(self):
        """연결 테스트"""
        print("\n=== 연결 테스트 ===")
        success, response = self.send_command('test', wait_time=0.5)
        if success:
            print(f"✓ 연결 성공!")
            return True
        else:
            print(f"✗ 연결 실패")
            return False
    
    def get_version(self):
        """펌웨어 버전 확인"""
        print("\n=== 펌웨어 버전 확인 ===")
        success, response = self.send_command('version')
        if success:
            print(f"✓ 버전 정보: {response}")
        else:
            print(f"⚠ 버전 확인 실패 (일부 모듈은 지원하지 않음)")
        return response
    
    def set_name(self, name):
        """블루투스 이름 설정"""
        print(f"\n=== 블루투스 이름 설정: {name} ===")
        success, response = self.send_command('name', name, wait_time=1.5)
        if success:
            print(f"✓ 이름 설정 성공!")
            return True
        else:
            print(f"✗ 이름 설정 실패")
            return False
    
    def set_pin(self, pin):
        """PIN 코드 설정"""
        print(f"\n=== PIN 코드 설정: {pin} ===")
        success, response = self.send_command('pin', pin, wait_time=1.5)
        if success:
            print(f"✓ PIN 설정 성공!")
            return True
        else:
            print(f"✗ PIN 설정 실패")
            return False
    
    def set_baudrate(self, target_baudrate):
        """
        통신 속도 설정
        
        Args:
            target_baudrate: 목표 baudrate (예: 115200)
        """
        print(f"\n=== 통신 속도 설정: {target_baudrate} ===")
        
        # AT+UART 형식 먼저 시도
        success, response = self.send_command('baud', target_baudrate, wait_time=1.5)
        
        # 실패하면 AT+BAUD 코드 형식 시도
        if not success and target_baudrate in self.BAUD_CODES:
            baud_code = self.BAUD_CODES[target_baudrate]
            print(f"  [코드 방식으로 재시도: {baud_code}]")
            success, response = self.send_command('baud', baud_code, wait_time=1.5)
        
        if success:
            print(f"✓ 통신 속도 설정 성공!")
            print(f"⚠ 중요: 모듈 전원을 껐다 켜면 {target_baudrate}로 변경됩니다.")
            return True
        else:
            print(f"✗ 통신 속도 설정 실패")
            return False
    
    def reset_to_factory(self):
        """
        공장 초기화 (AT+ORGL)
        - Pin code: "1234" 또는 "0000"
        - Baudrate: 9600 (대부분)
        """
        print("\n=== 공장 초기화 시도 ===")
        print("⚠ 경고: 모든 설정이 초기화됩니다!")
        
        success, response = self.send_command('reset', wait_time=2.0)
        
        if success:
            print(f"✓ 초기화 성공!")
            print("모듈이 공장 출하 상태로 초기화되었습니다.")
            print("  - Pin code: '1234' 또는 '0000'")
            print("  - Baudrate: 9600 (대부분)")
            print("⚠ 모듈 전원을 껐다 켜세요.")
            time.sleep(2)
            return True
        else:
            print(f"✗ 초기화 실패 또는 지원하지 않는 명령어")
            return False
    
    def close(self):
        """시리얼 연결 종료"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("\n시리얼 연결이 종료되었습니다.")


def main():
    """HC-06 모듈 설정 예제"""
    
    # 시리얼 포트 설정
    PORT = 'COM7'  # 사용자 환경에 맞게 수정
    
    try:
        # HC-06 모듈 연결 (자동 baudrate 및 명령어 형식 탐지)
        hc06 = HC06Bluetooth(PORT)
        
        # 연결 테스트
        hc06.test_connection()
        
        # 펌웨어 버전 확인
        hc06.get_version()
        
        # === 옵션 1: 공장 초기화 (필요시 주석 해제) ===
        # print("\n" + "="*60)
        # user_input = input("공장 초기화를 수행하시겠습니까? (y/n): ")
        # if user_input.lower() == 'y':
        #     hc06.reset_to_factory()
        #     print("\n초기화 후 전원을 껐다 켜고 다시 실행하세요.")
        #     hc06.close()
        #     return
        
        # === 옵션 2: 사용자 정의 설정 ===
        # 블루투스 이름 변경
        hc06.set_name("MyHC06-kkb")
        
        # PIN 코드 변경
        hc06.set_pin("1234")
        
        # 통신 속도를 115200으로 변경
        hc06.set_baudrate(115200)
        
        print("\n" + "="*60)
        print("설정 완료!")
        print("="*60)
        print("⚠ 중요: 모듈의 전원을 껐다 켜야 새 설정이 적용됩니다.")
        print("전원 재시작 후 다음 설정으로 연결하세요:")
        print(f"  - Baudrate: 115200")
        print(f"  - 이름: MyHC06")
        print(f"  - PIN: 1234")
        print("="*60)
        
        # 연결 종료
        hc06.close()
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"오류 발생: {e}")
        print(f"{'='*60}")
        print("\n문제 해결 방법:")
        print("1. LED 상태 확인:")
        print("   - 빠른 깜빡임 (1초 2번): 페어링 대기 중 → AT 명령 가능 ✅")
        print("   - 느린 깜빡임 (2초 1번): 페어링됨 → AT 명령 불가 ❌")
        print("   - LED 꺼짐: 전원 문제 ⚠️")
        print("\n2. 페어링된 경우: 블루투스 연결 해제")
        print("\n3. 배선 확인:")
        print("   HC-06 TX → USB-Serial RX")
        print("   HC-06 RX → USB-Serial TX")
        print("   HC-06 VCC → 3.3V~6V (5V 권장)")
        print("   HC-06 GND → GND")
        print("\n4. 전원 전압 측정 (멀티미터로 VCC-GND 간 전압)")
        print("\n5. 다른 COM 포트 확인 (장치 관리자)")
        print("\n6. 공장 초기화 시도 (코드에서 주석 해제)")


if __name__ == "__main__":
    main()