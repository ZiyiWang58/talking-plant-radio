import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

from dotenv import load_dotenv

import board
from adafruit_seesaw.seesaw import Seesaw
import adafruit_veml7700
import adafruit_sht31d

import paho.mqtt.client as mqtt
import azure.cognitiveservices.speech as speechsdk


# -----------------------------
# Load settings from .env
# -----------------------------

load_dotenv()

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
AZURE_VOICE_NAME = os.getenv("AZURE_VOICE_NAME", "en-US-JennyNeural")

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
PLANT_ID = os.getenv("PLANT_ID", "plant1")
UPDATE_INTERVAL_SECONDS = int(os.getenv("UPDATE_INTERVAL_SECONDS", "60"))

STATUS_TOPIC = f"talkingplant/{PLANT_ID}/status"
AUDIO_TOPIC = f"talkingplant/{PLANT_ID}/audio"

AUDIO_FILE = Path("latest_plant_voice.wav")

audio_lock = threading.Lock()


# -----------------------------
# Sensor setup and reading
# -----------------------------

def setup_sensors():
    """Create I2C sensor objects."""
    i2c = board.I2C()

    soil_sensor = Seesaw(i2c, addr=0x36)
    light_sensor = adafruit_veml7700.VEML7700(i2c)
    sht31 = adafruit_sht31d.SHT31D(i2c, address=0x44)

    return soil_sensor, light_sensor, sht31


def read_sensors(soil_sensor, light_sensor, sht31):
    """Read all three sensors and return raw values."""
    soil_raw = soil_sensor.moisture_read()
    light_lux = light_sensor.lux
    temperature_c = sht31.temperature
    humidity = sht31.relative_humidity

    return {
        "soil_raw": int(soil_raw),
        "light_lux": round(float(light_lux), 2),
        "temperature_c": round(float(temperature_c), 2),
        "humidity": round(float(humidity), 2),
    }


# -----------------------------
# Convert sensor data to language
# -----------------------------

def classify_soil(soil_raw):
    """
    Temporary thresholds.
    Later you should calibrate dry soil and wet soil for your specific sensor.
    """
    if soil_raw < 500:
        return "very dry"
    elif soil_raw < 850:
        return "dry"
    elif soil_raw < 1400:
        return "comfortable"
    else:
        return "wet"


def classify_light(light_lux):
    """Simple indoor light classification."""
    if light_lux < 100:
        return "very low"
    elif light_lux < 500:
        return "low"
    elif light_lux < 2000:
        return "comfortable"
    else:
        return "bright"


def classify_temperature(temperature_c):
    """Simple indoor temperature classification."""
    if temperature_c < 18:
        return "cool"
    elif temperature_c > 26:
        return "warm"
    else:
        return "mild"


def classify_humidity(humidity):
    """Simple indoor humidity classification."""
    if humidity < 40:
        return "dry"
    elif humidity > 70:
        return "humid"
    else:
        return "comfortable"


def build_plant_text(readings):
    """
    This is the first version of 'plant language'.
    It uses rules, not a real LLM yet.
    Later this function can be replaced by Azure OpenAI / Qwen / another LLM.
    """
    soil_state = classify_soil(readings["soil_raw"])
    light_state = classify_light(readings["light_lux"])
    temp_state = classify_temperature(readings["temperature_c"])
    humidity_state = classify_humidity(readings["humidity"])

    sentences = []

    if soil_state == "very dry":
        sentences.append("My soil is very dry. My roots feel tired, and I would like water soon.")
    elif soil_state == "dry":
        sentences.append("My soil is getting dry. I can still wait, but I am beginning to feel thirsty.")
    elif soil_state == "comfortable":
        sentences.append("My soil feels balanced today. I feel steady and comfortable.")
    else:
        sentences.append("My soil feels quite wet. My roots feel heavy.")

    if light_state == "very low":
        sentences.append("The light around me is very weak, so I feel quiet and a little hidden.")
    elif light_state == "low":
        sentences.append("The light is soft, but I would feel better closer to the window.")
    elif light_state == "comfortable":
        sentences.append("The light feels gentle on my leaves.")
    else:
        sentences.append("The light is bright today, and I can feel it strongly on my leaves.")

    if temp_state == "cool":
        sentences.append("The air feels a little cool around me.")
    elif temp_state == "warm":
        sentences.append("The air feels warm around me.")
    else:
        sentences.append("The temperature around me feels mild.")

    if humidity_state == "dry":
        sentences.append("The air feels dry, and I notice it on my leaves.")
    elif humidity_state == "humid":
        sentences.append("The air feels damp and heavy.")
    else:
        sentences.append("The air around me feels calm.")

    sentences.append("You are close enough to listen now, so I am sharing this small condition with you.")

    text = " ".join(sentences)

    states = {
        "soil_state": soil_state,
        "light_state": light_state,
        "temperature_state": temp_state,
        "humidity_state": humidity_state,
    }

    return text, states


