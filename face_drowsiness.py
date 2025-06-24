import cv2
import numpy as np
import time
import threading
import subprocess as sp
from scipy.spatial import distance as dist
import mediapipe as mp
import math
import os
import paho.mqtt.client as mqtt
from datetime import datetime
import json
import base64
import dlib  # 추가: dlib 얼굴 인식용

# MQTT 브로커 설정
MQTT_BROKER = "54.180.239.110"
MQTT_PORT = 1883

# MQTT 토픽
REQUEST_TOPIC = "face/request"
RESULT_TOPIC = "face/result"
CAR_TOPIC = "car/server"
DROWSINESS_TOPIC = "driver/drowsiness"
FACE_IMAGE_TOPIC = "face/image"

# MediaPipe 얼굴 메시 초기화
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    min_detection_confidence=0.2,
    min_tracking_confidence=0.2,
    refine_landmarks=False
)

# dlib 얼굴 인식 모델 초기화
print("dlib 모델을 로드하는 중...")
try:
    # 얼굴 검출기
    detector = dlib.get_frontal_face_detector()
    
    # 얼굴 랜드마크 예측기 (68개 점)
    shape_predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
    
    # 얼굴 인식 모델 (128차원 벡터 생성)
    face_encoder = dlib.face_recognition_model_v1("dlib_face_recognition_resnet_model_v1.dat")
    
    print("dlib 모델 로드 완료!")
    dlib_available = True
except Exception as e:
    print(f"dlib 모델 로드 실패: {e}")
    print("모델 파일을 다운로드하세요:")
    print("- shape_predictor_68_face_landmarks.dat")
    print("- dlib_face_recognition_resnet_model_v1.dat")
    print("http://dlib.net/files/에서 다운로드 가능합니다.")
    dlib_available = False

# 디렉토리 생성 함수
def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# 얼굴 이미지를 저장할 디렉토리 생성
ensure_dir("face_captures")
ensure_dir("face_encodings")  # 얼굴 인코딩 저장용

# 눈 가로세로비율(EAR) 계산 함수
def calculate_EAR(eye_points):
    # 눈의 세로 거리 계산
    A = dist.euclidean(eye_points[1], eye_points[5])
    B = dist.euclidean(eye_points[2], eye_points[4])
   
    # 눈의 가로 거리 계산
    C = dist.euclidean(eye_points[0], eye_points[3])
   
    # 0으로 나누기 방지 및 EAR 계산
    if C < 0.1:  
        return 0.3
       
    ear = (A + B) / (2.0 * C)
    return ear

# 고개 방향 계산 함수
def calculate_head_pose(face_landmarks, image_width, image_height):
    # 특징점 추출 (코, 이마, 턱)
    nose_tip = (int(face_landmarks.landmark[1].x * image_width),
               int(face_landmarks.landmark[1].y * image_height))
    forehead = (int(face_landmarks.landmark[10].x * image_width),
               int(face_landmarks.landmark[10].y * image_height))
    chin = (int(face_landmarks.landmark[152].x * image_width),
           int(face_landmarks.landmark[152].y * image_height))
   
    # 얼굴 중심점 (양쪽 귀 사이 중앙)
    left_ear = (int(face_landmarks.landmark[234].x * image_width),
               int(face_landmarks.landmark[234].y * image_height))
    right_ear = (int(face_landmarks.landmark[454].x * image_width),
                int(face_landmarks.landmark[454].y * image_height))
   
    # 얼굴 중심 계산
    face_center_x = (left_ear[0] + right_ear[0]) / 2
    face_center_y = (left_ear[1] + right_ear[1]) / 2
   
    # 고개 기울기 각도 계산 (세로축 기준)
    vertical_angle = math.degrees(math.atan2(chin[1] - nose_tip[1], chin[0] - nose_tip[0]))
   
    # 정면 응시 여부 계산
    horizontal_deviation = abs(nose_tip[0] - face_center_x) / image_width
   
    # 고개 떨굼 감지
    head_drop = (chin[1] - forehead[1]) / image_height
   
    return vertical_angle, horizontal_deviation, head_drop, (nose_tip, forehead, chin)

