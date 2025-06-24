import paho.mqtt.client as mqtt
import pyvjoy
from pywinusb import hid
import time

# MQTT 설정
MQTT_BROKER = "3.36.131.224"
MQTT_TOPIC = "car/server"

# 상태 변수
engine_permission = False   # 서버에서 ENGINE_ON 허용받은 상태
engine_running = False      # 실제 시동이 켜진 상태
vjoy = pyvjoy.VJoyDevice(1)
OFFSET = 16200

# MQTT 콜백
def on_connect(client, userdata, flags, rc):
    print("[MQTT] 연결됨")
    client.subscribe(MQTT_TOPIC)

def on_message(client, userdata, msg):
    global engine_permission, engine_running
    payload = msg.payload.decode()
    print(f"[MQTT 수신] {payload}")

    if payload == "ENGINE_ON":
        engine_permission = True
        engine_running = False
        print("✅ 시동 허용 (버튼 입력 대기)")
    elif payload == "ENGINE_OFF":
        engine_permission = False
        engine_running = False
        vjoy.reset()
        print("⛔ 시동 차단")

# MQTT 연결
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)
client.loop_start()

# HID 장치 탐색
devices = hid.HidDeviceFilter().get_devices()
if not devices:
    raise RuntimeError("USB 장치를 찾을 수 없습니다.")
device = devices[3]
device.open()
print(f"[USB] 장치 연결됨: {device.vendor_name}")

# 입력 핸들러
def handle_input(data):
    global engine_permission, engine_running

    steer = data[1]
    brake = data[2]
    start_button = data[5]  # 버튼 값 (시동 버튼 가정)

    # 시동 버튼 눌림 처리
    if engine_permission and start_button == 1 and not engine_running:
        engine_running = True
        print("▶️ 조이스틱 버튼 입력으로 시동 켜짐")
        # 시동이 켜질 때 페달 초기화
        vjoy.data.wAxisY = 32767  # 엑셀 중립
        vjoy.data.wAxisZ = 32767      # 브레이크 해제
        vjoy.update()

    # 시동 꺼져 있으면 모든 입력 무시하고 중립
    if not engine_running:
        vjoy.data.wAxisX = 32767 - OFFSET
        vjoy.data.wAxisY = 32767
        vjoy.data.wAxisZ = 0
        vjoy.update()
        return

    # 핸들
    norm = (steer - 128) / 127.0
    norm = max(-1.0, min(1.0, norm))
    vjoy.data.wAxisX = int(32767 + norm * 32767 - OFFSET)
    print(f"🌀 핸들: {norm:.2f}")

    # 페달
    if brake > 128:
        bval = (brake - 128) / 127.0
        vjoy.data.wAxisZ = int(bval * 32767)
        vjoy.data.wAxisY = 32767
        print(f"🛑 브레이크: {bval:.2f}")
    elif brake < 128:
        aval = (128 - brake) / 127.0
        vjoy.data.wAxisY = int((1 - aval) * 32767)
        vjoy.data.wAxisZ = 0
        print(f"🚗 가속: {aval:.2f}")
    else:
        vjoy.data.wAxisY = 32767
        vjoy.data.wAxisZ = 0

    vjoy.update()

# 핸들러 등록
device.set_raw_data_handler(handle_input)

# 메인 루프
try:
    while True:
        time.sleep(0.05)
except KeyboardInterrupt:
    print("종료됨")
    device.close()
    client.loop_stop()
    client.disconnect()
