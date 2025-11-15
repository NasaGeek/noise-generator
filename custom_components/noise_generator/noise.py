"""Utilities for generating synthetic noise audio."""

from __future__ import annotations

import random
import struct
import math
from typing import Any

from .const import (
    CONF_CUSTOM_HIGH_CUTOFF,
    CONF_CUSTOM_LOW_CUTOFF,
    CONF_CUSTOM_SLOPE,
    CONF_PROFILE_PARAMETERS,
    CONF_PROFILE_TYPE,
    CONF_SEED,
    CONF_VOLUME,
    DEFAULT_VOLUME,
    DEFAULT_CUSTOM_HIGH_CUTOFF,
    DEFAULT_CUSTOM_LOW_CUTOFF,
    DEFAULT_CUSTOM_SLOPE,
    PROFILE_TYPES,
    SAMPLE_RATE,
    CUSTOM_SLOPE_MIN,
    CUSTOM_SLOPE_MAX,
    CUSTOM_LOW_CUTOFF_MIN,
    CUSTOM_HIGH_CUTOFF_MAX,
)

class UnknownNoiseTypeError(ValueError):
    """Error raised when an unsupported noise type is requested."""


def _clamp(value: float, minimum: float, maximum: float) -> float:
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def _normalise(value: float) -> int:
    return int(_clamp(value, -1.0, 1.0) * 32767)


def _alpha_lowpass(cutoff_hz: float) -> float:
    if cutoff_hz <= 0:
        return 1.0
    rc = 1.0 / (2 * math.pi * cutoff_hz)
    dt = 1.0 / SAMPLE_RATE
    return dt / (rc + dt)


def _alpha_highpass(cutoff_hz: float) -> float:
    if cutoff_hz <= 0:
        return 0.0
    rc = 1.0 / (2 * math.pi * cutoff_hz)
    dt = 1.0 / SAMPLE_RATE
    return rc / (rc + dt)


class NoiseGenerator:
    """Generate PCM frames for a specific noise profile."""

    def __init__(
        self,
        noise_type: str,
        volume: float,
        seed: Any | None = None,
        *,
        custom_params: dict[str, Any] | None = None,
    ) -> None:
        if noise_type not in PROFILE_TYPES:
            raise UnknownNoiseTypeError(noise_type)

        self.noise_type = noise_type
        self.volume = _clamp(float(volume), 0.0, 1.0)
        self._rng = random.Random(seed)
        self._brown_value = 0.0
        self._pink_state = [0.0] * 7
        self._custom_state: dict[str, float] | None = None
        if noise_type == "custom":
            params = custom_params or {}
            slope = _clamp(
                float(params.get(CONF_CUSTOM_SLOPE, DEFAULT_CUSTOM_SLOPE)),
                CUSTOM_SLOPE_MIN,
                CUSTOM_SLOPE_MAX,
            )
            low = _clamp(
                float(params.get(CONF_CUSTOM_LOW_CUTOFF, DEFAULT_CUSTOM_LOW_CUTOFF)),
                CUSTOM_LOW_CUTOFF_MIN,
                CUSTOM_HIGH_CUTOFF_MAX,
            )
            high = _clamp(
                float(params.get(CONF_CUSTOM_HIGH_CUTOFF, DEFAULT_CUSTOM_HIGH_CUTOFF)),
                low + 1.0,
                CUSTOM_HIGH_CUTOFF_MAX,
            )
            if high <= low:
                high = min(max(low + 50.0, CUSTOM_LOW_CUTOFF_MIN + 1.0), CUSTOM_HIGH_CUTOFF_MAX)

            self._custom_state = {
                "tilt": slope / max(abs(CUSTOM_SLOPE_MIN), CUSTOM_SLOPE_MAX),
                "hp_alpha": _alpha_highpass(low),
                "hp_prev": 0.0,
                "hp_prev_input": 0.0,
                "lp_alpha": _alpha_lowpass(high),
                "lp_prev": 0.0,
                "prev_white": 0.0,
                "brown": 0.0,
            }

    def _next_sample(self) -> float:
        if self.noise_type == "white":
            return self._rng.uniform(-1.0, 1.0)
        if self.noise_type == "brown":
            self._brown_value += self._rng.uniform(-1.0, 1.0) * 0.02
            self._brown_value = _clamp(self._brown_value, -1.0, 1.0)
            # Apply slight damping so it does not drift indefinitely
            self._brown_value *= 0.98
            return self._brown_value
        if self.noise_type == "pink":
            white = self._rng.uniform(-1.0, 1.0)
            self._pink_state[0] = 0.99886 * self._pink_state[0] + white * 0.0555179
            self._pink_state[1] = 0.99332 * self._pink_state[1] + white * 0.0750759
            self._pink_state[2] = 0.96900 * self._pink_state[2] + white * 0.1538520
            self._pink_state[3] = 0.86650 * self._pink_state[3] + white * 0.3104856
            self._pink_state[4] = 0.55000 * self._pink_state[4] + white * 0.5329522
            self._pink_state[5] = -0.7616 * self._pink_state[5] - white * 0.0168980
            pink = (
                self._pink_state[0]
                + self._pink_state[1]
                + self._pink_state[2]
                + self._pink_state[3]
                + self._pink_state[4]
                + self._pink_state[5]
                + self._pink_state[6]
                + white * 0.5362
            )
            self._pink_state[6] = white * 0.115926
            return _clamp(pink * 0.11, -1.0, 1.0)

        if self.noise_type == "custom":
            return self._next_custom_sample()

        raise UnknownNoiseTypeError(self.noise_type)

    def _next_custom_sample(self) -> float:
        assert self._custom_state is not None

        white = self._rng.uniform(-1.0, 1.0)
        # Derive brown-ish curve
        brown = self._custom_state["brown"] + white * 0.02
        brown = _clamp(brown, -1.0, 1.0)
        self._custom_state["brown"] = brown * 0.98

        # Blue-ish component from differentiating white noise
        prev_white = self._custom_state["prev_white"]
        blue = _clamp(white - prev_white, -1.0, 1.0)
        self._custom_state["prev_white"] = white

        tilt = self._custom_state["tilt"]
        if tilt >= 0:
            shaped = (1.0 - tilt) * white + tilt * blue
        else:
            shaped = (1.0 + tilt) * white - tilt * brown

        # High-pass filter
        hp_alpha = self._custom_state["hp_alpha"]
        hp_prev = self._custom_state["hp_prev"]
        hp_prev_input = self._custom_state["hp_prev_input"]
        high = hp_alpha * (hp_prev + shaped - hp_prev_input)
        self._custom_state["hp_prev"] = _clamp(high, -1.5, 1.5)
        self._custom_state["hp_prev_input"] = shaped

        # Low-pass filter
        lp_alpha = self._custom_state["lp_alpha"]
        lp_prev = self._custom_state["lp_prev"]
        band = lp_prev + lp_alpha * (_clamp(high, -1.5, 1.5) - lp_prev)
        self._custom_state["lp_prev"] = band
        return _clamp(band, -1.0, 1.0)

    def next_chunk(self, sample_count: int) -> bytes:
        """Return the next PCM chunk for the configured noise profile."""

        frames = bytearray()
        for _ in range(sample_count):
            sample = self._next_sample() * self.volume
            frames.extend(struct.pack("<h", _normalise(sample)))
        return bytes(frames)