# dlib을 사용한 얼굴 인코딩 추출 함수
def get_face_encoding_dlib(face_image):
    """
    dlib을 사용하여 얼굴 이미지에서 128차원 인코딩 벡터를 추출
    """
    if not dlib_available:
        return None
    
    # RGB로 변환 (dlib은 RGB를 사용)
    rgb_image = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
    
    # 얼굴 검출
    faces = detector(rgb_image, 1)
    
    if len(faces) == 0:
        print("dlib: 얼굴을 찾을 수 없습니다.")
        return None
    
    # 첫 번째 얼굴 사용
    face = faces[0]
    
    # 얼굴 랜드마크 추출
    shape = shape_predictor(rgb_image, face)
    
    # 얼굴 인코딩 (128차원 벡터) 생성
    face_encoding = face_encoder.compute_face_descriptor(rgb_image, shape)
    
    # numpy 배열로 변환
    return np.array(face_encoding)

# dlib 기반 얼굴 비교 함수
def compare_faces_dlib(encoding1, encoding2, threshold=0.6):
    """
    dlib 얼굴 인코딩을 비교
    encoding1, encoding2: 128차원 얼굴 인코딩 벡터
    threshold: 동일인 판단 임계값 (기본값 0.6)
    """
    if encoding1 is None or encoding2 is None:
        print("인코딩이 None입니다. 히스토그램 비교로 대체합니다.")
        return 0.0, False
    
    # 유클리드 거리 계산
    distance = np.linalg.norm(encoding1 - encoding2)
    
    # 유사도 계산 (0~1 범위로 정규화)
    # 거리가 0이면 유사도 1, 거리가 1이면 유사도 0
    similarity = max(0, 1 - distance)
    
    # 동일인 여부 판단
    is_same_person = distance < threshold
    
    # 디버깅 정보
    print(f"dlib 얼굴 비교 - 거리: {distance:.3f}, 유사도: {similarity:.3f}, 임계값: {threshold}")
    
    return similarity, is_same_person

