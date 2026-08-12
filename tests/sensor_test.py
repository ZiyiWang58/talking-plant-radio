import time
import board

from adafruit_seesaw.seesaw import Seesaw
import adafruit_veml7700
import adafruit_sht31d

# Create the I2C bus.
i2c = board.I2C()

# Create sensor objects.
# 0x36 = soil sensor
# 0x10 = VEML7700 light sensor
# 0x44 = SHT31 temperature/humidity sensor
soil_sensor = Seesaw(i2c, addr=0x36)
light_sensor = adafruit_veml7700.VEML7700(i2c)
sht31 = adafruit_sht31d.SHT31D(i2c, address=0x44)

print("Reading sensors. Press Ctrl + C to stop.")

while True:
    soil_raw = soil_sensor.moisture_read()
    light_lux = light_sensor.lux
    temperature_c = sht31.temperature
    humidity = sht31.relative_humidity

    print("----------------------------")
    print(f"Soil moisture raw: {soil_raw}")
    print(f"Light: {light_lux:.2f} lux")
    print(f"Temperature: {temperature_c:.2f} °C")
    print(f"Humidity: {humidity:.2f} %")

    time.sleep(2)