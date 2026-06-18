#!/usr/bin/env python3
"""
조도 센서 입력을 숫자/방향 이벤트로 바꾸는 코드.

출력은 한 줄에 하나씩 나온다.
    1
    2
    LEFT
    RIGHT
    UP
    DOWN

uinput 연결 전에도 디버깅할 수 있게 stdout으로 흘린다.
"""

from __future__ import annotations

import argparse
import signal
import statistics
import sys
import time
from dataclasses import dataclass
from enum import Enum

try:
    import spidev
except ImportError:  # 라즈베리파이가 아니면 없을 수 있다.
    spidev = None


SENSOR_COORDS: tuple[tuple[int, int], ...] = (
    (0, 0),
    (1, 0),
    (2, 0),
    (3, 0),
    (0, 1),
    (1, 1),
    (2, 1),
    (3, 1),
)


class GestureState(Enum):
    IDLE = "idle"
    ACTIVE = "active"


@dataclass(frozen=True)
class DetectorConfig:
    interval: float
    frame_window: float
    calibration_seconds: float
    min_delta: float
    noise_multiplier: float
    baseline_alpha: float


@dataclass(frozen=True)
class SensorFrame:
    raw: list[int]
    deltas: list[float]
    pressed: list[bool]


class MCP3008:
    def __init__(self, bus: int = 0, device: int = 0, speed_hz: int = 1_000_000) -> None:
        if spidev is None:
            raise RuntimeError(
                "Missing dependency 'spidev'. Install it on the Raspberry Pi with: "
                "sudo apt install -y python3-spidev"
            )

        self.spi = spidev.SpiDev()
        self.spi.open(bus, device)
        self.spi.max_speed_hz = speed_hz
        self.spi.mode = 0

    def close(self) -> None:
        self.spi.close()

    def read_channel(self, channel: int) -> int:
        if not 0 <= channel <= 7:
            raise ValueError(f"MCP3008 channel must be 0..7, got {channel}")

        response = self.spi.xfer2([1, (8 + channel) << 4, 0])
        return ((response[1] & 0x03) << 8) | response[2]

    def read_all(self) -> list[int]:
        return [self.read_channel(channel) for channel in range(8)]


class KeyboardGestureDetector:
    def __init__(self, config: DetectorConfig, baseline: list[float], thresholds: list[float]) -> None:
        self.config = config
        self.baseline = baseline
        self.thresholds = thresholds
        self.state = GestureState.IDLE
        self.path: list[int] = []
        self.last_pressed_at = 0.0

    def observe(self, raw: list[int], now: float) -> str | None:
        frame = self._build_frame(raw)
        pressed_channels = [channel for channel, pressed in enumerate(frame.pressed) if pressed]

        if self.state == GestureState.IDLE:
            if pressed_channels:
                self._start_gesture(frame, now)
            else:
                self._update_baseline(raw)
            return None

        if pressed_channels:
            self._append_dominant_channel(frame)
            self.last_pressed_at = now
            return None

        if now - self.last_pressed_at < self.config.frame_window:
            return None

        event = classify_path(self.path)
        self._reset_gesture()
        self._update_baseline(raw)
        return event

    def _build_frame(self, raw: list[int]) -> SensorFrame:
        deltas = [self.baseline[channel] - value for channel, value in enumerate(raw)]
        pressed = [
            delta >= self.thresholds[channel] for channel, delta in enumerate(deltas)
        ]
        return SensorFrame(raw=raw, deltas=deltas, pressed=pressed)

    def _start_gesture(self, frame: SensorFrame, now: float) -> None:
        self.state = GestureState.ACTIVE
        self.path = []
        self.last_pressed_at = now
        self._append_dominant_channel(frame)

    def _append_dominant_channel(self, frame: SensorFrame) -> None:
        pressed_channels = [
            channel for channel, pressed in enumerate(frame.pressed) if pressed
        ]
        if not pressed_channels:
            return

        dominant = max(pressed_channels, key=lambda channel: frame.deltas[channel])
        if not self.path or self.path[-1] != dominant:
            self.path.append(dominant)

    def _reset_gesture(self) -> None:
        self.state = GestureState.IDLE
        self.path = []
        self.last_pressed_at = 0.0

    def _update_baseline(self, raw: list[int]) -> None:
        alpha = self.config.baseline_alpha
        for channel, value in enumerate(raw):
            self.baseline[channel] = self.baseline[channel] * (1 - alpha) + value * alpha