# 히스토그램 기반 얼굴 비교 함수 (폴백용)
def compare_faces_histogram(face1, face2):
    """
    히스토그램을 사용한 얼굴 비교 (dlib 실패 시 폴백)
    """
    # 이미지 크기 통일
    face1 = cv2.resize(face1, (100, 100))
    face2 = cv2.resize(face2, (100, 100))
   
    # 그레이스케일 변환
    gray1 = cv2.cvtColor(face1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(face2, cv2.COLOR_BGR2GRAY)
   
    # 히스토그램 계산
    hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
    hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
   
    # 히스토그램 정규화
    cv2.normalize(hist1, hist1, 0, 1, cv2.NORM_MINMAX)
    cv2.normalize(hist2, hist2, 0, 1, cv2.NORM_MINMAX)
   
    # 히스토그램 비교 (상관관계 방식)
    similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
   
    # 유사도 임계값 (0.7 이상이면 동일인으로 판단)
    return similarity, similarity >= 0.7

# 얼굴 이미지를 base64로 인코딩하여 MQTT로 전송하는 함수
def send_face_image(face_roi, is_match=True):
    """
    얼굴 이미지를 관리자 페이지로 전송
    face_roi: 얼굴 영역 이미지
    is_match: True면 등록된 사용자, False면 미등록 사용자
    """
    try:
        if face_roi is None or face_roi.size == 0:
            return
           
        # 이미지 크기 조정 (전송 최적화를 위해 적당한 크기로)
        face_resized = cv2.resize(face_roi, (150, 150))
       
        # 이미지를 JPEG로 인코딩
        _, buffer = cv2.imencode('.jpg', face_resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
       
        # base64로 인코딩
        image_base64 = base64.b64encode(buffer).decode('utf-8')
       
        # 전송할 데이터 구성
        image_data = {
            "image": image_base64,
            "type": "registered" if is_match else "unregistered",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
       
        # MQTT로 전송
        client.publish(FACE_IMAGE_TOPIC, json.dumps(image_data))
        print(f"얼굴 이미지 전송 완료 - 타입: {'등록됨' if is_match else '미등록'}")
       
    except Exception as e:
        print(f"얼굴 이미지 전송 오류: {e}")

# MediaPipe 랜드마크 인덱스
LEFT_EYE = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33, 160, 158, 133, 153, 144]

# 전역 변수
verification_mode = False
capture_mode = False
reference_face = None
reference_encoding = None  # 추가: 참조 얼굴의 dlib 인코딩
last_verification_time = 0
face_capture_countdown = 0

# 졸음 감지 상태 전역 변수
drowsiness_state = {
    "eye_warning": False,
    "head_pose_warning": False,
    "last_drowsiness_time": 0,
    "last_sent_state": None
}

# MQTT 클라이언트 콜백 함수
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT 브로커에 연결되었습니다")
        client.subscribe(REQUEST_TOPIC)
    else:
        print(f"MQTT 브로커 연결 실패, 코드: {rc}")

def on_message(client, userdata, msg):
    global verification_mode, capture_mode, reference_face, reference_encoding
   
    payload = msg.payload.decode()
    print(f"메시지 수신: {payload}")
   
    if msg.topic == REQUEST_TOPIC and payload == "VERIFY_FACE":
        print("얼굴 인증 요청을 받았습니다.")
        verification_mode = True
        capture_mode = True
        reference_face = None
        reference_encoding = None  # 인코딩도 초기화

# MQTT 클라이언트 설정
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# 얼굴 인증 결과 전송 함수
def send_verification_result(is_same_person, face_roi=None):
    result = {
        "face_match": "MATCH" if is_same_person else "MISMATCH",
        "drowsiness_detected": drowsiness_state["eye_warning"] or drowsiness_state["head_pose_warning"],
        "eye_warning": drowsiness_state["eye_warning"],
        "head_pose_warning": drowsiness_state["head_pose_warning"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
   
    client.publish(RESULT_TOPIC, json.dumps(result))
    print(f"얼굴 인증 결과 전송: {json.dumps(result)}")
   
    if face_roi is not None:
        send_face_image(face_roi, is_same_person)

# 졸음 감지 결과 전송 함수
def send_drowsiness_alert():
    alert_data = {
        "drowsiness_detected": drowsiness_state["eye_warning"] or drowsiness_state["head_pose_warning"],
        "eye_warning": drowsiness_state["eye_warning"],
        "head_pose_warning": drowsiness_state["head_pose_warning"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
   
    current_state = (drowsiness_state["eye_warning"], drowsiness_state["head_pose_warning"])
   
    if drowsiness_state["last_sent_state"] != current_state:
        client.publish(DROWSINESS_TOPIC, json.dumps(alert_data))
        print(f"졸음 감지 결과 전송: {json.dumps(alert_data)}")
        
        drowsiness_state["last_sent_state"] = current_state
        drowsiness_state["last_drowsiness_time"] = time.time()

def main():
    global verification_mode, capture_mode, reference_face, reference_encoding
    global last_verification_time, face_capture_countdown
    global drowsiness_state
   
    try:
        # MQTT 브로커 연결
        print(f"MQTT 브로커({MQTT_BROKER}:{MQTT_PORT})에 연결 중...")
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
       
        print("얼굴 인증 및 졸음 감지 시스템 시작...")
        
        if dlib_available:
            print("dlib 얼굴 인식 모델이 활성화되었습니다.")
        else:
            print("dlib을 사용할 수 없어 히스토그램 비교를 사용합니다.")
       
        # 해상도 설정
        width, height = 320, 240
       
        # GStreamer 명령어 설정 (IMX219 카메라용)
        command = [
            'gst-launch-1.0',
            '-q',
            'nvarguscamerasrc',
            '!', f'video/x-raw(memory:NVMM),width={width},height={height},format=NV12,framerate=30/1',
            '!', 'nvvidconv', 'flip-method=0',
            '!', 'video/x-raw,format=BGRx',
            '!', 'videoconvert',
            '!', 'video/x-raw,format=BGR',
            '!', 'fdsink'
        ]
       
        # 졸음 감지 파라미터
        EAR_THRESHOLD = 0.3
        EAR_FRAMES = 60
        PERCLOS_WINDOW = 90
        PERCLOS_THRESHOLD = 30
       
        # 고개 자세 감지 파라미터
        CENTER_ANGLE = 90.0
        VERTICAL_ANGLE_THRESHOLD = 25.0
        HORIZONTAL_DEVIATION_THRESHOLD = 0.08
        HEAD_DROP_THRESHOLD = 0.30
        HEAD_POSE_FRAMES = 90
       
        # 경고 리셋 파라미터
        EAR_RESET_FRAMES = 30
        HEAD_POSE_RESET_FRAMES = 30
       
        # 졸음 감지 변수 초기화
        ear_counter = 0
        ear_normal_counter = 0
        perclos_total_frames = 0
        perclos_closed_frames = 0
        head_pose_counter = 0
        head_pose_normal_counter = 0
       
        ear_warning_flag = False
        head_pose_warning_flag = False
       
        # GStreamer 프로세스 시작
        process = sp.Popen(command, stdout=sp.PIPE, stderr=sp.PIPE, bufsize=10**9)
       
        # 프레임 크기 계산
        frame_size = width * height * 3
       
        print("카메라 시작... 종료하려면 'q'를 누르세요.")
        print("AWS 서버로부터 얼굴 인증 요청 대기 중...")
        
        while True:
            # 프레임 읽기
            raw_image = process.stdout.read(frame_size)
           
            if len(raw_image) != frame_size:
                time.sleep(0.01)
                continue
           
            # 프레임을 NumPy 배열로 변환
            try:
                frame = np.frombuffer(raw_image, dtype=np.uint8).reshape((height, width, 3))
            except Exception as e:
                print(f"프레임 변환 오류: {e}")
                continue
           
            # 프레임 유효성 확인
            if frame is None or frame.size == 0:
                continue
           
            # 안전한 복사본 생성
            display_frame = frame.copy()
           
            # RGB로 변환 (MediaPipe 요구사항)
            try:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            except Exception as e:
                print(f"RGB 변환 오류: {e}")
                continue
           
            # 얼굴 랜드마크 감지
            results = face_mesh.process(rgb_frame)
           
            # 현재 시간
            current_time = time.time()
           
            # 상태 표시
            if not verification_mode:
                status_text = "AWS 서버 요청 대기 중..."
            elif capture_mode:
                status_text = "얼굴 캡처 모드 - 3초 후 캡처합니다"
            else:
                status_text = "얼굴 검증 모드 - 10초마다 검증합니다"
           
            cv2.putText(display_frame, status_text, (10, 20),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
           
            # 얼굴 랜드마크가 감지된 경우
            if results.multi_face_landmarks:
                face_landmarks = results.multi_face_landmarks[0]
               
                # 얼굴 경계 좌표 계산
                x_coords = [landmark.x * width for landmark in face_landmarks.landmark]
                y_coords = [landmark.y * height for landmark in face_landmarks.landmark]
               
                # 얼굴 사각형 좌표
                x_min, x_max = int(min(x_coords)), int(max(x_coords))
                y_min, y_max = int(min(y_coords)), int(max(y_coords))
               
                # 사각형 경계 보정
                x_min = max(0, x_min)
                y_min = max(0, y_min)
                x_max = min(width, x_max)
                y_max = min(height, y_max)
               
                # 얼굴 영역
                face_roi = frame[y_min:y_max, x_min:x_max]
               
                # 눈 랜드마크 추출
                try:
                    left_eye_points = [(int(face_landmarks.landmark[idx].x * width),
                                        int(face_landmarks.landmark[idx].y * height)) for idx in LEFT_EYE]
                    right_eye_points = [(int(face_landmarks.landmark[idx].x * width),
                                         int(face_landmarks.landmark[idx].y * height)) for idx in RIGHT_EYE]
                   
                    # 눈 랜드마크 그리기
                    for point in left_eye_points + right_eye_points:
                        cv2.drawMarker(display_frame, point, (0, 255, 0),
                                      markerType=0, markerSize=3, thickness=1)
                   
                    # EAR 계산
                    left_ear = calculate_EAR(left_eye_points)
                    right_ear = calculate_EAR(right_eye_points)
                    current_ear = (left_ear + right_ear) / 2.0
                   
                    # EAR 값 표시
                    eye_text_color = (0, 0, 255) if current_ear < EAR_THRESHOLD else (0, 255, 0)
                    cv2.putText(display_frame, f"EAR: {current_ear:.2f}", (10, 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, eye_text_color, 1)
                except Exception as e:
                    print(f"눈 랜드마크 추출 오류: {e}")
                    current_ear = None
               
                # 고개 자세 계산
                try:
                    vertical_angle, horizontal_deviation, head_drop, head_points = calculate_head_pose(
                        face_landmarks, width, height)
                   
                    # 정면 응시 여부
                    face_centered = (
                        abs(vertical_angle - CENTER_ANGLE) <= VERTICAL_ANGLE_THRESHOLD and
                        horizontal_deviation <= HORIZONTAL_DEVIATION_THRESHOLD and
                        head_drop >= HEAD_DROP_THRESHOLD
                    )
                   
                    # 고개 자세 정보 표시
                    cv2.putText(display_frame, f"Head angle: {vertical_angle:.1f}", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                    cv2.putText(display_frame, f"Gaze dev: {horizontal_deviation:.2f}", (10, 80),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                    cv2.putText(display_frame, f"Head drop: {head_drop:.2f}", (10, 100),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                   
                    # 고개 자세 포인트 그리기
                    if head_points:
                        for point in head_points:
                            cv2.drawMarker(display_frame, point, (255, 0, 0),
                                          markerType=0, markerSize=5, thickness=1)
                except Exception as e:
                    print(f"고개 자세 계산 오류: {e}")
                    face_centered = False
                    vertical_angle, horizontal_deviation, head_drop = 0, 0, 0
               
                # AWS 서버 요청 이후 얼굴 캡처 모드
                if verification_mode and capture_mode:
                    if face_capture_countdown == 0:
                        face_capture_countdown = 3 * 30  # 3초 (30FPS 기준)
                        print("얼굴 캡처 준비 중 - 3초 후 캡처합니다")
                   
                    face_capture_countdown -= 1
                   
                    # 카운트다운 표시
                    seconds_left = face_capture_countdown // 30 + 1
                    cv2.putText(display_frame, f"Capturing in: {seconds_left}s",
                               (width//2 - 70, height//2 + 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                   
                    # 카운트다운 완료 시 얼굴 캡처
                    if face_capture_countdown <= 0:
                        if face_roi.size > 0:
                            # 참조 얼굴로 저장
                            reference_face = face_roi.copy()
                            
                            # dlib 인코딩 추출
                            if dlib_available:
                                print("dlib으로 참조 얼굴 인코딩을 추출합니다...")
                                reference_encoding = get_face_encoding_dlib(face_roi)
                                
                                if reference_encoding is not None:
                                    print("참조 얼굴 인코딩 추출 성공!")
                                    
                                    # 인코딩 저장 (옵션)
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    np.save(f"face_encodings/reference_encoding_{timestamp}.npy", reference_encoding)
                                else:
                                    print("dlib 인코딩 추출 실패. 히스토그램 비교를 사용합니다.")
                            
                            # 참조용 얼굴 파일로 저장
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            cv2.imwrite(f"face_captures/reference_face_{timestamp}.jpg", face_roi)
                            print(f"참조 얼굴 캡처 완료! ({timestamp})")
                           
                            # 상태 변경
                            capture_mode = False
                            last_verification_time = current_time
                            print("10초마다 얼굴 비교를 시작합니다.")
               
                # 얼굴 검증 모드 (참조 얼굴 캡처 완료 후)
                elif verification_mode and not capture_mode and reference_face is not None:
                    # 다음 검증까지 남은 시간 표시
                    time_elapsed = current_time - last_verification_time
                    time_to_next = 10 - (time_elapsed % 10)
                   
                    cv2.putText(display_frame, f"Next verification: {int(time_to_next)}s",
                               (10, height - 10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                   
                    # 10초마다 얼굴 비교
                    if time_elapsed >= 10:
                        print(f"10초 경과: 얼굴 비교 수행 ({datetime.now().strftime('%H:%M:%S')})")
                        last_verification_time = current_time
                       
                        if face_roi.size > 0:
                            # 얼굴 비교 수행
                            if dlib_available and reference_encoding is not None:
                                # dlib을 사용한 비교
                                print("dlib으로 얼굴을 비교합니다...")
                                current_encoding = get_face_encoding_dlib(face_roi)
                                
                                if current_encoding is not None:
                                    similarity, is_same_person = compare_faces_dlib(
                                        reference_encoding, current_encoding, threshold=0.6)
                                    
                                    # 유사도 텍스트
                                    similarity_text = f"Similarity: {similarity:.3f}"
                                    result_text = "MATCH" if is_same_person else "MISMATCH"
                            else:
                                # 히스토그램 비교 (폴백)
                                print("dlib을 사용할 수 없어 히스토그램 비교를 수행합니다.")
                                similarity, is_same_person = compare_faces_histogram(reference_face, face_roi)
                                similarity_text = f"Histogram: {similarity:.2f}"
                                result_text = "MATCH" if is_same_person else "MISMATCH"
                           
                            cv2.putText(display_frame, similarity_text, (10, height - 30),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                            cv2.putText(display_frame, result_text, (10, height - 50),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                                       (0, 255, 0) if is_same_person else (0, 0, 255), 1)
                           
                            print(f"얼굴 비교 결과: {similarity:.2f} - {result_text}")
                           
                            # AWS 서버로 결과 전송
                            send_verification_result(is_same_person, face_roi)
               
                # 졸음 감지 및 고개 자세 모니터링 (항상 수행)
                if current_ear is not None:
                    # EAR 알고리즘 (2초 이상 눈 감음)
                    if current_ear < EAR_THRESHOLD:
                        ear_counter += 1
                        ear_normal_counter = 0
                       
                        # 2초 이상 눈을 감았을 때 경고
                        if ear_counter >= EAR_FRAMES and not ear_warning_flag:
                            print("\n[졸음 감지] 2초 이상 눈을 감았습니다!")
                            ear_warning_flag = True
                            drowsiness_state["eye_warning"] = True
                           
                            # 졸음 감지 즉시 서버로 알림
                            send_drowsiness_alert()
                    else:
                        # 눈을 뜬 경우
                        ear_counter = 0
                       
                        # 정상 눈 상태 확인
                        if ear_warning_flag:
                            ear_normal_counter += 1
                           
                            # 1초 이상 눈을 정상적으로 뜨면 경고 해제
                            if ear_normal_counter >= EAR_RESET_FRAMES:
                                print("\n[눈 상태] 정상 상태로 돌아왔습니다.")
                                ear_warning_flag = False
                                drowsiness_state["eye_warning"] = False
                               
                                # 경고 해제 시 서버로 알림
                                send_drowsiness_alert()
                   
                    # 졸음 경고 표시
                    if ear_warning_flag:
                        cv2.putText(display_frame, "DROWSINESS WARNING!", (width//2 - 100, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
               
                # 고개 자세 비정상 감지 (3초 기준)
                if 'vertical_angle' in locals() and 'horizontal_deviation' in locals() and 'head_drop' in locals():
                    head_pose_incorrect = (
                        abs(vertical_angle - CENTER_ANGLE) > VERTICAL_ANGLE_THRESHOLD or
                        horizontal_deviation > HORIZONTAL_DEVIATION_THRESHOLD or
                        head_drop < HEAD_DROP_THRESHOLD
                    )
                   
                    if head_pose_incorrect:
                        head_pose_counter += 1
                        head_pose_normal_counter = 0
                       
                        # 3초 이상 고개 자세가 비정상일 때
                        if head_pose_counter >= HEAD_POSE_FRAMES and not head_pose_warning_flag:
                            print("\n[고개 자세 경고] 3초 이상 비정상 자세가 지속되었습니다!")
                            head_pose_warning_flag = True
                            drowsiness_state["head_pose_warning"] = True
                           
                            # 고개 자세 비정상 감지 시 서버로 알림
                            send_drowsiness_alert()
                    else:
                        # 고개 자세가 정상일 때
                        head_pose_counter = 0
                       
                        # 정상 자세 확인
                        if head_pose_warning_flag:
                            head_pose_normal_counter += 1
                           
                            # 1초 이상 정상 자세면 경고 해제
                            if head_pose_normal_counter >= HEAD_POSE_RESET_FRAMES:
                                print("\n[고개 자세] 정상 자세로 돌아왔습니다.")
                                head_pose_warning_flag = False
                                drowsiness_state["head_pose_warning"] = False
                               
                                # 경고 해제 시 서버로 알림
                                send_drowsiness_alert()
                   
                    # 고개 자세 경고 표시
                    if head_pose_warning_flag:
                        cv2.putText(display_frame, "HEAD POSE WARNING!", (width//2 - 100, 50),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)
               
                # 얼굴 사각형 그리기
                rect_color = (0, 255, 0)  # 기본 초록색
                if ear_warning_flag:
                    rect_color = (0, 0, 255)  # 졸음 감지 시 빨간색
                elif head_pose_warning_flag:
                    rect_color = (0, 165, 255)  # 고개 자세 비정상 시 주황색
               
                cv2.rectangle(display_frame, (x_min, y_min), (x_max, y_max), rect_color, 2)
               
                # 상태 표시
                try:
                    # 얼굴 인증 모드 표시
                    mode_text = "INACTIVE"
                    if verification_mode:
                        mode_text = "CAPTURE" if capture_mode else "VERIFY"
                   
                    cv2.putText(display_frame, f"Mode: {mode_text}",
                               (width - 140, 40),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                               (0, 255, 0) if verification_mode else (0, 0, 255), 1)
                   
                    # 참조 얼굴 상태
                    ref_text = "Captured" if reference_face is not None else "Not captured"
                    cv2.putText(display_frame, f"Reference: {ref_text}",
                               (width - 140, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                               (0, 255, 0) if reference_face is not None else (0, 0, 255), 1)
                   
                    # MQTT 상태
                    mqtt_text = "Connected" if client.is_connected() else "Disconnected"
                    cv2.putText(display_frame, f"MQTT: {mqtt_text}",
                               (width - 140, 80),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                               (0, 255, 0) if client.is_connected() else (0, 0, 255), 1)
                   
                    # 눈 상태 표시
                    if current_ear is not None:
                        eye_state = "CLOSED" if current_ear < EAR_THRESHOLD else "OPEN"
                        cv2.putText(display_frame, f"Eye: {eye_state}",
                                   (width - 140, 100),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, eye_text_color, 1)
                   
                    # 졸음 감지 상태 표시
                    drowsy_text = "ACTIVE" if drowsiness_state["eye_warning"] or drowsiness_state["head_pose_warning"] else "NONE"
                    drowsy_color = (0, 0, 255) if drowsy_text == "ACTIVE" else (0, 255, 0)
                    cv2.putText(display_frame, f"Drowsy: {drowsy_text}",
                               (width - 140, 120),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, drowsy_color, 1)
                    
                    # dlib 상태 표시
                    dlib_text = "dlib" if dlib_available else "Histogram"
                    cv2.putText(display_frame, f"Method: {dlib_text}",
                               (width - 140, 140),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
                except Exception as e:
                    print(f"정보 표시 오류: {e}")
            else:
                # 얼굴이 감지되지 않은 경우
                if verification_mode and capture_mode:
                    cv2.putText(display_frame, "No face detected!",
                               (width//2 - 70, height//2),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
           
            # 프레임 표시
            try:
                display_frame_resized = cv2.resize(display_frame, (width*2, height*2), interpolation=cv2.INTER_LINEAR)
                cv2.imshow("Face Verification & Drowsiness Detection (dlib)", display_frame_resized)
            except Exception as e:
                print(f"프레임 표시 오류: {e}")
           
            # 'q' 키로 종료
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
       
    except KeyboardInterrupt:
        print("프로그램 중단됨")
    except Exception as e:
        print(f"주요 오류 발생: {e}")
    finally:
        # 리소스 해제
        try:
            client.loop_stop()
            client.disconnect()
        except:
            pass
       
        try:
            process.terminate()
            cv2.destroyAllWindows()
        except:
            pass
       
        print("프로그램 종료")

if __name__ == "__main__":
    main()
    
else:
    print("현재 얼굴 인코딩 추출 실패")
    # 폴백: 히스토그램 비교
    similarity, is_same_person = compare_faces_histogram(reference_face, face_roi)
    similarity_text = f"Histogram: {similarity:.2f}"
    result_text = "MATCH" if is_same_person else "MISMATCH"