import os
import json
import time
import csv
import subprocess
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


load_dotenv()

AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
AZURE_VOICE_NAME = os.getenv("AZURE_VOICE_NAME", "en-US-JennyNeural")

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
PLANT_ID = os.getenv("PLANT_ID", "plant1")
UPDATE_INTERVAL_SECONDS = int(os.getenv("UPDATE_INTERVAL_SECONDS", "60"))

# Keep MQTT during development so the PC can still display status/audio if needed.
ENABLE_MQTT = os.getenv("ENABLE_MQTT", "true").lower() == "true"

# Local playback is the new key function for the next prototype stage.
ENABLE_LOCAL_PLAYBACK = os.getenv("ENABLE_LOCAL_PLAYBACK", "true").lower() == "true"

STATUS_TOPIC = f"talkingplant/{PLANT_ID}/status"
AUDIO_TOPIC = f"talkingplant/{PLANT_ID}/audio"

AUDIO_FILE = Path("latest_plant_voice.wav")

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "broadcast_log.csv"


def setup_sensors():
    """Create I2C sensor objects."""
    i2c = board.I2C()
    soil_sensor = Seesaw(i2c, addr=0x36)
    light_sensor = adafruit_veml7700.VEML7700(i2c)
    sht31 = adafruit_sht31d.SHT31D(i2c, address=0x44)
    return soil_sensor, light_sensor, sht31


def read_sensors(soil_sensor, light_sensor, sht31):
    """Read all three sensors and return sensor readings."""
    return {
        "soil_raw": int(soil_sensor.moisture_read()),
        "light_lux": round(float(light_sensor.lux), 2),
        "temperature_c": round(float(sht31.temperature), 2),
        "humidity": round(float(sht31.relative_humidity), 2),
    }


def classify_soil(soil_raw):
    """Temporary soil thresholds. Calibrate these later for your actual plant and soil."""
    if soil_raw < 500:
        return "very dry"
    if soil_raw < 850:
        return "dry"
    if soil_raw < 1400:
        return "comfortable"
    return "wet"


def classify_light(light_lux):
    """Simple indoor light classification."""
    if light_lux < 100:
        return "very low"
    if light_lux < 500:
        return "low"
    if light_lux < 2000:
        return "comfortable"
    return "bright"


def classify_temperature(temperature_c):
    """Simple indoor temperature classification."""
    if temperature_c < 18:
        return "cool"
    if temperature_c > 26:
        return "warm"
    return "mild"


def classify_humidity(humidity):
    """Simple indoor humidity classification."""
    if humidity < 40:
        return "dry"
    if humidity > 70:
        return "humid"
    return "comfortable"


def build_plant_text(readings):
    """Rule-based first version of plant-language generation."""
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

    sentences.append("This is my scheduled radio message, sent from the plant pot at this moment.")

    states = {
        "soil_state": soil_state,
        "light_state": light_state,
        "temperature_state": temp_state,
        "humidity_state": humidity_state,
    }

    return " ".join(sentences), states


def synthesize_to_wav(text, output_file):
    """Use Azure Speech to save speech as a WAV file on the Raspberry Pi."""
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise RuntimeError("Missing Azure Speech key or region. Check .env.")

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )

    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
    )

    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_file))
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


def play_audio_locally(audio_file):
    """
    Play the generated WAV on the Raspberry Pi itself.

    This uses 'pw-play', a PipeWire-compatible command-line audio player.
    The playback blocks until the audio has finished.
    """
    if not audio_file.exists():
        print(f"Local playback skipped. File not found: {audio_file}")
        return False

    try:
        print(f"Playing locally on Raspberry Pi: {audio_file}")
        subprocess.run(["pw-play", str(audio_file)], check=True)
        print("Local playback finished.")
        return True
    except FileNotFoundError:
        print("Could not find 'pw-play'. Check PipeWire installation.")
        return False
    except subprocess.CalledProcessError as error:
        print("Local playback failed.")
        print(error)
        return False


