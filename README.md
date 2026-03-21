# IoT Lab 2 - PiCar-X Networking (Bluetooth + WiFi)
CS 437 @ UIUC

## 파일 구조

```
iot-lab2/
├── bluetooth/                     ← 블루투스 (보너스 5점)
│   ├── pi_bluetooth_server.py     ← Pi에서 실행
│   └── pc_bluetooth_client.py     ← PC에서 실행 (Tkinter GUI)
├── wifi_server/                   ← WiFi 서버 (메인)
│   └── wifi_server.py             ← Pi에서 실행
├── electron_app/                  ← Electron 프론트엔드 (메인)
│   ├── package.json
│   ├── main.js
│   ├── preload.js
│   ├── index.html
│   └── index.js
└── README.md
```

## 네 Lab 1 코드와 연동

Pi쪽 서버 코드(pi_bluetooth_server.py, wifi_server.py) 모두
네 Lab 1의 PiCar-X API를 그대로 사용:

- `from picarx import Picarx` / `px = Picarx()`
- `px.forward(speed)` / `px.backward(speed)` / `px.stop()`
- `px.set_dir_servo_angle(angle)` (-30 ~ +30)
- `px.ultrasonic.read()` (3회 평균, 네 get_front_dist() 방식)
- 기본 속도: 5, 조향각: 30 (Lab 1과 동일)

## 전송하는 데이터 (8가지, 최소 3개 요구사항 초과)

| Pi → PC | 설명 |
|---------|------|
| cpu_temp | CPU 온도 (°C) |
| battery_percent | 배터리 잔량 (%) |
| battery_voltage | 배터리 전압 (V) |
| speed | 현재 속도 |
| direction | 방향 (forward/backward/left/right/stopped) |
| steering_angle | 조향각 (°) |
| distance_traveled | 누적 주행 거리 (cm) |
| obstacle_dist | 초음파 장애물 거리 (cm) |

| PC → Pi | 설명 |
|---------|------|
| forward | 전진 |
| backward | 후진 |
| left | 좌회전 |
| right | 우회전 |
| stop | 정지 |
| GET_STATUS | 상태 요청 |

---

## 실행 방법

### 블루투스 (보너스)

**Pi 사전 설정:**
```bash
# bluez.service 수정 (lab 문서 참고)
sudo nano /etc/systemd/system/dbus-org.bluez.service
# ExecStart 줄 끝에 -C 추가
# ExecStartPost=/usr/bin/sdptool add SP 줄 추가
sudo systemctl daemon-reload
sudo systemctl restart bluetooth.service
```

**Pi에서:**
```bash
python3 pi_bluetooth_server.py
```

**PC에서:**
1. pc_bluetooth_client.py 열어서 `SERVER_MAC` 수정
   (Pi MAC 확인: Pi에서 `bluetoothctl show`)
2. 실행:
```bash
python3 pc_bluetooth_client.py
```

### WiFi + Electron (메인)

**Pi에서:**
```bash
python3 wifi_server.py
# 출력되는 IP 주소 메모
```

**PC에서:**
```bash
cd electron_app
npm install     # 처음 한 번
npm start
```
→ IP 입력 → Connect → 버튼/키보드로 제어

---

## 키보드 단축키 (블루투스 & Electron 둘 다)

| 키 | 동작 |
|----|------|
| ↑ / W | 전진 |
| ↓ / S | 후진 |
| ← / A | 좌회전 |
| → / D | 우회전 |
| Space / Q | 정지 |
