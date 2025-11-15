"""Subprocess entry-point that streams noise as WAV PCM data."""

from __future__ import annotations

import argparse
import signal
import sys
from typing import Any

from .const import (
    CONF_CUSTOM_HIGH_CUTOFF,
    CONF_CUSTOM_LOW_CUTOFF,
    CONF_CUSTOM_SLOPE,
    DEFAULT_CUSTOM_HIGH_CUTOFF,
    DEFAULT_CUSTOM_LOW_CUTOFF,
    DEFAULT_CUSTOM_SLOPE,
    SAMPLE_RATE,
    STREAM_CHUNK_DURATION,
)
from .noise import NoiseGenerator, build_wav_header

_STOP_REQUESTED = False


def _handle_signal(_: int, __) -> None:
    global _STOP_REQUESTED
    _STOP_REQUESTED = True


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Noise generator streaming process")
    parser.add_argument("--type", required=True, choices=["white", "pink", "brown", "custom"])
    parser.add_argument("--volume", type=float, default=0.5)
    parser.add_argument("--seed", default=None)
    parser.add_argument("--sample-rate", type=int, default=SAMPLE_RATE)
    parser.add_argument("--chunk-duration", type=float, default=STREAM_CHUNK_DURATION)
    parser.add_argument("--custom-slope", type=float, default=DEFAULT_CUSTOM_SLOPE)
    parser.add_argument("--custom-low-cutoff", type=float, default=DEFAULT_CUSTOM_LOW_CUTOFF)
    parser.add_argument("--custom-high-cutoff", type=float, default=DEFAULT_CUSTOM_HIGH_CUTOFF)
    return parser.parse_args(argv)


def _coerce_seed(seed: Any | None) -> Any | None:
    if seed in (None, "", "None"):
        return None
    try:
        return int(seed)
    except (TypeError, ValueError):
        return seed


def run(argv: list[str]) -> int:
    args = _parse_args(argv)

    chunk_samples = max(1, int(args.sample_rate * max(args.chunk_duration, 0.05)))
    custom_params = None
    if args.type == "custom":
        custom_params = {
            CONF_CUSTOM_SLOPE: args.custom_slope,
            CONF_CUSTOM_LOW_CUTOFF: args.custom_low_cutoff,
            CONF_CUSTOM_HIGH_CUTOFF: args.custom_high_cutoff,
        }
    generator = NoiseGenerator(
        args.type,
        args.volume,
        _coerce_seed(args.seed),
        custom_params=custom_params,
    )

    buffer = sys.stdout.buffer
    try:
        buffer.write(build_wav_header(args.sample_rate))
        buffer.flush()

        while not _STOP_REQUESTED:
            buffer.write(generator.next_chunk(chunk_samples))
            buffer.flush()
    except BrokenPipeError:
        return 0

    return 0


def main() -> None:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    sys.exit(run(sys.argv[1:]))


if __name__ == "__main__":  # pragma: no cover - executed as a module
    main()
