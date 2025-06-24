# 🚗 스마트 차량 운전자 인증 및 졸음/음주 방지 시스템

## 🔍 프로젝트 소개

본 프로젝트는 운전자의 안전을 보장하기 위한 **지능형 운전자 상태 인식 시스템**입니다.  
Jetson Nano의 얼굴 인식 및 졸음 감지 기능, 아두이노 기반 음주 측정,  
Windows 기반 스티어링 제어 시뮬레이터, 라즈베리파이 LCD 경고 시스템,  
그리고 AWS EC2 서버를 통한 **MQTT 기반 실시간 제어**가 통합된 종합적인 솔루션입니다.

> 🧠 핵심 기능:  
> - 운전자 얼굴 인증 실패 시 시동 차단  
> - 졸음 상태 감지 시 LED/부저 경고 및 LCD 안내  
> - 음주 상태 감지 시 시동 차단  
> - 관리자 페이지를 통한 상태 모니터링 및 제어

---

## 🧰 사용 기술

| 모듈          | 기술 스택 및 라이브러리 |
|---------------|--------------------------|
| 얼굴 인식/졸음 감지 | `Jetson Nano`, `OpenCV`, `Dlib`, `IR Camera` |
| 음주 측정        | `Arduino Uno`, `MQ-3 알콜센서` |
| 클라우드 서버     | `AWS EC2`, `Mosquitto MQTT`, `Python` |
| 차량 제어 시뮬레이션 | `Windows`, `pyvjoy`, `pywinusb`, `Euro Truck Simulator` |
| 운전자 LCD 표시 | `Raspberry Pi`, `Tkinter`, `GPIO`, `Buzzer`, `LED` |
| 관리자 페이지     | `Flask`, `HTML/CSS`, `JavaScript` |

---

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

5. **조향 장치 시뮬레이터** (Windows PC)
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




