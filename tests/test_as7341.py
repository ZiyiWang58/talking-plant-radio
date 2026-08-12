import time
import board
from adafruit_as7341 import AS7341

# Use Raspberry Pi default I2C pins: SDA=GPIO2, SCL=GPIO3
i2c = board.I2C()

# Create AS7341 sensor object
sensor = AS7341(i2c)

print("AS7341 detected. Reading spectral channels...")
print("Cover the sensor, shine a phone torch, or point it at different lights to test changes.\n")

while True:
    # Read visible spectrum channels and clear/NIR channels
    ch_415 = sensor.channel_415nm
    ch_445 = sensor.channel_445nm
    ch_480 = sensor.channel_480nm
    ch_515 = sensor.channel_515nm
    ch_555 = sensor.channel_555nm
    ch_590 = sensor.channel_590nm
    ch_630 = sensor.channel_630nm
    ch_680 = sensor.channel_680nm
    clear = sensor.channel_clear
    nir = sensor.channel_nir

    # Simple derived values for quick interpretation
    blue_part = ch_445 + ch_480
    green_part = ch_515 + ch_555
    red_part = ch_630 + ch_680

    print("------ AS7341 Reading ------")
    print(f"415nm violet: {ch_415}")
    print(f"445nm blue  : {ch_445}")
    print(f"480nm cyan  : {ch_480}")
    print(f"515nm green : {ch_515}")
    print(f"555nm green : {ch_555}")
    print(f"590nm yellow: {ch_590}")
    print(f"630nm red   : {ch_630}")
    print(f"680nm red   : {ch_680}")
    print(f"Clear       : {clear}")
    print(f"NIR         : {nir}")
    print(f"Blue sum    : {blue_part}")
    print(f"Green sum   : {green_part}")
    print(f"Red sum     : {red_part}")
    print()

    time.sleep(1)
