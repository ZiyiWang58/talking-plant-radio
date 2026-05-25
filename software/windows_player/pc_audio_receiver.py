import json
import time
import winsound
from pathlib import Path

import paho.mqtt.client as mqtt

MQTT_HOST = "192.168.137.32"
MQTT_PORT = 1883

PLANT_ID = "plant1"

STATUS_TOPIC = f"talkingplant/{PLANT_ID}/status"
AUDIO_TOPIC = f"talkingplant/{PLANT_ID}/audio"

OUTPUT_DIR = Path("received_audio")
OUTPUT_DIR.mkdir(exist_ok=True)

def on_connect(client, userdata, flags, reason_code, properties=None):
    print("Connected to MQTT broker on Raspberry Pi.")
    client.subscribe(STATUS_TOPIC)
    client.subscribe(AUDIO_TOPIC)
    print("Waiting for plant status and audio...")

def on_message(client, userdata, msg):
    if msg.topic == STATUS_TOPIC:
        try:
            data = json.loads(msg.payload.decode("utf-8"))
            print("\n--- Plant Status ---")
            print(json.dumps(data, indent=2, ensure_ascii=False))
        except Exception as e:
            print("Could not decode status:", e)

    elif msg.topic == AUDIO_TOPIC:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"plant_voice_{timestamp}.wav"

        with open(output_path, "wb") as f:
            f.write(msg.payload)

        print(f"\nReceived audio: {output_path}")
        print("Playing...")

        try:
            winsound.PlaySound(str(output_path), winsound.SND_FILENAME)
            print("Finished playing.")
        except Exception as e:
            print("Playback failed:", e)

def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"Connecting to {MQTT_HOST}:{MQTT_PORT} ...")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()