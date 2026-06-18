# Light Scroll Controller

## 프로젝트 소개

Light Scroll Controller는 GL5537 CdS 조도 센서 8개를 2x4 배열로 배치해
손가락 그림자의 이동을 입력으로 해석하는 Raspberry Pi 기반 입력 장치이다.

센서 위에는 투명 필름을 얹어 사용자가 터치패드처럼 조작할 수 있게 한다.
사용자가 필름 위를 터치하거나 쓸어 넘기면 각 센서에 들어오는 빛의 양이
달라지고, 프로그램은 이 조도 변화량과 변화 순서를 분석해 터치 및 스와이프
제스처를 판정한다.

현재 구현은 두 가지 입력 모드를 제공한다.

- 터치: 센서 1~8을 숫자패드 1~8 입력으로 변환
- 스와이프: 좌/우/상/하 움직임을 방향키 입력으로 변환

이 프로젝트의 목적은 고가의 터치패널이나 카메라 없이, 저렴한 조도 센서와
ADC만으로 범용적인 제스처 입력 장치를 구현하는 것이다.

## 회로 연결

사용 부품:

- Raspberry Pi 4
- MCP3008 ADC
- GL5537 CdS 조도 센서 8개
- 10k ohm 저항 8개
- 브레드보드 및 점퍼선

전원 레일:

```text
Raspberry Pi 3.3V  -> 브레드보드 3.3V 레일
Raspberry Pi GND   -> 브레드보드 GND 레일

브레드보드 3.3V   -> MCP3008 VDD, VREF, GL5537 센서 입력
브레드보드 GND    -> MCP3008 AGND, DGND, 센서 분압 저항
```

MCP3008은 반드시 3.3V로 동작시킨다. Raspberry Pi GPIO는 5V 입력을 허용하지
않으므로 MCP3008이나 GPIO 쪽에 5V를 연결하지 않는다.

MCP3008과 Raspberry Pi 연결:

```text
MCP3008 VDD  pin 16 -> 3.3V
MCP3008 VREF pin 15 -> 3.3V
MCP3008 AGND pin 14 -> GND
MCP3008 DGND pin 9  -> GND

MCP3008 CLK  pin 13 -> GPIO11 / SCLK / physical pin 23
MCP3008 DOUT pin 12 -> GPIO9  / MISO / physical pin 21
MCP3008 DIN  pin 11 -> GPIO10 / MOSI / physical pin 19
MCP3008 CS   pin 10 -> GPIO8  / CE0  / physical pin 24
```

조도 센서 분압 회로:

```text
3.3V
 |
[GL5537]
 |
 +----> MCP3008 CHx
 |
[10k ohm 저항]
 |
GND
```

이 배선에서는 밝을수록 ADC 값이 커지고, 손가락 그림자가 생기면 ADC 값이
작아진다.

센서 채널 배치:

```text
Sensor 1 -> MCP3008 CH0 pin 1
Sensor 2 -> MCP3008 CH1 pin 2
Sensor 3 -> MCP3008 CH2 pin 3
Sensor 4 -> MCP3008 CH3 pin 4
Sensor 5 -> MCP3008 CH4 pin 5
Sensor 6 -> MCP3008 CH5 pin 6
Sensor 7 -> MCP3008 CH6 pin 7
Sensor 8 -> MCP3008 CH7 pin 8
```

권장 2x4 센서 배열:

```text
CH0  CH1  CH2  CH3
CH4  CH5  CH6  CH7
```
