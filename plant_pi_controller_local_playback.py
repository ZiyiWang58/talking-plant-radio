import os
import json
import time
import csv
import subprocess
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

from dotenv import load_dotenv
from openai import OpenAI

import board
from adafruit_seesaw.seesaw import Seesaw
import adafruit_veml7700
import adafruit_sht31d
from adafruit_as7341 import AS7341

import paho.mqtt.client as mqtt
import azure.cognitiveservices.speech as speechsdk


# Resolve all generated files relative to this script so the repository can be
# cloned anywhere without depending on the caller's working directory.
APP_DIR = Path(__file__).resolve().parent
load_dotenv(APP_DIR / ".env")

# Azure Speech / TTS
AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")
AZURE_VOICE_NAME = os.getenv("AZURE_VOICE_NAME", "en-US-JennyNeural")

# Azure OpenAI / LLM
ENABLE_LLM = os.getenv("ENABLE_LLM", "true").lower() == "true"
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
LLM_MAX_WORDS = int(os.getenv("LLM_MAX_WORDS", "24"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "12"))

# Plant profile
# Prayer plant usually means Maranta leuconeura.
# It prefers warm stable air, higher humidity, evenly moist soil, and bright indirect light.
PLANT_SPECIES = os.getenv("PLANT_SPECIES", "prayer plant / Maranta leuconeura")

# Temporary raw thresholds for the Adafruit Seesaw capacitive soil sensor.
# These are intentionally adjustable in .env, because soil readings depend on the exact pot,
# soil mix, sensor depth, and watering condition.
# Higher raw value normally means wetter soil.
PRAYER_SOIL_VERY_DRY_RAW = int(os.getenv("PRAYER_SOIL_VERY_DRY_RAW", "650"))
PRAYER_SOIL_DRY_RAW = int(os.getenv("PRAYER_SOIL_DRY_RAW", "1000"))
PRAYER_SOIL_MOIST_RAW = int(os.getenv("PRAYER_SOIL_MOIST_RAW", "1450"))
PRAYER_SOIL_WET_RAW = int(os.getenv("PRAYER_SOIL_WET_RAW", "1850"))


# MQTT and playback
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
PLANT_ID = os.getenv("PLANT_ID", "plant1")
UPDATE_INTERVAL_SECONDS = int(os.getenv("UPDATE_INTERVAL_SECONDS", "30"))
ENABLE_MQTT = os.getenv("ENABLE_MQTT", "false").lower() == "true"
ENABLE_LOCAL_PLAYBACK = os.getenv("ENABLE_LOCAL_PLAYBACK", "true").lower() == "true"

STATUS_TOPIC = f"talkingplant/{PLANT_ID}/status"
AUDIO_TOPIC = f"talkingplant/{PLANT_ID}/audio"

RAW_AUDIO_FILE = APP_DIR / "latest_plant_voice_raw.wav"
AUDIO_FILE = APP_DIR / "latest_plant_voice.wav"
LOG_DIR = APP_DIR / "logs"
LOG_FILE = LOG_DIR / "broadcast_log.csv"

LOG_FIELDNAMES = [
    "timestamp",
    "plant_id",
    "soil_raw",
    "light_lux",
    "temperature_c",
    "humidity",
    "spectral_visible_total",
    "spectral_clear",
    "spectral_nir",
    "spectral_blue_ratio",
    "spectral_green_ratio",
    "spectral_red_ratio",
    "soil_state",
    "light_state",
    "spectral_light_state",
    "temperature_state",
    "humidity_state",
    "text_source",
    "llm_error",
    "generated_text",
    "audio_file",
    "audio_generated",
    "audio_sent_mqtt",
    "audio_played_locally",
]


def setup_sensors():
    """Create all I2C sensor objects."""
    i2c = board.I2C()

    soil_sensor = Seesaw(i2c, addr=0x36)
    light_sensor = adafruit_veml7700.VEML7700(i2c)
    sht31 = adafruit_sht31d.SHT31D(i2c, address=0x44)
    spectral_sensor = AS7341(i2c)

    return soil_sensor, light_sensor, sht31, spectral_sensor


