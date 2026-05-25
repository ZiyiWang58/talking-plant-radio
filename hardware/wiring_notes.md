\# Wiring Notes



\## Raspberry Pi I2C Pins



| Raspberry Pi Physical Pin | Function |

|---:|---|

| Pin 1 | 3.3V |

| Pin 3 | SDA / GPIO2 |

| Pin 5 | SCL / GPIO3 |

| Pin 6 | GND |



\## Sensor Connections



All three sensors share the same I2C bus.



| Sensor Pin | Raspberry Pi Pin |

|---|---|

| VIN | Pin 1 / 3.3V |

| GND | Pin 6 / GND |

| SDA | Pin 3 / SDA |

| SCL | Pin 5 / SCL |



\## I2C Addresses



| Device | Address |

|---|---|

| VEML7700 light sensor | `0x10` |

| I2C soil moisture sensor | `0x36` |

| SHT31 temperature/humidity sensor | `0x44` |



\## Important Note



Use 3.3V for I2C sensors with Raspberry Pi.

