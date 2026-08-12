# Hardware Documentation

This page records the main hardware used in the final TuneIn prototype. The
software expects one Raspberry Pi connected to four I2C environmental sensors,
with processed speech audio sent from the Raspberry Pi into a short-range AM
transmitter and received through a crystal-radio setup.

## Bill of Materials

| Component | Model / Specification | Quantity |
| --- | --- | ---: |
| Raspberry Pi | Raspberry Pi 4B | 1 |
| Soil moisture sensor | Adafruit STEMMA Soil Sensor, I2C capacitive moisture sensor | 1 |
| Temperature and humidity sensor | Adafruit SHT31-D Temperature & Humidity Sensor | 1 |
| Ambient light sensor | Adafruit VEML7700 Ambient Light Sensor, I2C lux sensor | 1 |
| Spectral sensor | AS7341 visible light spectral sensor | 1 |
| I2C wiring / jumper wires | I2C connection between sensors and Raspberry Pi | As required |
| 3.5 mm audio output | Raspberry Pi audio output to AM transmitter input | 1 |
| 1 MHz crystal oscillator | Fixed-frequency oscillator module | 1 |
| LM386 audio amplifier | Low-voltage audio power amplifier IC | 1 |
| Potentiometer | 10 kΩ potentiometer | 1 |
| Capacitor | 220 pF ceramic capacitor | 1 |
| Capacitor | 47 nF ceramic capacitor | 1 |
| Capacitor | 100 nF ceramic capacitor | 3 |
| Capacitor | 1 µF electrolytic capacitor pack | 1 |
| Capacitor | 10 µF electrolytic capacitor pack | 1 |
| Capacitor | 100 µF electrolytic capacitor pack | 1 |
| Capacitor | 220 µF electrolytic capacitor pack | 1 |
| Capacitor | 60 pF trimmer capacitor | 1 |
| Resistor | 10 Ω | 1 |
| Resistor | 220 Ω | 1 |
| Resistor | 4.7 kΩ | 1 |
| Resistor | 100 kΩ | 1 |
| Audio transformer | LT700 miniature audio transformer | 1 |
| RF transistor | 2N2222 NPN transistor | 1 |
| Transmitting coil | Hand-wound coil / loop tuned around the AM carrier frequency | 1 |
| Receiver coil | Tuned coil forming an LC circuit around 1 MHz | 1 |
| Tuning capacitor | Variable or fixed capacitor matched with receiver coil | 1 |
| Detector diode | Germanium diode | 1 |
| High-impedance earphone | High-impedance listening device or amplified audio input | 1 |
| Plant pot enclosure | Single prayer plant pot structure | 1 |
| Power supply | Raspberry Pi power adapter and circuit power supply | 1 |

## Sensor Addresses

| Sensor | Purpose | Address used by the software |
| --- | --- | ---: |
| Adafruit STEMMA soil sensor / Seesaw | Relative soil moisture | `0x36` |
| VEML7700 | Illuminance | `0x10` |
| SHT31-D | Temperature and humidity | `0x44` |
| AS7341 | Visible spectral composition | `0x39` |

All four sensors share the Raspberry Pi I2C bus using the standard SDA and SCL
pins. The final AM reception quality depended on coil placement, orientation,
tuning and nearby electronic interference, so the hand-wound coil and tuning
values should be verified against the final physical exhibit rather than
inferred from the software alone.