def read_sensors(soil_sensor, light_sensor, sht31, spectral_sensor):
    """Read all sensors and return one dictionary."""
    ch_415 = int(spectral_sensor.channel_415nm)
    ch_445 = int(spectral_sensor.channel_445nm)
    ch_480 = int(spectral_sensor.channel_480nm)
    ch_515 = int(spectral_sensor.channel_515nm)
    ch_555 = int(spectral_sensor.channel_555nm)
    ch_590 = int(spectral_sensor.channel_590nm)
    ch_630 = int(spectral_sensor.channel_630nm)
    ch_680 = int(spectral_sensor.channel_680nm)
    clear = int(spectral_sensor.channel_clear)
    nir = int(spectral_sensor.channel_nir)

    blue_sum = ch_445 + ch_480
    green_sum = ch_515 + ch_555
    red_sum = ch_630 + ch_680
    visible_total = (
        ch_415 + ch_445 + ch_480 + ch_515
        + ch_555 + ch_590 + ch_630 + ch_680
    )

    if visible_total > 0:
        blue_ratio = round(blue_sum / visible_total, 3)
        green_ratio = round(green_sum / visible_total, 3)
        red_ratio = round(red_sum / visible_total, 3)
    else:
        blue_ratio = 0
        green_ratio = 0
        red_ratio = 0

    return {
        "soil_raw": int(soil_sensor.moisture_read()),
        "light_lux": round(float(light_sensor.lux), 2),
        "temperature_c": round(float(sht31.temperature), 2),
        "humidity": round(float(sht31.relative_humidity), 2),
        "spectral_415nm": ch_415,
        "spectral_445nm": ch_445,
        "spectral_480nm": ch_480,
        "spectral_515nm": ch_515,
        "spectral_555nm": ch_555,
        "spectral_590nm": ch_590,
        "spectral_630nm": ch_630,
        "spectral_680nm": ch_680,
        "spectral_clear": clear,
        "spectral_nir": nir,
        "spectral_visible_total": visible_total,
        "spectral_blue_sum": blue_sum,
        "spectral_green_sum": green_sum,
        "spectral_red_sum": red_sum,
        "spectral_blue_ratio": blue_ratio,
        "spectral_green_ratio": green_ratio,
        "spectral_red_ratio": red_ratio,
    }


def classify_soil(soil_raw):
    """
    Prayer plant soil interpretation.

    Prayer plants should not dry out completely. This makes the program
    complain earlier than a generic drought-tolerant plant.
    Adjust PRAYER_SOIL_* values in .env after real calibration.
    """
    if soil_raw < PRAYER_SOIL_VERY_DRY_RAW:
        return "very dry for a prayer plant"
    if soil_raw < PRAYER_SOIL_DRY_RAW:
        return "slightly dry for a prayer plant"
    if soil_raw < PRAYER_SOIL_MOIST_RAW:
        return "comfortably moist"
    if soil_raw < PRAYER_SOIL_WET_RAW:
        return "wet"
    return "too wet or waterlogged"


def classify_light(light_lux):
    """Prayer plant light interpretation based on approximate indoor lux."""
    if light_lux < 300:
        return "too dim for a prayer plant"
    if light_lux < 800:
        return "low indirect light"
    if light_lux < 6500:
        return "bright indirect light"
    if light_lux < 10000:
        return "very bright light"
    return "too bright or possibly direct sun"


def classify_spectral_light(readings):
    visible_total = readings["spectral_visible_total"]
    clear = readings["spectral_clear"]
    blue_ratio = readings["spectral_blue_ratio"]
    green_ratio = readings["spectral_green_ratio"]
    red_ratio = readings["spectral_red_ratio"]

    if visible_total < 50 or clear < 50:
        return "too dim to judge"
    if blue_ratio > red_ratio + 0.06:
        return "cool and bluish"
    if red_ratio > blue_ratio + 0.06:
        return "warm and reddish"
    if green_ratio > blue_ratio and green_ratio > red_ratio:
        return "green balanced"
    return "mixed and balanced"


