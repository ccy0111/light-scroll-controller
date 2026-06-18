#!/usr/bin/env python3
"""
센서 제스처를 실제 키보드 입력처럼 보내는 코드.

매핑:
    1..8        -> numpad 1..8
    LEFT/RIGHT  -> keyboard arrow keys
    UP/DOWN     -> keyboard arrow keys
"""

from __future__ import annotations

import argparse
import signal
import sys
import time

from keyboard_input_stream import (
    DetectorConfig,
    KeyboardGestureDetector,
    MCP3008,
    calibrate,
    positive_float,
)

try:
    from evdev import UInput, ecodes
except ImportError:  # evdev 설치 전이면 여기로 온다.
    UInput = None
    ecodes = None


class UInputKeyboard:
    def __init__(self, key_hold: float) -> None:
        if UInput is None or ecodes is None:
            raise RuntimeError(
                "Missing dependency 'evdev'. Install it on the Raspberry Pi with: "
                "sudo apt install -y python3-evdev"
            )

        self.key_hold = key_hold
        self.key_map = {
            "1": ecodes.KEY_KP1,
            "2": ecodes.KEY_KP2,
            "3": ecodes.KEY_KP3,
            "4": ecodes.KEY_KP4,
            "5": ecodes.KEY_KP5,
            "6": ecodes.KEY_KP6,
            "7": ecodes.KEY_KP7,
            "8": ecodes.KEY_KP8,
            "LEFT": ecodes.KEY_LEFT,
            "RIGHT": ecodes.KEY_RIGHT,
            "UP": ecodes.KEY_UP,
            "DOWN": ecodes.KEY_DOWN,
        }
        capabilities = {ecodes.EV_KEY: list(self.key_map.values())}
        self.ui = UInput(capabilities, name="light-scroll-controller")

    def close(self) -> None:
        self.ui.close()

    def emit(self, event: str) -> None:
        key_code = self.key_map.get(event)
        if key_code is None:
            return

        self.ui.write(ecodes.EV_KEY, key_code, 1)
        self.ui.syn()
        time.sleep(self.key_hold)
        self.ui.write(ecodes.EV_KEY, key_code, 0)
        self.ui.syn()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send light-sensor gestures as Linux uinput keyboard events."
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
    parser.add_argument(
        "--key-hold",
        type=positive_float,
        default=0.03,
        help="Seconds to hold each virtual key press. Default: 0.03",
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
    adc = None
    keyboard = None

    try:
        adc = MCP3008(bus=args.bus, device=args.device, speed_hz=args.speed_hz)
        keyboard = UInputKeyboard(key_hold=args.key_hold)
        baseline, thresholds = calibrate(adc, config)
        detector = KeyboardGestureDetector(config, baseline, thresholds)
        print(
            "Virtual keyboard ready: 1..8 -> numpad keys, swipes -> arrow keys.",
            file=sys.stderr,
            flush=True,
        )

        while running:
            event = detector.observe(adc.read_all(), time.monotonic())
            if event is not None:
                keyboard.emit(event)
                print(f"EVENT {event}", file=sys.stderr, flush=True)
            time.sleep(config.interval)
    finally:
        if keyboard is not None:
            keyboard.close()
        if adc is not None:
            adc.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
