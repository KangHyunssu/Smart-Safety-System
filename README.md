# 🚗 스마트 차량 운전자 인증 및 졸음/음주 방지 시스템

## 🔍 프로젝트 소개
본 프로젝트는 운전자의 상태를 실시간으로 감지하고, 위험 상황 발생 시 시동을 차단하거나 경고를 제공하는
지능형 운전자 보호 시스템입니다.

Jetson Nano, Arduino, Raspberry Pi, Windows 시뮬레이터, AWS EC2 등 다양한 장치를 연동하여,
MQTT 기반의 통합 제어 시스템으로 동작합니다.


### 🧠 핵심 기능 요약

- 🧪 음주 측정
MQ-3 센서와 압력 센서를 이용해 실제 숨을 불어넣은 경우에만 측정 가능하며,
알코올이 감지되면 즉시 시동 차단

- 👤 얼굴 인증
Jetson Nano에서 딥러닝 기반 얼굴 인식을 수행하여, 운전자 본인이 아닐 경우 시동 차단

- 😴 졸음 감지
눈 감김(2초), 고개 기울임(3초) 등 졸음 상태를 감지하면
LCD 문구, LED, 부저로 경고 발생

- 🖥️ 라즈베리파이 LCD 시스템
실시간 상태(음주, 졸음, 인증 실패 등)를 표시하고
시각/청각 경고를 함께 출력

- 🕹️ Windows 조향 시뮬레이터
USB 페달/핸들을 통해 시동·주행을 pyvjoy로 구현

- ☁️ AWS EC2 서버
모든 장치 간 MQTT 메시지를 중계하고 중앙 제어 허브 역할 수행

---


## 🧰 사용 기술

| 기능 모듈              | 기술 스택 및 라이브러리                                                                   |
| ------------------ | ------------------------------------------------------------------------------- |
| **얼굴 인식 / 졸음 감지**  | `Jetson Nano`, `OpenCV`, `Dlib`, `적외선 카메라 (IR)`                                 |
| **음주 측정**          | `Arduino Uno`, `MQ-3 알코올 센서`, `압력 센서`, `C++`                                    |
| **클라우드 서버**        | `AWS EC2`, `Mosquitto MQTT`, `Python`, `paho-mqtt`                              |
| **차량 제어 시뮬레이션**    | `Windows`, `pyvjoy`, `pywinusb`, `USB Steering Wheel`, `Euro Truck Simulator 2` |
| **운전자 LCD 경고 시스템** | `Raspberry Pi`, `Tkinter GUI`, `GPIO`, `Buzzer`, `LED`                          |
| **관리자 대시보드**       | `Flask`, `HTML5/CSS3`, `JavaScript`, `Chart.js`                                 |


---


## 🧠 핵심 기술

- 딥러닝 기반 얼굴 랜드마크 인식
Dlib의 68-point landmark 모델을 활용해 눈, 얼굴 방향을 실시간 분석하며, 졸음 운전 감지를 정밀하게 수행합니다.

- 적외선 카메라(IR)
야간 환경에서도 운전자의 눈 감김과 고개 기울임을 안정적으로 감지하기 위해 사용됩니다.

- MQTT 프로토콜 통신
경량 메시지 기반 프로토콜을 활용해 각 장치 간 빠르고 안정적인 통신을 실현하였습니다. (음주 결과, 졸음 여부, 인증 상태 등)

- pyvjoy / pywinusb
실제 USB 핸들과 페달 장치를 읽고, 이를 vJoy 가상 조이스틱으로 전달하여 게임과 시뮬레이션에 연동됩니다.

- 실시간 GUI 경고 시스템
라즈베리파이 LCD를 기반으로 한 Tkinter GUI와 GPIO 모듈을 사용해 운전자에게 시각/청각 경고를 실시간으로 제공합니다.

- 음주 대리 방지 로직
음주 측정 이후, Jetson Nano에서 운전자의 얼굴을 검증하여 다른 사람이 대신 음주 측정을 하는 행위(대리)를 방지합니다.


## 📦 프로젝트 구조

```plaintext
SmartCarSystem/
├── aws_server/              # MQTT 브로커 및 중계 로직
│   └── ec2_main.py
├── jetson_nano/             # 얼굴 인식 및 졸음 감지
│   └── face_drowsiness.py
├── arduino/                 # 음주 측정기 코드
│   └── breath_sensor.ino
├── raspberry_pi_lcd/        # LCD 경고 시스템
│   └── lcd_monitor.py
├── windows_simulator/       # USB 조향장치 연동
│   └── steering_control.py
├── admin_dashboard/         # 관리자 페이지
│   ├── app.py
│   └── templates/
└── README.md
```


## ⚙️ 시스템 흐름 요약

1. **음주 측정** (Arduino)
   - MQ-3 센서를 통해 측정된 값이 정상일 경우 → 시동 허용
   - 이상값이면 바로 시동 차단

2. **얼굴 인식 및 졸음 감지** (Jetson Nano)
   - 얼굴이 등록되지 않았거나 눈 감김/고개 기울임 지속 → 경고 전송

3. **AWS EC2 서버** (중앙 허브)
   - 모든 MQTT 메시지 중계 및 제어 로직 담당

4. **LCD 시스템** (Raspberry Pi)
   - “음주 감지”, “운전자 불일치”, “졸음 감지” 등의 상태를 실시간 표시
   - 부저 및 LED로 시각/청각 경고 동시 제공

5. **조향 장치 시뮬레이터** (USB 게임용 스티어링휠)
   - USB 페달 및 핸들 조작 → pyvjoy로 가상 조이스틱 동작

---

## 🖥️ 설치 방법

**클론 받기**

bash
git clone https://github.com/KangHyunssu/SmartCarSystem.git

cd SmartCarSystem

pip install -r requirements.txt

sudo systemctl start mosquitto
python ec2_main.py

## 🧪 테스트 방법

Arduino에서 "1" 또는 "0"을 시리얼 입력으로 보내 음주 상태 시뮬레이션

Jetson Nano의 카메라 앞에 등록된 얼굴이 아닌 사람을 배치하거나, 눈 감기 유지

Raspberry Pi LCD 화면에서 상태 확인

Windows 시뮬레이터에서 조향 장치가 정상 작동하는지 확인


##💡 향후 개선 방향
YOLO 기반 객체 인식 추가로 더 정밀한 졸음 감지

관리자 대시보드에서 위치 추적 및 긴급 출동 요청 기능 추가

차량 내 CAN 통신 연동으로 실차 제어 연동


## 📸 시연 이미지




