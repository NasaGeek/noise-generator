"""Constants for the Noise Generator integration."""

from __future__ import annotations

DOMAIN = "noise_generator"

CONF_PROFILES = "profiles"
CONF_PROFILE_NAME = "name"
CONF_PROFILE_TYPE = "type"
CONF_PROFILE_PARAMETERS = "parameters"

CONF_VOLUME = "volume"
CONF_SEED = "seed"
CONF_CUSTOM_SLOPE = "Custom slope"
CONF_CUSTOM_LOW_CUTOFF = "Custom low cutoff"
CONF_CUSTOM_HIGH_CUTOFF = "Custom high cutoff"

CONF_ACTION = "action"

DEFAULT_PROFILE_NAME = "White noise"
DEFAULT_PROFILE_TYPE = "white"
DEFAULT_VOLUME = 0.5
DEFAULT_CUSTOM_SLOPE = 0.0
DEFAULT_CUSTOM_LOW_CUTOFF = 20.0
DEFAULT_CUSTOM_HIGH_CUTOFF = 16000.0
CUSTOM_SLOPE_MIN = -12.0
CUSTOM_SLOPE_MAX = 12.0
CUSTOM_LOW_CUTOFF_MIN = 1.0

PROFILE_TYPES = [
    "white",
    "pink",
    "brown",
    "custom",
]

MEDIA_MIME_TYPE = "audio/wav"
SAMPLE_RATE = 44100
STREAM_CHUNK_DURATION = 0.5
STREAM_URL_PATH = f"/api/{DOMAIN}"
STDOUT_READ_SIZE = 32768
CUSTOM_HIGH_CUTOFF_MAX = SAMPLE_RATE / 2 - 200

ACTION_ADD = "add"
ACTION_EDIT = "edit"
ACTION_REMOVE = "remove"
ACTION_FINISH = "finish"
PROFILE_ROUTE = "profile"
