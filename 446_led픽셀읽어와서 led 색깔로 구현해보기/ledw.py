import pyautogui
import serial
import time

ser = serial.Serial('COM3', 115200, timeout=1)

try:
    while True:
        x, y = pyautogui.position()
        pixel = pyautogui.pixel(x, y)
        
        # 아래 줄들이 'while True:'보다 한 단계(스페이스바 4번) 더 들어가 있어야 합니다.
        print(f"R:{pixel[0]}, G:{pixel[1]}, B:{pixel[2]}") 
        ser.write(bytes([pixel[0], pixel[1], pixel[2]]))
        
        time.sleep(0.1)
except KeyboardInterrupt:
    ser.close()