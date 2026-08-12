# Hardware documentation still required

The software expects four I²C sensors on the Raspberry Pi bus:

| Sensor | Purpose | Address used by the software |
| --- | --- | ---: |
| Adafruit STEMMA soil sensor / Seesaw | Relative soil moisture | `0x36` |
| VEML7700 | Illuminance | `0x10` (library default) |
| SHT31-D | Temperature and humidity | `0x44` |
| AS7341 | Visible spectral composition | `0x39` (library default) |

All four share the Raspberry Pi I²C SDA and SCL lines. Before claiming full
physical reproducibility, add the verified final-project materials below:

- complete bill of materials with exact component values and part numbers;
- labelled sensor wiring diagram and power connections;
- AM transmitter circuit schematic and audio-input connection;
- near-field coupling coil dimensions and winding instructions;
- crystal radio circuit, coil, tuning and earphone details;
- final enclosure, pot and mounting dimensions, with CAD/STL files if used;
- final assembly photographs and tested audio-level settings.

Do not infer the AM transmitter wiring from the software files. Add only the
schematic that matches the physical exhibit.
