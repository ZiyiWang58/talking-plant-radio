\# Talking Plant Radio



This project explores a talking plant interface using Raspberry Pi, environmental sensors, cloud-based text-to-speech, MQTT audio transfer, and later short-range AM radio transmission.



\## Current Prototype Status



The current working prototype can:



\- Read data from three I2C sensors:

&#x20; - SHT31 temperature and humidity sensor

&#x20; - VEML7700 light sensor

&#x20; - I2C soil moisture sensor

\- Convert sensor readings into simple plant-like language using rule-based logic

\- Generate speech using Microsoft Azure Speech

\- Send generated audio from Raspberry Pi to a Windows PC through MQTT

\- Play the received audio on the PC command line



\## Hardware Used So Far



\- Raspberry Pi 4 Model B

\- SHT31 temperature and humidity sensor

\- VEML7700 light sensor

\- I2C capacitive soil moisture sensor

\- Windows PC for temporary audio playback



\## Software Structure



```text

software/

├── raspberry\_pi/

│   ├── sensor\_test.py

│   ├── azure\_tts\_test.py

│   ├── plant\_pi\_controller.py

│   └── .env.example

└── windows\_player/

&#x20;   └── pc\_audio\_receiver.py



\## Notes



The .env file is not included in this repository because it contains the Azure Speech API key.



\## Next Steps

Replace the manual Enter-key trigger with an infrared proximity sensor

Add sensor data logging

Move playback from PC to Raspberry Pi local audio output

Connect Raspberry Pi audio output to an AM modulation circuit

Test short-range loop antenna transmission to a passive crystal radio receiver