def classify_path(path: list[int]) -> str | None:
    if not path:
        return None

    if len(path) == 1:
        return str(path[0] + 1)

    start_x, start_y = SENSOR_COORDS[path[0]]
    end_x, end_y = SENSOR_COORDS[path[-1]]
    dx = end_x - start_x
    dy = end_y - start_y

    if dx > 0:
        return "RIGHT"
    if dx < 0:
        return "LEFT"
    if dy > 0:
        return "DOWN"
    if dy < 0:
        return "UP"

    return str(path[-1] + 1)


def calibrate(adc: MCP3008, config: DetectorConfig) -> tuple[list[float], list[float]]:
    samples: list[list[int]] = []
    deadline = time.monotonic() + config.calibration_seconds

    print(
        f"Calibrating for {config.calibration_seconds:.2f}s. "
        "Keep sensors uncovered.",
        file=sys.stderr,
        flush=True,
    )

    while time.monotonic() < deadline:
        samples.append(adc.read_all())
        time.sleep(config.interval)

    if not samples:
        samples.append(adc.read_all())

    baseline = [
        statistics.fmean(sample[channel] for sample in samples) for channel in range(8)
    ]
    thresholds = []

    for channel in range(8):
        channel_values = [sample[channel] for sample in samples]
        noise = max(abs(value - baseline[channel]) for value in channel_values)
        thresholds.append(max(config.min_delta, noise * config.noise_multiplier))

    print(
        "Calibration complete. "
        f"baseline={format_numbers(baseline)} "
        f"thresholds={format_numbers(thresholds)}",
        file=sys.stderr,
        flush=True,
    )
    return baseline, thresholds


def format_numbers(values: list[float]) -> str:
    return "[" + ", ".join(f"{value:.1f}" for value in values) + "]"


def positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("value must be greater than 0")
    return parsed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stream keyboard-like touch and swipe events from 8 light sensors."
    )
    parser.add_argument("--bus", type=int, default=0, help="SPI bus number. Default: 0")
    parser.add_argument(
        "--device", type=int, default=0, help="SPI device/chip select. Default: 0"
    )
    parser.add_argument(
        "--speed-hz", type=int, default=1_000_000, help="SPI speed. Default: 1000000"
    )
    parser.add_argument(
        "--interval",
        type=positive_float,
        default=0.02,
        help="Sensor polling interval in seconds. Default: 0.02",
    )
    parser.add_argument(
        "--frame-window",
        type=positive_float,
        default=0.3,
        help="Seconds to wait before closing an inactive gesture frame. Default: 0.3",
    )
    parser.add_argument(
        "--calibration-seconds",
        type=positive_float,
        default=1.0,
        help="Initial baseline calibration duration. Default: 1.0",
    )
    parser.add_argument(
        "--min-delta",
        type=positive_float,
        default=50.0,
        help="Minimum ADC drop needed to mark a sensor pressed. Default: 50",
    )
    parser.add_argument(
        "--noise-multiplier",
        type=positive_float,
        default=4.0,
        help="Calibration noise multiplier for per-channel thresholds. Default: 4",
    )
    parser.add_argument(
        "--baseline-alpha",
        type=positive_float,
        default=0.01,
        help="Idle-only baseline smoothing factor. Default: 0.01",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    config = DetectorConfig(
        interval=args.interval,
        frame_window=args.frame_window,
        calibration_seconds=args.calibration_seconds,
        min_delta=args.min_delta,
        noise_multiplier=args.noise_multiplier,
        baseline_alpha=args.baseline_alpha,
    )
    adc = MCP3008(bus=args.bus, device=args.device, speed_hz=args.speed_hz)

    try:
        baseline, thresholds = calibrate(adc, config)
        detector = KeyboardGestureDetector(config, baseline, thresholds)

        while running:
            event = detector.observe(adc.read_all(), time.monotonic())
            if event is not None:
                print(event, flush=True)
            time.sleep(config.interval)
    finally:
        adc.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