def classify_temperature(temperature_c):
    """Prayer plant temperature interpretation in degrees Celsius."""
    if temperature_c < 15:
        return "cold stress for a prayer plant"
    if temperature_c < 18:
        return "a little cool for a prayer plant"
    if temperature_c <= 27:
        return "comfortable warmth"
    if temperature_c <= 30:
        return "rather warm"
    return "too hot"


def classify_humidity(humidity):
    """Prayer plant humidity interpretation in relative humidity percent."""
    if humidity < 40:
        return "very dry air for a prayer plant"
    if humidity < 55:
        return "slightly dry air for a prayer plant"
    if humidity <= 75:
        return "comfortable humid air"
    if humidity <= 85:
        return "very humid air"
    return "too damp"


def build_rule_based_text(readings):
    """
    Build the original preset speech and the interpreted sensor states.

    This text is the offline fallback if Azure OpenAI is unavailable.
    """
    soil_state = classify_soil(readings["soil_raw"])
    light_state = classify_light(readings["light_lux"])
    spectral_light_state = classify_spectral_light(readings)
    temperature_state = classify_temperature(readings["temperature_c"])
    humidity_state = classify_humidity(readings["humidity"])

    sentences = []

    if soil_state == "very dry for a prayer plant":
        sentences.append(
            "My soil has become too dry for my prayer plant roots. I would like water soon."
        )
    elif soil_state == "slightly dry for a prayer plant":
        sentences.append(
            "My soil is beginning to dry, and I am starting to feel thirsty."
        )
    elif soil_state == "comfortably moist":
        sentences.append(
            "My soil feels softly moist, which helps me feel settled."
        )
    elif soil_state == "wet":
        sentences.append(
            "My soil is wet now. I do not need more water yet."
        )
    else:
        sentences.append(
            "My soil feels too wet and heavy around my roots."
        )

    if light_state == "too dim for a prayer plant":
        sentences.append(
            "The light is too dim, and my patterned leaves would like brighter indirect light."
        )
    elif light_state == "low indirect light":
        sentences.append(
            "The light is gentle but a little low for me."
        )
    elif light_state == "bright indirect light":
        sentences.append(
            "The light feels bright but gentle, like a good place for my leaves."
        )
    elif light_state == "very bright light":
        sentences.append(
            "The light is strong today, so I hope it stays soft and indirect."
        )
    else:
        sentences.append(
            "The light feels too intense, and my leaves may prefer shade from direct sun."
        )

    if spectral_light_state == "too dim to judge":
        sentences.append(
            "The light is too dim for me to clearly sense its colour."
        )
    elif spectral_light_state == "cool and bluish":
        sentences.append(
            "The light has a cooler, bluer quality today."
        )
    elif spectral_light_state == "warm and reddish":
        sentences.append(
            "The light feels warmer and redder, as if the room has shifted in tone."
        )
    elif spectral_light_state == "green balanced":
        sentences.append("The light has a softer green balance around me.")
    else:
        sentences.append("The colour of the light feels balanced and mixed.")

    if temperature_state == "cold stress for a prayer plant":
        sentences.append("The air feels too cold for me.")
    elif temperature_state == "a little cool for a prayer plant":
        sentences.append("The air feels a little cool for my tropical leaves.")
    elif temperature_state == "comfortable warmth":
        sentences.append("The temperature feels comfortably warm and steady.")
    elif temperature_state == "rather warm":
        sentences.append("The air feels rather warm around me.")
    else:
        sentences.append("The air feels too hot, and I would like a calmer place.")

    if humidity_state == "very dry air for a prayer plant":
        sentences.append("The air is very dry, and my leaves feel it quickly.")
    elif humidity_state == "slightly dry air for a prayer plant":
        sentences.append("The air is a little dry for me, though I can still manage.")
    elif humidity_state == "comfortable humid air":
        sentences.append("The humidity feels kind to my leaves.")
    elif humidity_state == "very humid air":
        sentences.append("The air feels very humid and heavy.")
    else:
        sentences.append("The air feels too damp and still around me.")

    states = {
        "soil_state": soil_state,
        "light_state": light_state,
        "spectral_light_state": spectral_light_state,
        "temperature_state": temperature_state,
        "humidity_state": humidity_state,
    }

    return " ".join(sentences), states


