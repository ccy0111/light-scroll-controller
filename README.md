# Light Scroll Controller

Raspberry Pi 4, MCP3008 ADC, and GL5537 CdS light sensor based non-contact
controller.

The first step is to read an 8-channel light sensor array in real time. Later
steps can use the measured light offset pattern to detect swipe, tap, and hold
gestures.

## Hardware

- Raspberry Pi 4
- MCP3008 ADC
- GL5537 CdS light sensors x 8
- 10k ohm resistors x 8, for voltage dividers
- Breadboard and jumper wires

## Pin Layout

Use Raspberry Pi physical pin numbers when wiring. GPIO numbers are included
for reference.

### Breadboard Power Rails

Use breadboard power rails to distribute shared power and ground.

Recommended rail layout:

```text
Breadboard left + rail   -> 3.3V rail for MCP3008 and light sensors
Breadboard left - rail   -> GND rail

Breadboard right + rail  -> 5V rail, currently unused and reserved for expansion
Breadboard right - rail  -> GND rail
```

Connect both breadboard GND rails together. All modules must share the same
ground. The current MCP3008/light sensor circuit does not require 5V, but
keeping a separate 5V rail is useful for later modules. Keep it isolated from
the 3.3V rail.

```text
Raspberry Pi physical pin 1 or 17 -> breadboard 3.3V rail
Raspberry Pi physical pin 2 or 4  -> breadboard 5V rail, optional for expansion
Raspberry Pi physical pin 25      -> breadboard GND rail

breadboard 3.3V rail -> MCP3008 VDD, MCP3008 VREF, GL5537 sensor inputs
breadboard 5V rail   -> currently unused
breadboard GND rail  -> MCP3008 AGND/DGND, sensor resistors
```

Keep the 3.3V rail and 5V rail separate. Do not connect 5V to the MCP3008 or
to Raspberry Pi GPIO pins.

### Power and Ground

```text
Raspberry Pi 4        Target
--------------        ------
3.3V pin 1 or 17  ->  breadboard 3.3V rail
5V pin 2 or 4     ->  breadboard 5V rail, optional for expansion
GND pin 25        ->  breadboard GND rail

breadboard 3.3V   ->  MCP3008 VDD pin 16
breadboard 3.3V   ->  MCP3008 VREF pin 15
breadboard 3.3V   ->  GL5537 sensor voltage dividers

breadboard 5V     ->  currently unused

breadboard GND    ->  MCP3008 AGND pin 14
breadboard GND    ->  MCP3008 DGND pin 9
breadboard GND    ->  GL5537 sensor divider resistors
```

Keep the MCP3008 on 3.3V. Do not power the MCP3008 from 5V because Raspberry Pi
GPIO pins are not 5V tolerant.

### MCP3008 to Raspberry Pi 4

```text
MCP3008          Raspberry Pi 4
-------          --------------
VDD  pin 16  ->  3.3V   breadboard 3.3V rail
VREF pin 15  ->  3.3V   breadboard 3.3V rail
AGND pin 14  ->  GND    breadboard GND rail
DGND pin 9   ->  GND    breadboard GND rail

CLK  pin 13  ->  GPIO11 / SCLK  physical pin 23
DOUT pin 12  ->  GPIO9  / MISO  physical pin 21
DIN  pin 11  ->  GPIO10 / MOSI  physical pin 19
CS   pin 10  ->  GPIO8  / CE0   physical pin 24
```

### Light Sensors to MCP3008

Connect each GL5537 sensor as a voltage divider.

```text
3.3V
 |
[GL5537]
 |
 +----> MCP3008 CHx
 |
[10k ohm resistor]
 |
GND
```

With this layout, brighter light gives a higher ADC value and shadow gives a
lower ADC value.

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

Recommended 2x4 physical layout:

```text
CH0  CH1  CH2  CH3
CH4  CH5  CH6  CH7
```

## GPIO Summary

```text
MCP3008 SPI0:
GPIO8, GPIO9, GPIO10, GPIO11
```

Only the SPI0 pins are required for the current MCP3008/light sensor circuit.

## Raspberry Pi Setup

Enable SPI:

```bash
sudo raspi-config
```

```text
Interface Options -> SPI -> Enable
```

Reboot after enabling SPI:

```bash
sudo reboot
```

Install the Python SPI dependency:

```bash
sudo apt update
sudo apt install -y python3-spidev
```

Run the live sensor reader:

```bash
python3 read_light_sensors.py
```

If everything is wired correctly, covering a sensor should change the matching
`CH0` to `CH7` value in real time.
