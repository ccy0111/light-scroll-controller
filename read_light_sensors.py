#!/usr/bin/env python3
"""
MCP3008로 조도 센서 8개 값을 실시간 확인하는 디버그용 코드.

메모:
- Raspberry Pi SPI를 켜야 함
- MCP3008은 3.3V 기준으로 사용
- 센서는 CH0..CH7에 연결

설치:
    python3 -m pip install spidev

실행:
    python3 read_light_sensors.py
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
import spidev
from dataclasses import dataclass


@dataclass(frozen=True)
class SensorReading:
    channel: int
    raw: int
    volts: float


class MCP3008:
    def __init__(self, bus: int = 0, device: int = 0, speed_hz: int = 1_000_000) -> None:
        if spidev is None:
            raise RuntimeError(
                "Missing dependency 'spidev'. Install it on the Raspberry Pi with: "
                "python3 -m pip install spidev"
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

        # MCP3008에서 10비트 ADC 값을 읽는다.
        response = self.spi.xfer2([1, (8 + channel) << 4, 0])
        return ((response[1] & 0x03) << 8) | response[2]


def clear_screen() -> None:
    sys.stdout.write("\033[2J\033[H")


def render(readings: list[SensorReading], interval: float, vref: float) -> None:
    clear_screen()
    print("Light Scroll Controller - live MCP3008 readings")
    print(f"Refresh: {interval:.3f}s | Vref: {vref:.2f}V | Ctrl+C to quit")
    print()
    print("2x4 sensor layout")
    print()

    for row_start in (0, 4):
        cells = []
        for reading in readings[row_start : row_start + 4]:
            bar = "#" * round(reading.raw / 1023 * 20)
            cells.append(
                f"CH{reading.channel}: {reading.raw:4d} "
                f"{reading.volts:5.3f}V [{bar:<20}]"
            )
        print("  ".join(cells))

    print()
    print("Raw order: " + " ".join(f"{reading.raw:4d}" for reading in readings))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read 8 light sensors connected to an MCP3008 ADC."
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
        type=float,
        default=0.05,
        help="Refresh interval in seconds. Default: 0.05",
    )
    parser.add_argument(
        "--vref",
        type=float,
        default=3.3,
        help="ADC reference voltage. Default: 3.3",
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

    adc = MCP3008(bus=args.bus, device=args.device, speed_hz=args.speed_hz)

    try:
        while running:
            readings = []
            for channel in range(8):
                raw = adc.read_channel(channel)
                volts = raw / 1023 * args.vref
                readings.append(SensorReading(channel=channel, raw=raw, volts=volts))

            render(readings, interval=args.interval, vref=args.vref)
            time.sleep(args.interval)
    finally:
        adc.close()
        print("\nStopped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