def setup_mqtt():
    """Connect to the MQTT broker running on the Raspberry Pi."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    return client


def publish_status(client, status):
    """Send sensor readings and generated text to the PC."""
    client.publish(STATUS_TOPIC, json.dumps(status, ensure_ascii=False), qos=1)
    print("Published status.")


def publish_audio(client):
    """Send the latest WAV audio file to the PC through MQTT."""
    if not AUDIO_FILE.exists():
        print("No audio file found yet.")
        return False

    audio_bytes = AUDIO_FILE.read_bytes()
    client.publish(AUDIO_TOPIC, audio_bytes, qos=1)
    print(f"Published audio through MQTT: {AUDIO_FILE} ({len(audio_bytes)} bytes)")
    return True


def ensure_log_file():
    """Create the CSV log file and header if it does not already exist."""
    LOG_DIR.mkdir(exist_ok=True)

    if LOG_FILE.exists():
        return

    fieldnames = [
        "timestamp",
        "plant_id",
        "soil_raw",
        "light_lux",
        "temperature_c",
        "humidity",
        "soil_state",
        "light_state",
        "temperature_state",
        "humidity_state",
        "generated_text",
        "audio_file",
        "audio_generated",
        "audio_sent_mqtt",
        "audio_played_locally",
    ]

    with LOG_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

    print(f"Created log file: {LOG_FILE}")


def append_broadcast_log(status, audio_generated, audio_sent_mqtt, audio_played_locally):
    """Append one broadcast record to the CSV log."""
    ensure_log_file()

    readings = status["readings"]
    states = status["states"]

    row = {
        "timestamp": status["timestamp"],
        "plant_id": status["plant_id"],
        "soil_raw": readings["soil_raw"],
        "light_lux": readings["light_lux"],
        "temperature_c": readings["temperature_c"],
        "humidity": readings["humidity"],
        "soil_state": states["soil_state"],
        "light_state": states["light_state"],
        "temperature_state": states["temperature_state"],
        "humidity_state": states["humidity_state"],
        "generated_text": status["text"],
        "audio_file": status["audio_file"],
        "audio_generated": audio_generated,
        "audio_sent_mqtt": audio_sent_mqtt,
        "audio_played_locally": audio_played_locally,
    }

    with LOG_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=row.keys())
        writer.writerow(row)

    print(f"Appended broadcast log: {LOG_FILE}")


def scheduled_broadcast_loop(client, sensors):
    """Automatically broadcast once every UPDATE_INTERVAL_SECONDS."""
    soil_sensor, light_sensor, sht31 = sensors

    while True:
        cycle_started = datetime.now()
        audio_generated = False
        audio_sent_mqtt = False
        audio_played_locally = False
        status = None

        try:
            print("\\n------------------------------")
            print("Scheduled plant broadcast")
            print(cycle_started.strftime("%Y-%m-%d %H:%M:%S"))

            readings = read_sensors(soil_sensor, light_sensor, sht31)
            text, states = build_plant_text(readings)

            status = {
                "plant_id": PLANT_ID,
                "timestamp": cycle_started.isoformat(timespec="seconds"),
                "readings": readings,
                "states": states,
                "text": text,
                "audio_file": str(AUDIO_FILE),
            }

            print("Readings:")
            print(json.dumps(readings, indent=2))
            print("Generated text:")
            print(text)

            audio_generated = synthesize_to_wav(text, AUDIO_FILE)

            if audio_generated:
                print(f"Audio saved: {AUDIO_FILE}")

                if ENABLE_MQTT and client is not None:
                    publish_status(client, status)
                    audio_sent_mqtt = publish_audio(client)

                if ENABLE_LOCAL_PLAYBACK:
                    audio_played_locally = play_audio_locally(AUDIO_FILE)
            else:
                print("Audio generation failed. Nothing was played or sent.")

        except Exception as e:
            print("Error during scheduled broadcast:", e)

        if status is not None:
            append_broadcast_log(
                status=status,
                audio_generated=audio_generated,
                audio_sent_mqtt=audio_sent_mqtt,
                audio_played_locally=audio_played_locally
            )

        print(f"Waiting {UPDATE_INTERVAL_SECONDS} seconds before next scheduled broadcast...")
        time.sleep(UPDATE_INTERVAL_SECONDS)


def main():
    print("Starting Talking Plant automatic broadcast controller with local playback...")
    print(f"Broadcast interval: {UPDATE_INTERVAL_SECONDS} seconds")
    print(f"MQTT enabled: {ENABLE_MQTT}")
    print(f"Local playback enabled: {ENABLE_LOCAL_PLAYBACK}")

    ensure_log_file()

    print("Setting up sensors...")
    sensors = setup_sensors()
    print("Sensors ready.")

    mqtt_client = None
    if ENABLE_MQTT:
        print("Connecting to MQTT broker...")
        mqtt_client = setup_mqtt()
        print("MQTT connected.")

    try:
        scheduled_broadcast_loop(mqtt_client, sensors)
    except KeyboardInterrupt:
        print("\\nStopping...")
    finally:
        if mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()


if __name__ == "__main__":
    main()
