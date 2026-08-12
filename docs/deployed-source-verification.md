# Deployed source verification

These SHA-256 values were calculated from files copied from the final Raspberry
Pi project directory. They identify the source material used to prepare this
repository.

| File | SHA-256 |
| --- | --- |
| `plant_pi_controller_local_playback.py` | `f8bdbf91299d0923a04c3cf15d898881eabaefd9b51fca9da73c65728962ce13` |
| `display_server.py` | `a3d6d4e4fad1c11a238eefe7714cb44cfbc5daf36356b7c6dfd156041774a34f` |
| `start_main_service.sh` | `953ac641e06c29f5e86f6eab1d4e7595aa209bf122396cbc06ef4611d3c1f7c9` |
| `start_demo.sh` | `3f0be5a719c0471007bbd3cb582e40baf89aa8a274634ac13da3e684a42697d7` |
| `sensor_test.py` | `aa8699470903ee6edf37f7b495da222e2a36347b4d3864cf15b4a211d36ce748` |
| `test_as7341.py` | `9f2ee74727cd9c55fc025f39af1f6bae8ab10e1089f2d21e6cc1729fb77351f2` |
| `requirements-lock.txt` | `da92d6f17b97ddf2ad46c45786cd0a104caf67102f2a8e52cdf29105152788a3` |

The top-level GitHub-ready copies intentionally differ from some deployed
hashes only where portability required a change: fixed `/home/ziyi/...` paths
were replaced with paths resolved from each script, and audio sink `57` became
an optional `PIPEWIRE_SINK` setting. Sensor interpretation, message generation,
speech synthesis and AM audio processing logic were not changed.
