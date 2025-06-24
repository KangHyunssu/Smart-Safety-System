#include <WiFiS3.h>
#include <PubSubClient.h>

const int pressurePin = A0; // MPX5010DP
const int alcoholPin = A1;  // MQ-3

const float PRESSURE_THRESHOLD = 5.0; // kPa
const int ALCOHOL_THRESHOLD = 300;   // 실험에 따라 조정

// WiFi & MQTT 설정
const char* ssid = "HSKANG";
const char* password = "58790347";
const char* mqtt_server = "3.36.131.224";
const char* mqtt_topic = "breathalyzer/status";

WiFiClient wifiClient;
PubSubClient client(wifiClient);

// 측정 일시 중지 관련 변수
bool measurementPaused = false;
bool pauseMessageShown = false; // 일시정지 메시지를 한 번만 출력하기 위한 플래그
unsigned long pauseStartTime = 0;
const unsigned long pauseDuration = 20000; // 20초

void setup_wifi() {
  Serial.print("WiFi 연결 중...");
  while (WiFi.begin(ssid, password) != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi 연결 완료!");
  Serial.print("IP 주소: ");
  Serial.println(WiFi.localIP());
}

void reconnect_mqtt() {
  while (!client.connected()) {
    Serial.print("MQTT 재연결 중...");
    if (client.connect("arduinoClient")) {
      Serial.println("MQTT 연결 성공!");
    } else {
      Serial.print("실패, 재시도 코드: ");
      Serial.print(client.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(9600);
  while (!Serial);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
}

void loop() {
  if (!client.connected()) {
    reconnect_mqtt();
  }
  client.loop();

  if (measurementPaused) {
    if (!pauseMessageShown) {
      Serial.println("측정 일시 정지됨 (20초)");
      pauseMessageShown = true;
    }
    if (millis() - pauseStartTime >= pauseDuration) {
      measurementPaused = false;
      pauseMessageShown = false;
      Serial.println("측정 재개됨");
    }
    delay(1000);
    return;
  }

  // 압력 읽기
  int rawPressure = analogRead(pressurePin);
  float voltage = rawPressure * (5.0 / 1023.0);
  float pressure_kPa = (voltage - 0.2) * (10.0 / 4.7);
  if (pressure_kPa < 0) pressure_kPa = 0;

  Serial.print("압력: ");
  Serial.print(pressure_kPa);
  Serial.print(" kPa");

  if (pressure_kPa >= PRESSURE_THRESHOLD) {
    Serial.print(" ➜ 숨 감지됨. 측정 중... ");

    // 알코올 측정
    int alcoholValue = analogRead(alcoholPin);
    Serial.print("알코올 값: ");
    Serial.print(alcoholValue);

    // 판정
    int status = (alcoholValue < ALCOHOL_THRESHOLD) ? 1 : 0;
    Serial.print(" | 판정: ");
    Serial.println(status == 1 ? "정상" : "음주");

    // MQTT 전송
    char msg[2];
    sprintf(msg, "%d", status);
    client.publish(mqtt_topic, msg);

    // 측정 일시 중지 시작
    measurementPaused = true;
    pauseMessageShown = false;
    pauseStartTime = millis();

  } else {
    Serial.println(" ➜ 숨 감지되지 않음.");
  }

  delay(1000); // 1초 간격
}
