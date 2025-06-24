import tkinter as tk
import paho.mqtt.client as mqtt
import RPi.GPIO as GPIO
import time
import threading
import json

# GPIO 설정
LED_PIN = 14
BUZZER_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# MQTT 설정
MQTT_BROKER = "54.180.229.202"
MQTT_PORT = 1883

# 토픽 정의
RPI_ENGINE = "pi/engine"
RPI_ALERT = "pi/alert"

# 전역 변수
engine_status = "OFF"
drowsy_count = 0
alert_thread = None
alert_running = False
is_driving = False

# GUI 초기화
root = tk.Tk()
root.title("차량 제어 시스템")
root.configure(bg='black')

# 전체 화면 설정 (라즈베리파이)
root.attributes('-fullscreen', True)

# ESC 키로 전체화면 종료
root.bind('<Escape>', lambda e: root.attributes('-fullscreen', False))

# 메인 라벨 (LCD 역할)
main_label = tk.Label(root, text="CAR", font=("Arial", 80), fg="white", bg="black")
main_label.pack(expand=True)

# LED와 부저 제어
def alert_control(pattern, continuous=False):
    """LED와 부저 패턴 제어"""
    global alert_running, drowsy_count
    alert_running = True
    
    if pattern == "alcohol":
        # 음주 감지 패턴: 0.5초 간격, 5초간
        for i in range(10):
            if not alert_running:
                break
            GPIO.output(LED_PIN, GPIO.HIGH)
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            time.sleep(0.5)
            GPIO.output(LED_PIN, GPIO.LOW)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
            time.sleep(0.5)
    
    elif pattern == "drowsy" and continuous:
        # 졸음 감지 패턴: 속도 증가
        while alert_running:
            # 졸음 횟수에 따라 간격 감소 (0.5초 → 0.1초)
            interval = max(0.1, 0.5 - (drowsy_count - 1) * 0.1)
            GPIO.output(LED_PIN, GPIO.HIGH)
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            time.sleep(interval)
            GPIO.output(LED_PIN, GPIO.LOW)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
            time.sleep(interval)
    
    # 알림 종료
    GPIO.output(LED_PIN, GPIO.LOW)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

# 알림 중지
def stop_alert():
    """진행 중인 알림 중지"""
    global alert_running, alert_thread
    alert_running = False
    if alert_thread and alert_thread.is_alive():
        alert_thread.join(timeout=1)
    GPIO.output(LED_PIN, GPIO.LOW)
    GPIO.output(BUZZER_PIN, GPIO.LOW)

# GUI 텍스트 업데이트
def update_display(text, bg_color="black", duration=0):
    """화면 텍스트 업데이트"""
    main_label.config(text=text, bg=bg_color)
    root.configure(bg=bg_color)
    
    if duration > 0:
        # duration 후에 실행할 함수 예약
        root.after(duration * 1000, lambda: None)

# 초기 화면으로 돌아가기
def show_car_screen():
    """CAR 초기 화면 표시"""
    update_display("CAR", "black")

# MQTT 콜백 함수
def on_connect(client, userdata, flags, rc):
    """MQTT 연결 콜백"""
    if rc == 0:
        print("✅ MQTT 브로커 연결 성공")
        client.subscribe(RPI_ENGINE)
        client.subscribe(RPI_ALERT)
        print(f"📡 구독 토픽: {RPI_ENGINE}, {RPI_ALERT}")
    else:
        print(f"❌ MQTT 연결 실패: {rc}")