def generate_plant_text_with_llm(readings, states):
    """Generate the primary plant speech using Azure OpenAI."""
    if not AZURE_OPENAI_ENDPOINT:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT is missing.")
    if not AZURE_OPENAI_API_KEY:
        raise RuntimeError("AZURE_OPENAI_API_KEY is missing.")
    if not AZURE_OPENAI_DEPLOYMENT:
        raise RuntimeError("AZURE_OPENAI_DEPLOYMENT is missing.")

    client = OpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        base_url=AZURE_OPENAI_ENDPOINT,
        timeout=LLM_TIMEOUT_SECONDS,
        max_retries=0,
    )

    system_prompt = (
        "You are the voice of a prayer plant, Maranta leuconeura, "
        "inside a talking plant pot in an art and design exhibition. "
        "Interpret the live readings through prayer plant preferences: "
        "evenly moist but not soggy soil, warm stable air, higher humidity, "
        "and bright indirect light rather than harsh direct sun. "
        "Write speech for transmission over a noisy AM radio link. "
        "Use one or two very short first-person sentences. "
        "Keep each sentence under twelve words. "
        "Use common words and direct sentence structure. "
        "Use a full stop between sentences. "
        "Avoid semicolons, dashes, parentheses, abbreviations, numbers, "
        "technical labels, greetings, quotation marks, and uncommon poetic words. "
        "Mention only one or two of the most meaningful current conditions. "
        "Do not claim that the plant is truly conscious. "
        "Do not invent measurements or conditions that were not provided. "
        f"Use no more than {LLM_MAX_WORDS} words. "
        "Output only the plant's spoken message."
    )

    user_prompt = f"""
Plant species: {PLANT_SPECIES}

Current live readings:
- Soil moisture raw value: {readings["soil_raw"]}
- Soil condition: {states["soil_state"]}
- Light intensity: {readings["light_lux"]} lux
- Light condition: {states["light_state"]}
- Spectral light condition: {states["spectral_light_state"]}
- Blue spectral ratio: {readings["spectral_blue_ratio"]}
- Green spectral ratio: {readings["spectral_green_ratio"]}
- Red spectral ratio: {readings["spectral_red_ratio"]}
- Air temperature: {readings["temperature_c"]} degrees Celsius
- Temperature condition: {states["temperature_state"]}
- Relative humidity: {readings["humidity"]} percent
- Humidity condition: {states["humidity_state"]}

Write one short plant voice message.
""".strip()

    response = client.chat.completions.create(
        model=AZURE_OPENAI_DEPLOYMENT,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
        max_tokens=120,
    )

    text = (response.choices[0].message.content or "").strip()
    if not text:
        raise RuntimeError("Azure OpenAI returned an empty response.")

    return text


def choose_plant_text(readings):
    """
    Use Azure OpenAI as the primary generator.

    If LLM is disabled, misconfigured, offline, timed out, or returns an error,
    immediately use the original rule-based preset speech.
    """
    fallback_text, states = build_rule_based_text(readings)

    if not ENABLE_LLM:
        print("LLM disabled; using preset fallback speech.")
        return fallback_text, states, "rule_fallback", "LLM disabled"

    try:
        llm_text = generate_plant_text_with_llm(readings, states)
        return llm_text, states, "azure_llm", ""
    except Exception as error:
        error_message = f"{type(error).__name__}: {error}"
        print("Azure LLM unavailable; using preset fallback speech.")
        print("LLM error:", error_message)
        return fallback_text, states, "rule_fallback", error_message


