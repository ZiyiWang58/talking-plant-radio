# Calibration and final interpretation settings

## Soil moisture

The Adafruit STEMMA soil sensor reports a relative raw value rather than
volumetric water content. Its readings depend on the pot, substrate, insertion
depth, sensor position and watering pattern. Higher values normally indicate
wetter soil.

The final program defaults are:

| Raw reading | State |
| ---: | --- |
| `< 650` | very dry for a prayer plant |
| `650–999` | slightly dry for a prayer plant |
| `1000–1449` | comfortably moist |
| `1450–1849` | wet |
| `≥ 1850` | too wet or waterlogged |

To recalibrate, log readings with the probe fixed in its final position at
several repeatable conditions: before watering, after an ordinary watering,
after drainage and during gradual drying. Choose boundaries from these observed
ranges, then change the four `PRAYER_SOIL_*` values in `.env`.

## Other final classifications

| Variable | Final ranges or ordered rules |
| --- | --- |
| Illuminance | `<300`, `300–799`, `800–6499`, `6500–9999`, `≥10000` lux |
| Temperature | `<15`, `15–<18`, `18–27`, `>27–30`, `>30` °C |
| Relative humidity | `<40`, `40–<55`, `55–75`, `>75–85`, `>85` % RH |
| Spectrum | too dim if visible total or clear `<50`; otherwise blue/red dominance differs by `0.06`, followed by green dominance, then mixed/balanced |

The spectral ratios are calculated from the AS7341 visible bands. NIR is logged
but is not used for classification.

## Timing

`UPDATE_INTERVAL_SECONDS=5` means the controller waits five seconds after a
complete sensing, generation, synthesis, filtering and playback cycle. It does
not guarantee a new broadcast every five seconds because the preceding work
also takes time.
