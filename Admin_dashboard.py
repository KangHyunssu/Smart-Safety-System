<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>스마트카 관리자 대시보드</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/paho-mqtt/1.0.1/mqttws31.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .header h1 {
            color: #2c3e50;
            font-size: 2.5em;
            font-weight: 700;
            text-align: center;
            margin-bottom: 10px;
        }

        .connection-status {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-top: 15px;
        }

        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #e74c3c;
            animation: pulse 2s infinite;
        }

        .status-indicator.connected {
            background: #27ae60;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            margin-bottom: 25px;
        }

        .card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        .card h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }

        .manual-controls {
            grid-column: 1 / -1;
        }

        .control-buttons {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            justify-content: center;
        }

        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 25px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .btn-success {
            background: linear-gradient(45deg, #27ae60, #2ecc71);
            color: white;
        }

        .btn-danger {
            background: linear-gradient(45deg, #e74c3c, #c0392b);
            color: white;
        }

        .btn-warning {
            background: linear-gradient(45deg, #f39c12, #e67e22);
            color: white;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
        }

        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .status-item {
            background: rgba(52, 152, 219, 0.1);
            border-left: 4px solid #3498db;
            padding: 15px;
            border-radius: 10px;
        }

        .status-item.success {
            background: rgba(39, 174, 96, 0.1);
            border-left-color: #27ae60;
        }

        .status-item.danger {
            background: rgba(231, 76, 60, 0.1);
            border-left-color: #e74c3c;
        }

        .status-item.warning {
            background: rgba(243, 156, 18, 0.1);
            border-left-color: #f39c12;
        }

        .status-label {
            font-weight: 600;
            margin-bottom: 5px;
            color: #2c3e50;
        }

        .status-value {
            font-size: 1.2em;
            font-weight: 700;
        }

        .log-container {
            background: #2c3e50;
            color: #ecf0f1;
            border-radius: 15px;
            padding: 20px;
            height: 300px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.4;
        }

        .log-entry {
            margin-bottom: 8px;
            padding: 8px;
            border-radius: 5px;
            background: rgba(52, 152, 219, 0.1);
        }

        .log-entry.success {
            background: rgba(39, 174, 96, 0.2);
        }

        .log-entry.error {
            background: rgba(231, 76, 60, 0.2);
        }

        .log-entry.warning {
            background: rgba(243, 156, 18, 0.2);
        }

        .timestamp {
            color: #95a5a6;
            font-size: 12px;
        }

        .alert-banner {
            background: linear-gradient(45deg, #e74c3c, #c0392b);
            color: white;
            padding: 15px;
            border-radius: 15px;
            margin-bottom: 20px;
            text-align: center;
            font-weight: 600;
            animation: alertPulse 1s ease-in-out infinite alternate;
            display: none;
        }

        .alert-banner.show {
            display: block;
        }

        .driver-info {
            text-align: center;
        }

        .driver-status {
            font-size: 1.5em;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 20px;
            padding: 20px;
            border-radius: 10px;
            background: rgba(52, 152, 219, 0.1);
            border: 2px solid #3498db;
        }

        .driver-status.match {
            background: rgba(39, 174, 96, 0.1);
            border-color: #27ae60;
            color: #27ae60;
        }

        .driver-status.mismatch {
            background: rgba(231, 76, 60, 0.1);
            border-color: #e74c3c;
            color: #e74c3c;
        }

        .measurement-times {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 20px;
        }

        .time-item {
            background: rgba(52, 152, 219, 0.1);
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #3498db;
        }

        .time-item.breath {
            border-left-color: #27ae60;
            background: rgba(39, 174, 96, 0.1);
        }

        .time-item.face {
            border-left-color: #9b59b6;
            background: rgba(155, 89, 182, 0.1);
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        @keyframes alertPulse {
            0% { transform: scale(1); }
            100% { transform: scale(1.02); }
        }

        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
            
            .control-buttons {
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
            }

            .measurement-times {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚗 스마트카 관리자 대시보드</h1>
            <div class="connection-status">
                <div class="status-indicator" id="connectionStatus"></div>
                <span id="connectionText">MQTT 연결 중...</span>
            </div>
        </div>

        <div class="alert-banner" id="alertBanner">
            <strong>⚠️ 긴급 상황 발생!</strong> <span id="alertMessage"></span>
        </div>

        <div class="dashboard-grid">
            <div class="card">
                <h2>🔧 수동 제어</h2>
                <div class="control-buttons">
                    <button class="btn btn-success" onclick="sendEngineCommand('ON')">
                        🔥 엔진 시동
                    </button>
                    <button class="btn btn-danger" onclick="sendEngineCommand('OFF')">
                        🛑 엔진 정지
                    </button>
                    <button class="btn btn-warning" onclick="requestFaceVerification()">
                        👤 얼굴 인증 요청
                    </button>
                </div>
            </div>

            <div class="card">
                <h2>📊 시스템 상태</h2>
                <div class="status-grid">
                    <div class="status-item" id="engineStatus">
                        <div class="status-label">엔진 상태</div>
                        <div class="status-value" id="engineValue">대기 중</div>
                    </div>
                    <div class="status-item" id="breathStatus">
                        <div class="status-label">음주 측정</div>
                        <div class="status-value" id="breathValue">대기 중</div>
                    </div>
                    <div class="status-item" id="faceStatus">
                        <div class="status-label">얼굴 인증</div>
                        <div class="status-value" id="faceValue">대기 중</div>
                    </div>
                    <div class="status-item" id="drowsyStatus">
                        <div class="status-label">졸음 감지</div>
                        <div class="status-value" id="drowsyValue">대기 중</div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>👤 운전자 정보</h2>
                <div class="driver-info">
                    <div class="driver-status" id="driverStatus">운전자 상태 대기 중</div>
                    <div class="measurement-times">
                        <div class="time-item breath">
                            <div class="status-label">🍺 음주 측정 시간</div>
                            <div class="status-value" id="breathMeasurementTime">-</div>
                        </div>
                        <div class="time-item face">
                            <div class="status-label">👤 얼굴 인증 시간</div>
                            <div class="status-value" id="faceMeasurementTime">-</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>📝 실시간 로그</h2>
                <div class="log-container" id="logContainer">
                    <div class="log-entry">
                        <span class="timestamp">[시스템 시작]</span> 관리자 대시보드 초기화 완료
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // MQTT 클라이언트 설정
        const MQTT_BROKER = "your_mqtt_broker_ip"; // 실제 브로커 IP로 변경
        const MQTT_PORT = 9001; // WebSocket 포트
        
        // 토픽 정의
        const TOPICS = {
            BREATHALYZER: "breathalyzer/status",
            FACE_REQUEST: "face/request",
            FACE_RESULT: "face/result",
            FACE_IMAGE: "face/image",
            DRIVER_PHOTO: "driver/photo",
            CAR_CONTROL: "car/server",
            RPI_ENGINE: "pi/engine",
            RPI_ALERT: "pi/alert"
        };

        let client;
        let isConnected = false;
        
        // 얼굴 인증 상태 관리
        let lastFaceMatchStatus = null; // 이전 매치 상태 저장

        // 시스템 상태 객체
        const systemStatus = {
            engine: "대기 중",
            breath: "대기 중",
            face: "대기 중",
            drowsy: "정상"
        };

        // MQTT 연결 초기화
        function initMQTT() {
            const clientId = "admin_dashboard_" + Math.random().toString(16).substr(2, 8);
            client = new Paho.MQTT.Client(MQTT_BROKER, MQTT_PORT, clientId);
            
            client.onConnectionLost = onConnectionLost;
            client.onMessageArrived = onMessageArrived;
            
            const options = {
                onSuccess: onConnect,
                onFailure: onFailure,
                keepAliveInterval: 60,
                cleanSession: true
            };
            
            client.connect(options);
        }

        function onConnect() {
            console.log("MQTT 연결 성공");
            isConnected = true;
            updateConnectionStatus(true);
            
            // 모든 토픽 구독
            Object.values(TOPICS).forEach(topic => {
                client.subscribe(topic);
            });
            
            addLog("MQTT 브로커 연결 완료", "success");
        }

        function onFailure(responseObject) {
            console.log("MQTT 연결 실패: " + responseObject.errorMessage);
            updateConnectionStatus(false);
            addLog("MQTT 연결 실패: " + responseObject.errorMessage, "error");
        }

        function onConnectionLost(responseObject) {
            if (responseObject.errorCode !== 0) {
                console.log("MQTT 연결 끊김: " + responseObject.errorMessage);
                isConnected = false;
                updateConnectionStatus(false);
                addLog("MQTT 연결 끊김", "error");
                
                // 재연결 시도
                setTimeout(initMQTT, 5000);
            }
        }

        function onMessageArrived(message) {
            const topic = message.destinationName;
            const payload = message.payloadString;
            
            console.log("메시지 수신:", topic, payload);
            
            switch(topic) {
                case TOPICS.BREATHALYZER:
                    handleBreathalyzerResult(payload);
                    break;
                case TOPICS.FACE_RESULT:
                    handleFaceResult(payload);
                    break;
                case TOPICS.CAR_CONTROL:
                    handleEngineControl(payload);
                    break;
                case TOPICS.RPI_ENGINE:
                    handleEngineControl(payload);
                    break;
                case TOPICS.RPI_ALERT:
                    handleEmergencyAlert(payload);
                    break;
                case TOPICS.FACE_REQUEST:
                    addLog(`얼굴 인증 요청: ${payload}`, "info");
                    break;
                default:
                    // 알 수 없는 토픽에 대한 로그를 제거하고, 단순히 콘솔에만 출력
                    console.log(`기타 토픽 메시지: ${topic} - ${payload}`);
                    break;
            }
        }

        function handleBreathalyzerResult(payload) {
            const timestamp = new Date().toLocaleString();
            
            if (payload === "1") {
                systemStatus.breath = "정상";
                systemStatus.engine = "시동 ON"; // 🎯 엔진 상태 업데이트
                
                updateStatus("breathStatus", "success", "정상");
                updateStatus("engineStatus", "success", "시동 ON"); // 🎯 엔진 상태 표시
                
                addLog("음주 측정 결과: 정상 (운전 가능) → 엔진 시동", "success");
                document.getElementById("breathMeasurementTime").textContent = timestamp;
                
            } else if (payload === "0") {
                systemStatus.breath = "음주 감지";
                systemStatus.engine = "시동 OFF"; // 🎯 엔진 상태 업데이트
                
                updateStatus("breathStatus", "danger", "음주 감지");
                updateStatus("engineStatus", "danger", "시동 OFF"); // 🎯 엔진 상태 표시
                
                addLog("음주 측정 결과: 음주 감지 (운전 불가) → 엔진 정지", "error");
                showAlert("음주가 감지되었습니다!");
                document.getElementById("breathMeasurementTime").textContent = timestamp;
            }
        }

        function handleFaceResult(payload) {
            try {
                const data = JSON.parse(payload);
                const faceMatch = data.face_match;
                const drowsy = data.drowsiness_detected || false;
                const driverName = data.driver_name || "운전자";
                const timestamp = new Date().toLocaleString();
                
                // 🎯 얼굴 인증 시간 업데이트
                document.getElementById("faceMeasurementTime").textContent = timestamp;
                
                // 얼굴 인증 결과 처리
                if (faceMatch === "MATCH") {
                    systemStatus.face = "인증 성공";
                    updateStatus("faceStatus", "success", "인증 성공");
                    addLog(`얼굴 인증: 성공 (${driverName})`, "success");
                    
                    // 운전자 일치 표시
                    updateDriverStatus("match", "✅ 운전자 일치");
                    
                } else if (faceMatch === "MISMATCH") {
                    systemStatus.face = "인증 실패";
                    systemStatus.engine = "시동 OFF"; // 🎯 얼굴 불일치 시 엔진 정지
                    
                    updateStatus("faceStatus", "danger", "인증 실패");
                    updateStatus("engineStatus", "danger", "시동 OFF"); // 🎯 엔진 상태 업데이트
                    
                    addLog("얼굴 인증: 실패 (미등록 사용자) → 엔진 정지", "error");
                    showAlert("미등록 사용자가 감지되었습니다!");
                    
                    // 운전자 불일치 표시
                    updateDriverStatus("mismatch", "❌ 운전자 불일치");
                }
                
                // 이전 상태 저장
                lastFaceMatchStatus = faceMatch;
                
                // 졸음 감지 처리
                if (drowsy) {
                    systemStatus.drowsy = "졸음 감지";
                    updateStatus("drowsyStatus", "danger", "졸음 감지");
                    addLog("졸음 상태 감지됨", "warning");
                    showAlert("운전자 졸음이 감지되었습니다!");
                } else {
                    systemStatus.drowsy = "정상";
                    updateStatus("drowsyStatus", "success", "정상");
                }
                
            } catch (error) {
                addLog("얼굴 인식 데이터 파싱 오류: " + error.message, "error");
            }
        }

        // 🎯 새로운 함수: 엔진 제어 메시지 처리
        function handleEngineControl(payload) {
            if (payload === "ENGINE_ON") {
                systemStatus.engine = "시동 ON";
                updateStatus("engineStatus", "success", "시동 ON");
                addLog(`엔진 제어: 시동 ON`, "success");
            } else if (payload === "ENGINE_OFF") {
                systemStatus.engine = "시동 OFF";
                updateStatus("engineStatus", "danger", "시동 OFF");
                addLog(`엔진 제어: 시동 OFF`, "warning");
            }
        }

        // 긴급상황 알림 처리
        function handleEmergencyAlert(payload) {
            try {
                const data = JSON.parse(payload);
                const alertType = data.type || "unknown";
                const message = data.message || payload;
                const severity = data.severity || "warning";
                
                let logType = "warning";
                let alertMessage = "";
                
                switch(alertType) {
                    case "emergency":
                        logType = "error";
                        alertMessage = `긴급상황: ${message}`;
                        break;
                    case "malfunction":
                        logType = "error";
                        alertMessage = `시스템 고장: ${message}`;
                        break;
                    case "sensor_error":
                        logType = "warning";
                        alertMessage = `센서 오류: ${message}`;
                        break;
                    case "connection_lost":
                        logType = "warning";
                        alertMessage = `연결 끊김: ${message}`;
                        break;
                    default:
                        alertMessage = `알림: ${message}`;
                }
                
                addLog(alertMessage, logType);
                
                if (severity === "critical" || alertType === "emergency") {
                    showAlert(alertMessage);
                }
                
            } catch (error) {
                // JSON이 아닌 일반 텍스트 메시지인 경우
                addLog(`시스템 알림: ${payload}`, "warning");
                if (payload.includes("긴급") || payload.includes("응급") || payload.includes("위험")) {
                    showAlert(payload);
                }
            }
        }

        function sendEngineCommand(command) {
            if (!isConnected) {
                addLog("MQTT 연결이 끊어져 있습니다", "error");
                return;
            }
            
            const message = command === "ON" ? "ENGINE_ON" : "ENGINE_OFF";
            
            // 조향장치와 라즈베리파이에 동시 전송
            publishMessage(TOPICS.CAR_CONTROL, message);
            publishMessage(TOPICS.RPI_ENGINE, message);
            
            systemStatus.engine = command === "ON" ? "시동 ON" : "시동 OFF";
            updateStatus("engineStatus", command === "ON" ? "success" : "danger", systemStatus.engine);
            
            addLog(`수동 엔진 제어: ${message}`, command === "ON" ? "success" : "warning");
        }

        function requestFaceVerification() {
            if (!isConnected) {
                addLog("MQTT 연결이 끊어져 있습니다", "error");
                return;
            }
            
            publishMessage(TOPICS.FACE_REQUEST, "VERIFY_FACE");
            addLog("얼굴 인증 요청 전송", "success");
        }

        function publishMessage(topic, message) {
            const mqttMessage = new Paho.MQTT.Message(message);
            mqttMessage.destinationName = topic;
            client.send(mqttMessage);
        }

        function updateConnectionStatus(connected) {
            const indicator = document.getElementById("connectionStatus");
            const text = document.getElementById("connectionText");
            
            if (connected) {
                indicator.classList.add("connected");
                text.textContent = "MQTT 연결됨";
            } else {
                indicator.classList.remove("connected");
                text.textContent = "MQTT 연결 끊김";
            }
        }

        function updateStatus(elementId, statusClass, value) {
            const element = document.getElementById(elementId);
            const valueElement = element.querySelector(".status-value");
            
            element.className = "status-item " + statusClass;
            valueElement.textContent = value;
        }

        function updateDriverStatus(statusType, message) {
            const driverStatusElement = document.getElementById("driverStatus");
            
            driverStatusElement.className = "driver-status " + statusType;
            driverStatusElement.textContent = message;
        }

        function addLog(message, type = "info") {
            const logContainer = document.getElementById("logContainer");
            const timestamp = new Date().toLocaleString();
            
            const logEntry = document.createElement("div");
            logEntry.className = `log-entry ${type}`;
            logEntry.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message}`;
            
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
            
            // 로그가 너무 많아지면 오래된 것 삭제
            if (logContainer.children.length > 50) {
                logContainer.removeChild(logContainer.firstChild);
            }
        }

        function showAlert(message) {
            const alertBanner = document.getElementById("alertBanner");
            const alertMessage = document.getElementById("alertMessage");
            
            alertMessage.textContent = message;
            alertBanner.classList.add("show");
            
            // 10초 후 자동으로 숨김
            setTimeout(() => {
                alertBanner.classList.remove("show");
            }, 10000);
        }

        // 페이지 로드 시 MQTT 연결 시작
        window.addEventListener('load', function() {
            addLog("관리자 대시보드 시작", "success");
            initMQTT();
        });

        // 페이지 언로드 시 연결 해제
        window.addEventListener('beforeunload', function() {
            if (client && isConnected) {
                client.disconnect();
            }
        });
    </script>
</body>
</html>