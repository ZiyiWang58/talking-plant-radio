# TuneIn: Talking Plants over the AM Waveband

TuneIn is a single-prayer-plant installation that senses soil moisture,
temperature, humidity, illuminance and spectral light composition. A Raspberry
Pi classifies the readings, generates a short first-person message with Azure
OpenAI or preset fallback sentences, synthesises speech with Azure Speech,
processes it for AM intelligibility with FFmpeg and plays it into the physical
AM transmitter. A phone-friendly Flask page shows the latest reading and spoken
message.

This repository is based on the final Raspberry Pi program
`plant_pi_controller_local_playback.py`.

## Repository contents

| Path | Purpose |
| --- | --- |
| `plant_pi_controller_local_playback.py` | Final sensing, interpretation, text, TTS, audio and logging loop |
| `display_server.py` | Self-contained status webpage and JSON endpoint |
| `start_demo.sh` | Starts the controller with PipeWire playback |
| `start_main_service.sh` | Waits for the user audio session, then starts the controller |
| `start_display.sh` | Starts the Flask display |
| `tests/` | Four-sensor and AS7341-only hardware checks |
| `requirements.txt` | Direct Python dependencies used by the project |
| `requirements-lock.txt` | Complete package versions exported from the deployed `.venv` |
| `.env.example` | Safe configuration template without credentials |
| `systemd/` | Optional user-service templates for automatic startup |
| `docs/` | Calibration, timing and source-verification notes |
| `hardware/` | Required physical-documentation checklist |

## Final deployed settings represented here

- One prayer plant: *Maranta leuconeura*.
- Azure OpenAI enabled, with a maximum of 24 words and a 12-second timeout.
- Preset first-person sentences used automatically if the LLM is disabled or
  unavailable, times out or returns unusable text.
- Azure voice `en-US-JennyNeural`.
- 16 kHz, 16-bit, mono WAV synthesis; SSML rate `-10%`, pitch `0%`, with a
  250 ms break inserted between sentences.
- FFmpeg filtering: 300 Hz high-pass, 3.2 kHz low-pass, compression and loudness
  normalisation.
- Local PipeWire playback enabled; MQTT disabled.
- Five-second wait after each complete broadcast cycle.

## Raspberry Pi setup

The deployed environment used Python 3.13. A Raspberry Pi OS installation with
I²C enabled, working network access, a PipeWire audio sink and the four connected
sensors is required.

1. Install system packages:

   ```bash
   sudo apt update
   sudo apt install -y git python3-venv python3-pip ffmpeg pipewire-bin
   ```

2. Enable I²C with `sudo raspi-config`, then reboot if prompted.

3. Clone the repository to `~/TuneIn` and enter it:

   ```bash
   git clone https://github.com/ZiyiWang58/talking-plant-radio.git ~/TuneIn
   cd ~/TuneIn
   ```

4. Create the virtual environment and install the locked packages:

   ```bash
   python3 -m venv .venv
   ./.venv/bin/python -m pip install --upgrade pip
   ./.venv/bin/python -m pip install -r requirements-lock.txt
   ```

   Use `requirements.txt` instead when only the project's direct dependencies
   should be pinned and pip may resolve their subdependencies.

5. Create the private configuration:

   ```bash
   cp .env.example .env
   nano .env
   ```

   Enter the Azure Speech key and region. If Azure OpenAI is enabled, also enter
   its endpoint, key and deployment name. Never commit `.env`.

## Test the sensors

Run the combined soil, lux, temperature and humidity test:

```bash
./.venv/bin/python tests/sensor_test.py
```

Run the AS7341 spectral test separately:

```bash
./.venv/bin/python tests/test_as7341.py
```

Both programs continue until `Ctrl+C` is pressed.

## Select and test the audio output

List PipeWire devices:

```bash
wpctl status
```

If the Pi analogue output is already the default, start the controller with:

```bash
./start_demo.sh
```

Otherwise provide the sink ID shown by `wpctl status`:

```bash
PIPEWIRE_SINK=57 PIPEWIRE_VOLUME=60% ./start_demo.sh
```

The number `57` was used by the final exhibit but is not portable; PipeWire may
assign a different ID after reboot or on another Raspberry Pi.

## Start the phone display

In a second terminal:

```bash
./start_display.sh
```

Open `http://PI_IP_ADDRESS:5000` on a device that can reach the Raspberry Pi.
The page requests `/api/status` every two seconds and displays the newest row
from `logs/broadcast_log.csv`. The controller creates this file automatically.
The Flask server binds to all interfaces, so expose it only on a trusted local
network or private overlay network, not directly to the public internet.

## Optional automatic startup

The included user-service templates assume the repository is `~/TuneIn`:

```bash
mkdir -p ~/.config/systemd/user
cp systemd/tunein-controller.service ~/.config/systemd/user/
cp systemd/tunein-display.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now tunein-controller.service
systemctl --user enable --now tunein-display.service
```

To keep user services running without an interactive login, an administrator
can enable lingering for the Pi account:

```bash
sudo loginctl enable-linger "$USER"
```

If the analogue sink is not the default, edit the controller service and set
`PIPEWIRE_SINK` to the correct ID before enabling it.

## Runtime files

The controller generates these files, all excluded by `.gitignore`:

- `latest_plant_voice_raw.wav` — Azure Speech output;
- `latest_plant_voice.wav` — filtered AM-oriented output;
- `logs/broadcast_log.csv` — readings, states, message source and playback status.

The web display requires no `templates/` or `static/` directory because its
HTML, CSS and JavaScript are embedded in `display_server.py`.

## Reproducibility boundary

The software side is represented by the final controller, display, dependency
versions, safe configuration template, tests and startup files. Full physical
reproduction still requires the exact AM transmitter, coupling coil, crystal
radio, wiring, bill of materials and enclosure documentation listed in
`hardware/README.md`. Add only materials verified against the final exhibit.
