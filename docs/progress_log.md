\# Progress Log



\## 2026-05-22



\### Completed



\- Connected Raspberry Pi 4 Model B to three I2C sensors.

\- Confirmed I2C detection:

&#x20; - `0x10` VEML7700 light sensor

&#x20; - `0x36` I2C soil moisture sensor

&#x20; - `0x44` SHT31 temperature and humidity sensor

\- Built a working software chain:

&#x20; - sensor reading on Raspberry Pi

&#x20; - rule-based plant language generation

&#x20; - Azure Speech text-to-speech generation

&#x20; - MQTT audio transfer

&#x20; - Windows command-line audio playback



\### Current Limitation



\- User trigger is currently simulated by pressing Enter in the Raspberry Pi terminal.

\- Audio playback is still handled by the Windows PC.

\- The AM modulation and loop antenna stage has not yet been integrated.



\### Next Step



Replace the manual Enter trigger with an infrared proximity sensor.

