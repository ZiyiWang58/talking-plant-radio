import os
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

load_dotenv()

speech_key = os.getenv("AZURE_SPEECH_KEY")
speech_region = os.getenv("AZURE_SPEECH_REGION")
voice_name = os.getenv("AZURE_VOICE_NAME", "en-US-JennyNeural")

if not speech_key or not speech_region:
    raise RuntimeError("Missing Azure key or region. Check your .env file.")

speech_config = speechsdk.SpeechConfig(
    subscription=speech_key,
    region=speech_region
)

speech_config.speech_synthesis_voice_name = voice_name

# Save audio to a WAV file on the Raspberry Pi.
audio_config = speechsdk.audio.AudioOutputConfig(filename="test_voice.wav")

synthesizer = speechsdk.SpeechSynthesizer(
    speech_config=speech_config,
    audio_config=audio_config
)

text = "Hello. I am the plant. My sensors are awake, and I am ready to speak."

result = synthesizer.speak_text_async(text).get()

if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
    print("Success. Audio saved as test_voice.wav")
else:
    print("Failed.")
    print(result.reason)
    if result.reason == speechsdk.ResultReason.Canceled:
        print(result.cancellation_details.reason)
        print(result.cancellation_details.error_details)
