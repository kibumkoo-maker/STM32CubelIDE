import serial
import time

class BT06Bluetooth:
    """BT06/BOLUTEK 펌웨어 전용 블루투스 모듈 설정 클래스"""
    
    # 지원하는 baudrate 목록
    BAUDRATES = [9600, 38400, 19200, 57600, 115200, 4800, 2400, 1200]
    
    # BOLUTEK Baudrate 코드 매핑
    BAUD_CODES = {
        1200: '1', 2400: '2', 4800: '3', 9600: '4',
        19200: '5', 38400: '6', 57600: '7', 115200: '8'
    }
    
    def __init__(self, port, baudrate=9600, timeout=1):
        """
        BT06 모듈 초기화
        
        Args:
            port: 시리얼 포트 (예: 'COM10')
            baudrate: 통신 속도 (기본 9600)
            timeout: 타임아웃 (초)
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = None
        
        print(f"BT06 모듈 연결 중... (포트: {port}, 속도: {baudrate})")
        
        try:
            self.serial = serial.Serial(port, baudrate, timeout=timeout)
            time.sleep(1.0)  # 연결 안정화
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            print("✓ 시리얼 포트 열림")
        except Exception as e:
            raise Exception(f"시리얼 포트 열기 실패: {e}")
    
    def send_command(self, command, wait_time=1.0, use_crlf=True):
        """
        AT 명령어 전송
        
        Args:
            command: AT 명령어 (예: 'AT', 'AT+VERSION?')
            wait_time: 응답 대기 시간 (초)
            use_crlf: CR/LF 추가 여부
        
        Returns:
            응답 문자열
        """
        if not self.serial or not self.serial.is_open:
            return ""
        
        # 버퍼 완전 클리어
        self.serial.reset_input_buffer()
        self.serial.reset_output_buffer()
        time.sleep(0.1)
        
        # 명령어 전송
        if use_crlf:
            full_cmd = command + '\r\n'
        else:
            full_cmd = command
        
        self.serial.write(full_cmd.encode('utf-8'))
        self.serial.flush()
        
        # 응답 대기
        time.sleep(wait_time)
        
        # 응답 읽기
        response = ""
        if self.serial.in_waiting > 0:
            response = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
        
        return response.strip()
    
    def test_connection(self):
        """연결 테스트"""
        print("\n" + "="*50)
        print("연결 테스트")
        print("="*50)
        
        response = self.send_command('AT', wait_time=0.5)
        print(f"  AT → {repr(response)}")
        
        if 'OK' in response:
            print("✓ 연결 성공!")
            return True
        else:
            print("✗ 연결 실패")
            return False
    
    def get_version(self):
        """버전 확인"""
        print("\n버전 확인...")
        response = self.send_command('AT+VERSION?', wait_time=0.5)
        print(f"  → {response}")
        return response
    
    def interactive_test(self):
        """인터랙티브 AT 명령어 테스트"""
        print("\n" + "="*50)
        print("인터랙티브 AT 명령어 테스트")
        print("="*50)
        print("명령어를 입력하세요. 종료: 'quit' 또는 'exit'")
        print("예: AT, AT+VERSION?, AT+NAME=Test, AT+PIN=1234, AT+BAUD8")
        print("="*50)
        
        while True:
            try:
                cmd = input("\n명령어> ").strip()
                
                if cmd.lower() in ['quit', 'exit', 'q']:
                    print("종료합니다.")
                    break
                
                if not cmd:
                    continue
                
                # CR/LF 있는 버전
                print(f"\n[1] '{cmd}' + CR/LF:")
                response = self.send_command(cmd, wait_time=1.0, use_crlf=True)
                print(f"    응답: {repr(response)}")
                
                # CR/LF 없는 버전도 테스트
                time.sleep(0.5)
                print(f"[2] '{cmd}' (no CR/LF):")
                response = self.send_command(cmd, wait_time=1.0, use_crlf=False)
                print(f"    응답: {repr(response)}")
                
            except KeyboardInterrupt:
                print("\n종료합니다.")
                break
    
    def configure_module(self, name=None, pin=None, baudrate=None):
        """
        모듈 설정 (명령어 사이에 충분한 딜레이)
        
        Args:
            name: 블루투스 이름 (예: "MyBT06")
            pin: PIN 코드 (예: "1234")
            baudrate: 통신 속도 (예: 115200)
        """
        print("\n" + "="*50)
        print("모듈 설정 시작")
        print("="*50)
        
        # 연결 테스트
        if not self.test_connection():
            print("연결 실패! 설정을 중단합니다.")
            return False
        
        time.sleep(1.0)  # 명령어 간 딜레이
        
        # 버전 확인
        self.get_version()
        time.sleep(1.0)
        
        results = {}
        
        # 이름 설정
        if name:
            print(f"\n=== 이름 설정: {name} ===")
            time.sleep(0.5)
            
            # 여러 형식 시도
            formats = [
                f'AT+NAME={name}',    # 표준 형식
                f'AT+NAME{name}',     # HC-06 형식
            ]
            
            for fmt in formats:
                print(f"  시도: {fmt}")
                response = self.send_command(fmt, wait_time=1.5)
                print(f"  응답: {repr(response)}")
                
                if response and 'OK' in response:
                    print(f"  ✓ 이름 설정 성공!")
                    results['name'] = True
                    break
                elif response and 'ERROR' not in response and response:
                    print(f"  ✓ 이름 설정 성공 (응답: {response})")
                    results['name'] = True
                    break
                
                time.sleep(0.5)
            else:
                print(f"  ✗ 이름 설정 실패")
                results['name'] = False
            
            time.sleep(1.0)
        
        # PIN 설정
        if pin:
            print(f"\n=== PIN 설정: {pin} ===")
            time.sleep(0.5)
            
            formats = [
                f'AT+PIN={pin}',      # BOLUTEK 형식
                f'AT+PIN{pin}',       # HC-06 형식
                f'AT+PSWD={pin}',     # HC-05 형식
                f'AT+PSWD{pin}',
            ]
            
            for fmt in formats:
                print(f"  시도: {fmt}")
                response = self.send_command(fmt, wait_time=1.5)
                print(f"  응답: {repr(response)}")
                
                if response and 'OK' in response:
                    print(f"  ✓ PIN 설정 성공!")
                    results['pin'] = True
                    break
                elif response and 'ERROR' not in response and response:
                    print(f"  ✓ PIN 설정 성공 (응답: {response})")
                    results['pin'] = True
                    break
                
                time.sleep(0.5)
            else:
                print(f"  ✗ PIN 설정 실패")
                results['pin'] = False
            
            time.sleep(1.0)
        
        # Baudrate 설정
        if baudrate:
            print(f"\n=== 통신 속도 설정: {baudrate} ===")
            time.sleep(0.5)
            
            if baudrate not in self.BAUD_CODES:
                print(f"  ✗ 지원하지 않는 속도: {baudrate}")
                print(f"  지원 속도: {list(self.BAUD_CODES.keys())}")
                results['baudrate'] = False
            else:
                baud_code = self.BAUD_CODES[baudrate]
                
                formats = [
                    f'AT+BAUD{baud_code}',        # BOLUTEK/HC-06 형식 (AT+BAUD8)
                    f'AT+UART={baudrate},0,0',    # HC-05 형식
                    f'AT+BAUD={baud_code}',       # 변형
                ]
                
                for fmt in formats:
                    print(f"  시도: {fmt}")
                    response = self.send_command(fmt, wait_time=1.5)
                    print(f"  응답: {repr(response)}")
                    
                    if response and 'OK' in response:
                        print(f"  ✓ 통신 속도 설정 성공!")
                        results['baudrate'] = True
                        break
                    elif response and 'ERROR' not in response and response:
                        # BOLUTEK은 +BAUD:115200 같은 응답을 줄 수 있음
                        print(f"  ✓ 통신 속도 설정 성공 (응답: {response})")
                        results['baudrate'] = True
                        break
                    
                    time.sleep(0.5)
                else:
                    print(f"  ✗ 통신 속도 설정 실패")
                    results['baudrate'] = False
        
        # 결과 요약
        print("\n" + "="*50)
        print("설정 결과 요약")
        print("="*50)
        for key, value in results.items():
            status = "✓ 성공" if value else "✗ 실패"
            print(f"  {key}: {status}")
        
        if all(results.values()):
            print("\n⚠ 중요: 전원을 껐다 켜면 새 설정이 적용됩니다!")
        
        return results
    
    def scan_all_commands(self):
        """BOLUTEK 지원 명령어 스캔"""
        print("\n" + "="*50)
        print("BOLUTEK 명령어 스캔")
        print("="*50)
        
        commands = [
            'AT',
            'AT+VERSION',
            'AT+VERSION?',
            'AT+NAME?',
            'AT+PIN?',
            'AT+PSWD?',
            'AT+UART?',
            'AT+BAUD?',
            'AT+ADDR?',
            'AT+ROLE?',
            'AT+STATE?',
            'AT+HELP',
            'AT+LIST',
        ]
        
        print("지원 명령어 확인 중...\n")
        
        for cmd in commands:
            response = self.send_command(cmd, wait_time=0.8)
            if response:
                status = "✓" if 'ERROR' not in response else "✗"
                print(f"  {cmd:15} → {status} {response[:50]}")
            else:
                print(f"  {cmd:15} → 응답 없음")
            time.sleep(0.3)
    
    def close(self):
        """연결 종료"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("\n시리얼 연결 종료")