# -----------------------------
# Azure text-to-speech
# -----------------------------

def synthesize_to_wav(text, output_file):
    """Use Azure Speech to save speech as a WAV file on the Raspberry Pi."""
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise RuntimeError("Missing Azure Speech key or region. Check .env.")

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )

    # Smaller WAV, easier to send via MQTT.
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
    )

    audio_config = speechsdk.audio.AudioOutputConfig(
        filename=str(output_file)
    )

    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    safe_text = escape(text)

    ssml = f"""
    <speak version="1.0" xml:lang="en-US">
      <voice name="{AZURE_VOICE_NAME}">
        <prosody rate="-8%" pitch="-2%">
          {safe_text}
        </prosody>
      </voice>
    </speak>
    """

    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True

    if result.reason == speechsdk.ResultReason.Canceled:
        details = result.cancellation_details
        print("Azure TTS canceled.")
        print("Reason:", details.reason)
        print("Error details:", details.error_details)

    return False


# -----------------------------
# MQTT
# -----------------------------

def setup_mqtt():
    """Connect to the MQTT broker running on the Raspberry Pi."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    return client


def publish_status(client, status):
    payload = json.dumps(status, ensure_ascii=False)
    client.publish(STATUS_TOPIC, payload, qos=1)
    print("Published status.")


def publish_audio(client):
    if not AUDIO_FILE.exists():
        print("No audio file found yet.")
        return

    with audio_lock:
        audio_bytes = AUDIO_FILE.read_bytes()

    client.publish(AUDIO_TOPIC, audio_bytes, qos=1)
    print(f"Published audio: {AUDIO_FILE} ({len(audio_bytes)} bytes)")


# -----------------------------
# Main loops
# -----------------------------

def update_voice_loop(client, sensors):
    """Periodically update the cached plant voice."""
    soil_sensor, light_sensor, sht31 = sensors

    while True:
        try:
            print("\n------------------------------")
            print("Updating plant voice...")
            print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            readings = read_sensors(soil_sensor, light_sensor, sht31)
            text, states = build_plant_text(readings)

            status = {
                "plant_id": PLANT_ID,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "readings": readings,
                "states": states,
                "text": text,
            }

            print("Readings:")
            print(json.dumps(readings, indent=2))
            print("Generated text:")
            print(text)

            with audio_lock:
                ok = synthesize_to_wav(text, AUDIO_FILE)

            if ok:
                print(f"Audio saved: {AUDIO_FILE}")
                publish_status(client, status)
            else:
                print("Audio generation failed.")

        except Exception as e:
            print("Error while updating voice:", e)

        print(f"Waiting {UPDATE_INTERVAL_SECONDS} seconds before next update...")
        time.sleep(UPDATE_INTERVAL_SECONDS)


def trigger_loop(client):
    """
    First prototype trigger:
    Press Enter in the Raspberry Pi terminal to send the latest audio to the PC.

    Later, this will be replaced by an infrared sensor trigger.
    """
    while True:
        input("\nPress Enter to simulate user approaching the plant...")
        publish_audio(client)


def main():
    print("Starting Talking Plant controller...")

    print("Setting up sensors...")
    sensors = setup_sensors()
    print("Sensors ready.")

    print("Connecting to MQTT...")
    mqtt_client = setup_mqtt()
    print("MQTT connected.")

    voice_thread = threading.Thread(
        target=update_voice_loop,
        args=(mqtt_client, sensors),
        daemon=True
    )

    trigger_thread = threading.Thread(
        target=trigger_loop,
        args=(mqtt_client,),
        daemon=True
    )

    voice_thread.start()
    trigger_thread.start()

    print("System is running.")
    print("Keep this terminal open.")
    print("Press Ctrl + C to stop.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()