def on_message(client, userdata, msg):
    """MQTT 메시지 수신 콜백"""
    global engine_status, drowsy_count, alert_thread, is_driving
    
    topic = msg.topic
    payload = msg.payload.decode()
    print(f"[수신] {topic}: {payload}")
    
    # 1. 시동 제어 메시지
    if topic == RPI_ENGINE:
        if payload == "ENGINE_OFF":
            # 음주 감지 - 시동 OFF
            engine_status = "OFF"
            is_driving = False
            drowsy_count = 0
            
            # 기존 알림 중지
            stop_alert()
            
            # 화면 표시
            update_display("음주가 감지되었음\n시동이 OFF됩니다", "red")
            
            # LED와 부저 알림 (5초)
            alert_thread = threading.Thread(target=alert_control, args=("alcohol",))
            alert_thread.start()
            
            # 3초 후 초기 화면으로
            root.after(3000, show_car_screen)
            
        elif payload == "ENGINE_ON":
            # 음주 정상 - 시동 ON
            engine_status = "ON"
            drowsy_count = 0
            
            # 순차적 메시지 표시
            def show_sequence():
                update_display("음주측정 정상\n시동이 ON됩니다", "green")
                root.after(2000, lambda: update_display("얼굴 인증을\n해주세요", "blue"))
                root.after(4000, lambda: start_driving())
            
            def start_driving():
                global is_driving
                is_driving = True
                update_display("정상 운행", "darkgreen")
            
            show_sequence()
    
    # 2. 경고 메시지
    elif topic == RPI_ALERT:
        # JSON 메시지 처리 (긴급/고장 신고)
        try:
            data = json.loads(payload)
            if data.get("type") == "emergency":
                update_display("🚨 긴급신고 수신", "red")
                root.after(3000, lambda: update_display("정상 운행", "darkgreen") if is_driving else show_car_screen())
                return
            elif data.get("type") == "malfunction":
                update_display("⚠️ 고장신고 수신", "orange")
                root.after(3000, lambda: update_display("정상 운행", "darkgreen") if is_driving else show_car_screen())
                return
        except json.JSONDecodeError:
            pass  # JSON이 아닌 경우 문자열로 처리
        
        # 문자열 메시지 처리
        if payload == "DRIVER_MISMATCH" or payload == "MISMATCH":
            # 운전자 불일치
            engine_status = "OFF"
            is_driving = False
            
            # 기존 알림 중지
            stop_alert()
            
            # 화면 표시
            update_display("운전자 불일치\n시동 OFF", "purple")
            
            # LED와 부저 알림 (5초)
            alert_thread = threading.Thread(target=alert_control, args=("alcohol",))  # 같은 패턴 사용
            alert_thread.start()
            
            # 3초 후 초기 화면으로
            root.after(3000, show_car_screen)
            
        elif payload == "DROWSY" and is_driving:
            # 졸음 감지
            drowsy_count += 1
            
            # 기존 알림 중지
            stop_alert()
            
            # 화면 표시
            update_display("졸음이 감지되었음", "orange")
            
            # LED와 부저 알림 (계속)
            alert_thread = threading.Thread(target=alert_control, args=("drowsy", True))
            alert_thread.start()
            
        elif payload == "NORMAL" and is_driving:
            # 정상 상태로 복귀
            if drowsy_count > 0:
                drowsy_count = 0
                
                # 알림 중지
                stop_alert()
                
                # 정상 복귀 메시지
                update_display("정상 상태로\n돌아옴", "blue")
                root.after(2000, lambda: update_display("정상 운행", "darkgreen"))
            else:
                # 이미 정상 상태인 경우
                update_display("정상 운행", "darkgreen")

# MQTT 클라이언트 설정
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# 프로그램 종료 처리
def on_closing():
    """프로그램 종료 시 정리"""
    print("\n프로그램 종료 중...")
    stop_alert()
    GPIO.cleanup()
    client.loop_stop()
    client.disconnect()
    root.destroy()

# 윈도우 닫기 이벤트
root.protocol("WM_DELETE_WINDOW", on_closing)

# 메인 실행
if __name__ == "__main__":
    print("🚗 라즈베리파이 GUI 차량 제어 시스템 시작")
    print(f"📡 MQTT 브로커: {MQTT_BROKER}")
    print(f"💡 LED: GPIO {LED_PIN}")
    print(f"🔊 부저: GPIO {BUZZER_PIN}")
    print("📺 디스플레이: GUI 모드\n")
    print("ESC 키: 전체화면 종료")
    
    try:
        # MQTT 연결
        print("🔄 MQTT 브로커 연결 중...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        # GUI 실행
        root.mainloop()
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        on_closing()