def synthesize_to_wav(text, output_file):
    """Use Azure Speech to save the selected text as a WAV file."""
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        raise RuntimeError("Missing Azure Speech key or region. Check .env.")

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION,
    )

    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
    )

    audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_file))
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config,
    )

    safe_text = escape(text.strip())

    # Insert a short pause between sentences for better AM intelligibility.
    ssml_text = safe_text.replace(
        ". ",
        '.<break time="250ms"/> ',
    )

    ssml = f"""
    <speak version="1.0" xml:lang="en-US">
      <voice name="{AZURE_VOICE_NAME}">
        <prosody rate="-10%" pitch="0%">
          {ssml_text}
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



def process_audio_for_am(input_file, output_file):
    """Convert Azure TTS audio into AM-oriented narrow-band speech."""

    input_path = Path(input_file)
    output_path = Path(output_file)

    # Verify that Azure TTS produced the original audio file.
    if not input_path.exists():
        print(f"AM processing skipped. Input file not found: {input_path}")
        return False

    # Restrict the signal to the main speech-frequency range.
    # Compression improves word consistency and loudness normalisation
    # leaves sufficient headroom to reduce clipping and overmodulation.
    audio_filter = (
        "highpass=f=300,"
        "lowpass=f=3200,"
        "acompressor="
        "threshold=0.125:"
        "ratio=4:"
        "attack=10:"
        "release=100:"
        "makeup=2,"
        "loudnorm=I=-20:TP=-4:LRA=6"
    )

    # Build the FFmpeg command using fixed output settings.
    command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-af",
        audio_filter,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]

    try:
        # Run FFmpeg and capture error output for troubleshooting.
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        print(f"AM audio saved: {output_path}")
        return True

    except FileNotFoundError:
        print("FFmpeg was not found. Run: sudo apt install -y ffmpeg")
        return False

    except subprocess.CalledProcessError as error:
        print("FFmpeg AM audio processing failed.")
        print(error.stderr)
        return False

def play_audio_locally(audio_file):
    """Play the generated WAV through PipeWire and the Pi analogue output."""
    if not audio_file.exists():
        print(f"Local playback skipped. File not found: {audio_file}")
        return False

    try:
        print(f"Playing locally on Raspberry Pi: {audio_file}")
        subprocess.run(["pw-play", str(audio_file)], check=True)
        print("Local playback finished.")
        return True
    except FileNotFoundError:
        print("Could not find 'pw-play'.")
        return False
    except subprocess.CalledProcessError as error:
        print("Local playback failed.")
        print(error)
        return False


def setup_mqtt():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()
    return client


def publish_status(client, status):
    client.publish(STATUS_TOPIC, json.dumps(status, ensure_ascii=False), qos=1)
    print("Published status.")


def publish_audio(client):
    if not AUDIO_FILE.exists():
        print("No audio file found yet.")
        return False

    audio_bytes = AUDIO_FILE.read_bytes()
    client.publish(AUDIO_TOPIC, audio_bytes, qos=1)
    print(f"Published audio through MQTT: {AUDIO_FILE} ({len(audio_bytes)} bytes)")
    return True


def ensure_log_file():
    """
    Create a compatible CSV log.

    If an older log has a different header, preserve it with a timestamped name.
    """
    LOG_DIR.mkdir(exist_ok=True)

    if LOG_FILE.exists():
        try:
            with LOG_FILE.open("r", newline="", encoding="utf-8") as file:
                existing_header = next(csv.reader(file), [])
        except (OSError, StopIteration):
            existing_header = []

        if existing_header == LOG_FIELDNAMES:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archived_file = LOG_DIR / f"broadcast_log_before_llm_{timestamp}.csv"
        LOG_FILE.rename(archived_file)
        print(f"Archived old log file: {archived_file}")

    with LOG_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=LOG_FIELDNAMES)
        writer.writeheader()

    print(f"Created log file: {LOG_FILE}")


def append_broadcast_log(status, audio_generated, audio_sent_mqtt, audio_played_locally):
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
        "spectral_visible_total": readings["spectral_visible_total"],
        "spectral_clear": readings["spectral_clear"],
        "spectral_nir": readings["spectral_nir"],
        "spectral_blue_ratio": readings["spectral_blue_ratio"],
        "spectral_green_ratio": readings["spectral_green_ratio"],
        "spectral_red_ratio": readings["spectral_red_ratio"],
        "soil_state": states["soil_state"],
        "light_state": states["light_state"],
        "spectral_light_state": states["spectral_light_state"],
        "temperature_state": states["temperature_state"],
        "humidity_state": states["humidity_state"],
        "text_source": status["text_source"],
        "llm_error": status["llm_error"],
        "generated_text": status["text"],
        "audio_file": status["audio_file"],
        "audio_generated": audio_generated,
        "audio_sent_mqtt": audio_sent_mqtt,
        "audio_played_locally": audio_played_locally,
    }

    with LOG_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=LOG_FIELDNAMES)
        writer.writerow(row)

    print(f"Appended broadcast log: {LOG_FILE}")


def scheduled_broadcast_loop(client, sensors):
    soil_sensor, light_sensor, sht31, spectral_sensor = sensors

    while True:
        cycle_started = datetime.now()
        audio_generated = False
        audio_sent_mqtt = False
        audio_played_locally = False
        status = None

        try:
            print("\n------------------------------")
            print("Scheduled plant broadcast")
            print(cycle_started.strftime("%Y-%m-%d %H:%M:%S"))

            readings = read_sensors(
                soil_sensor,
                light_sensor,
                sht31,
                spectral_sensor,
            )

            text, states, text_source, llm_error = choose_plant_text(readings)

            status = {
                "plant_id": PLANT_ID,
                "timestamp": cycle_started.isoformat(timespec="seconds"),
                "readings": readings,
                "states": states,
                "text_source": text_source,
                "llm_error": llm_error,
                "text": text,
                "audio_file": str(AUDIO_FILE),
            }

            print("Readings:")
            print(json.dumps(readings, indent=2))
            print("Text source:", text_source)
            print("Generated text:")
            print(text)

            raw_audio_generated = synthesize_to_wav(
                text,
                RAW_AUDIO_FILE
            )

            if raw_audio_generated:
                audio_generated = process_audio_for_am(
                    RAW_AUDIO_FILE,
                    AUDIO_FILE
                )
            else:
                audio_generated = False

            if audio_generated:
                print(f"Audio saved: {AUDIO_FILE}")

                if ENABLE_MQTT and client is not None:
                    publish_status(client, status)
                    audio_sent_mqtt = publish_audio(client)

                if ENABLE_LOCAL_PLAYBACK:
                    audio_played_locally = play_audio_locally(AUDIO_FILE)
            else:
                print("Audio generation failed. Nothing was played or sent.")

        except Exception as error:
            print("Error during scheduled broadcast:", error)

        if status is not None:
            append_broadcast_log(
                status=status,
                audio_generated=audio_generated,
                audio_sent_mqtt=audio_sent_mqtt,
                audio_played_locally=audio_played_locally,
            )

        print(
            f"Waiting {UPDATE_INTERVAL_SECONDS} seconds "
            "before next scheduled broadcast..."
        )
        time.sleep(UPDATE_INTERVAL_SECONDS)


def main():
    print("Starting Talking Plant controller...")
    print(f"Broadcast interval: {UPDATE_INTERVAL_SECONDS} seconds")
    print(f"Azure LLM enabled: {ENABLE_LLM}")
    print(f"LLM timeout: {LLM_TIMEOUT_SECONDS} seconds")
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
        print("\nStopping...")
    finally:
        if mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()


if __name__ == "__main__":
    main()
