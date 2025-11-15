# Noise Generator for Home Assistant

Noise Generator is a custom integration that synthesizes continuous white, pink, brown, or fully custom noise directly inside Home Assistant. Each profile becomes a media source entry that you can browse from the UI or trigger through automations or scripts, giving you a reliable ambient-noise generator without relying on external services.

> Built by **vibe coding** with ChatGPT-assisted development.

---

## Features

- Pure Python noise generation—no external APIs or cloud dependencies.
- Built-in profiles (white, pink, brown) plus unlimited custom “colors”.
- Per-profile volume and random seed controls to balance or stabilize outputs.
- Seamless Media Source integration: play from the Media Browser or call `media_player.play_media`.
- 100% UI-driven config flow for adding, editing, and deleting profiles.

---

## Installation

### HACS (Recommended)
1. **Add repository**: In Home Assistant, go to **HACS → Integrations → ⋮ → Custom repositories**, enter the GitHub URL for this repo, and choose **Integration**.
2. **Install**: After the repo is added, find “Noise Generator” in HACS → Integrations and click **Download**.
3. **Restart HA** when prompted, then add the integration via **Settings → Devices & Services → Add Integration**.

### Manual Installation
1. Download or clone this repository.
2. Copy `custom_components/noise_generator/` into your Home Assistant config directory under `custom_components/`.
3. Restart HA and add the integration from **Settings → Devices & Services**.

---

## Usage

### Initial Setup
1. Go to **Settings → Devices & Services → Configure (cogwheel icon)**.
2. Select **Noise Generator**.
3. Fill out the form: profile name, noise type, volume (0–1), optional seed, and custom parameters if needed.
4. Submit to create the first profile and entry.

### Managing Profiles
- Navigate to **Settings → Devices & Services → Noise Generator → Configure (cogwheel icon)**.
- Choose **Add profile**, **Edit profile**, or **Remove profile** as needed.
- Saving via **Save changes** updates every profile in the entry.

### Playing Noise
**Media Browser**
1. Use the global **Media** panel or a media player’s “Browse media” button.
2. Open **Noise Generator** and choose a profile to play.

**Automations / Scripts**
Use the media-source URI for a profile:
```yaml
service: media_player.play_media
target:
  entity_id: media_player.living_room
data:
  media:
    media_content_id: media-source://noise_generator/<profile_name>
```
Obtain the name by browsing to the profile in the Media Browser or checking the integration’s logs.

### Custom Noise Parameters
| Parameter | Range | Effect |
|-----------|-------|--------|
| **Custom slope (dB/oct)** | –12.0 to +12.0 | Tilts the spectrum. Positive values brighten the noise (more high frequencies); negative values darken it (more low-end energy). |
| **Custom low cutoff (Hz)** | 1 to 21,800 | High-pass corner frequency. Raising it removes rumble/bass; lower values keep the full spectrum. |
| **Custom high cutoff (Hz)** | (Low cutoff + 1) to 21,800 | Low-pass corner. Lower settings yield softer, muffled tones; higher values preserve high-end hiss. |
| **Volume (0–1)** | 0.0 to 1.0 | Scales the generated signal before streaming. Use it to balance profiles; final loudness is still controlled by the media player. |
| **Random seed** | Any string or integer | Optional deterministic seed so the noise texture is reproducible. Leave blank for natural variation. |

Volume and seed apply to every profile type (built-in or custom), while slope/cutoffs are only shown when “Custom” is selected.

---

## License

This project is released under the **MIT License**, allowing you to use, modify, and redistribute the integration with minimal restrictions while retaining attribution and disclaiming liability.

---

Enjoy your bespoke ambient soundscapes!
