import paho.mqtt.client as mqtt
import json

# 브로커 주소
MQTT_BROKER = "your_mqtt_broker_ip"

# 토픽 정의
BREATHALYZER_TOPIC = "breathalyzer/status"   # 아두이노에서 보내는 토픽
REQUEST_TOPIC      = "face/request"          # Jetson 얼굴인증 요청
RESULT_TOPIC       = "face/result"           # Jetson 인증 결과
DROWSINESS_TOPIC   = "driver/drowsiness"     # Jetson 실시간 졸음 감지 결과 (추가)
CAR_TOPIC          = "car/server"            # 조향장치
RPI_ENGINE         = "pi/engine"             # 라즈베리파이 시동 제어
RPI_ALERT          = "pi/alert"              # 졸음 경고용 (true/false 모두 전송)

client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    print("✅ EC2 MQTT 연결 완료, 토픽 구독 시작")
    client.subscribe(BREATHALYZER_TOPIC)
    client.subscribe(RESULT_TOPIC)
    client.subscribe(DROWSINESS_TOPIC)  # 실시간 졸음 감지 토픽 구독 추가

def on_message(client, userdata, msg):
    payload = msg.payload.decode()
    topic   = msg.topic
    
    # 1) 아두이노 음주측정기 결과 처리
    if topic == BREATHALYZER_TOPIC:
        print(f"[음주측정기 결과 수신] {payload}")
        if payload == "1":  # 정상
            client.publish(CAR_TOPIC, "ENGINE_ON")
            client.publish(RPI_ENGINE, "ENGINE_ON")
            client.publish(REQUEST_TOPIC, "VERIFY_FACE")
            print("[전송] ENGINE_ON → 조향장치, 라즈베리파이")
            print("[전송] 얼굴 인증 요청 → Jetson")
        elif payload == "0":  # 음주 감지
            client.publish(CAR_TOPIC, "ENGINE_OFF")
            client.publish(RPI_ENGINE, "ENGINE_OFF")
            print("[전송] ENGINE_OFF → 조향장치, 라즈베리파이 (음주 감지)")
    
    # 2) Jetson 얼굴 인증 및 졸음 감지
    elif topic == RESULT_TOPIC:
        print(f"[Jetson 결과 수신] {payload}")
        try:
            data = json.loads(payload)
            face_match = data.get("face_match")
            drowsy     = data.get("drowsiness_detected", False)
            
            # 얼굴 인증 실패 시 시동 차단
            if face_match == "MISMATCH":
                client.publish(CAR_TOPIC, "ENGINE_OFF")
                client.publish(RPI_ALERT, "MISMATCH")
                print("[전송] ENGINE_OFF → 조향장치")
                print("[전송] 운전자 불일치 알림 → 라즈베리파이")
            
            # 졸음 여부 전송 (true/false 모두 라즈베리파이에 전달)
            if drowsy is True:
                client.publish(RPI_ALERT, "DROWSY")
                print("[전송] 졸음 상태 → 라즈베리파이 (DROWSY)")
            else:
                client.publish(RPI_ALERT, "NORMAL")
                print("[전송] 졸음 없음 → 라즈베리파이 (NORMAL)")
        except json.JSONDecodeError:
            print("⚠️ JSON 파싱 오류 - Jetson 데이터 확인 필요")
    
    # 3) Jetson 실시간 졸음 감지 결과 처리 (새로 추가)
    elif topic == DROWSINESS_TOPIC:
        print(f"[실시간 졸음 감지 수신] {payload}")
        try:
            data = json.loads(payload)
            drowsy = data.get("drowsiness_detected", False)
            
            # 실시간 졸음 상태를 라즈베리파이에 즉시 전송
            if drowsy is True:
                client.publish(RPI_ALERT, "DROWSY")
                print("[전송] 실시간 졸음 감지 → 라즈베리파이 (DROWSY)")
            else:
                client.publish(RPI_ALERT, "NORMAL")
                print("[전송] 실시간 졸음 해제 → 라즈베리파이 (NORMAL)")
            
            # 🎯 관리자 페이지로 실시간 졸음 감지 결과 전달 (추가된 부분)
            admin_data = {
                "face_match": "CONTINUE",  # 얼굴 인증은 계속 유지
                "drowsiness_detected": drowsy,
                "driver_name": "운전자",
                "timestamp": payload  # 원본 데이터도 포함
            }
            client.publish(RESULT_TOPIC, json.dumps(admin_data))
            print(f"[전송] 실시간 졸음 상태 → 관리자 페이지 (drowsy: {drowsy})")
            
        except json.JSONDecodeError:
            print("⚠️ 실시간 졸음 감지 JSON 파싱 오류")

# 연결 및 시작
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.loop_forever()