def main():
    PORT = 'COM10'  # 사용자 환경에 맞게 수정
    BAUDRATE = 9600
    
    print("="*60)
    print("BT06/BOLUTEK 블루투스 모듈 설정 프로그램")
    print("="*60)
    
    try:
        bt = BT06Bluetooth(PORT, BAUDRATE)
        
        while True:
            print("\n" + "-"*40)
            print("메뉴 선택:")
            print("  1. 연결 테스트")
            print("  2. 지원 명령어 스캔")
            print("  3. 인터랙티브 모드 (직접 명령어 입력)")
            print("  4. 모듈 설정 (이름, PIN, 속도)")
            print("  5. 빠른 설정 (MyHC06-020, 1234, 115200)")
            print("  0. 종료")
            print("-"*40)
            
            choice = input("선택> ").strip()
            
            if choice == '1':
                bt.test_connection()
                bt.get_version()
                
            elif choice == '2':
                bt.scan_all_commands()
                
            elif choice == '3':
                bt.interactive_test()
                
            elif choice == '4':
                name = input("이름 (Enter=건너뛰기): ").strip() or None
                pin = input("PIN (Enter=건너뛰기): ").strip() or None
                baud_str = input("속도 (Enter=건너뛰기): ").strip()
                baud = int(baud_str) if baud_str else None
                
                bt.configure_module(name=name, pin=pin, baudrate=baud)
                
            elif choice == '5':
                bt.configure_module(
                    name="MyHC06-020",
                    pin="1234",
                    baudrate=115200
                )
                
            elif choice == '0':
                break
            else:
                print("잘못된 선택입니다.")
        
        bt.close()
        
    except Exception as e:
        print(f"\n오류: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()