def build_wav_header(sample_rate: int = SAMPLE_RATE) -> bytes:
    """Return a WAV header suitable for indefinite streaming."""

    channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    return struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        0xFFFFFFFF,
        b"WAVE",
        b"fmt ",
        16,
        1,
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        0xFFFFFFFF,
    )


def coerce_profile(raw_profile: dict[str, Any]) -> dict[str, Any]:
    """Return a serialisable copy of a profile definition."""

    noise_type = raw_profile.get(CONF_PROFILE_TYPE, PROFILE_TYPES[0])
    if noise_type not in PROFILE_TYPES:
        noise_type = PROFILE_TYPES[0]

    parameters = dict(raw_profile.get(CONF_PROFILE_PARAMETERS, {}))

    volume = float(parameters.get(CONF_VOLUME, DEFAULT_VOLUME))
    volume = _clamp(volume, 0.0, 1.0)
    parameters[CONF_VOLUME] = volume

    seed = parameters.get(CONF_SEED)
    if seed in ("", None):
        parameters.pop(CONF_SEED, None)
    else:
        parameters[CONF_SEED] = seed

    if noise_type == "custom":
        slope = float(parameters.get(CONF_CUSTOM_SLOPE, DEFAULT_CUSTOM_SLOPE))
        slope = _clamp(slope, CUSTOM_SLOPE_MIN, CUSTOM_SLOPE_MAX)
        low = float(parameters.get(CONF_CUSTOM_LOW_CUTOFF, DEFAULT_CUSTOM_LOW_CUTOFF))
        low = _clamp(low, CUSTOM_LOW_CUTOFF_MIN, CUSTOM_HIGH_CUTOFF_MAX)
        high = float(parameters.get(CONF_CUSTOM_HIGH_CUTOFF, DEFAULT_CUSTOM_HIGH_CUTOFF))
        high = _clamp(high, low + 1.0, CUSTOM_HIGH_CUTOFF_MAX)
        if high <= low:
            high = min(max(low + 50.0, CUSTOM_LOW_CUTOFF_MIN + 1.0), CUSTOM_HIGH_CUTOFF_MAX)
        parameters[CONF_CUSTOM_SLOPE] = slope
        parameters[CONF_CUSTOM_LOW_CUTOFF] = low
        parameters[CONF_CUSTOM_HIGH_CUTOFF] = high
    else:
        parameters.pop(CONF_CUSTOM_SLOPE, None)
        parameters.pop(CONF_CUSTOM_LOW_CUTOFF, None)
        parameters.pop(CONF_CUSTOM_HIGH_CUTOFF, None)

    return {
        CONF_PROFILE_TYPE: noise_type,
        CONF_PROFILE_PARAMETERS: parameters,
    }
