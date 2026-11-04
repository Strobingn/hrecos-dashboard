"""Lowrance .sl2 and .sl3 frame reader.

Field order follows the MIT-licensed readers python-sllib (Peter Magnusson,
opensounder, https://github.com/opensounder/python-sllib) and sonarlight
(Kenneth Thorø Martinsen, https://github.com/KennethTM/sonarlight). This
module does not vendor either package.

Checked against the public example headers in the sonarlight repo:

- SL2 water depth is the float at frame offset 64 (sllib). The sonarlight
  SL2 dtype places that float one byte earlier and does not match the example.
- SL2 hardware time is the uint32 at frame offset 60, inside the pad sllib
  leaves anonymous. On the example file it is a Unix second.
- SL3 water depth is the float at frame offset 48. Flags are the uint16 at
  offset 116 and the millisecond field is the uint32 at offset 124 (sllib).
  sonarlight's SL3 flags and seconds fields sit two bytes earlier and do not
  match the example.

Depths in the file are feet. GPS speed is knots. Coordinates are a Mercator
encoding used by both readers. Sounding samples are uint8 after a fixed
header (144 bytes on SL2, 168 on SL3). The frame stride is the framesize
field, not a constant block.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

EARTH_RADIUS_M = 6356752.3142
FEET_TO_M = 0.3048
KNOTS_TO_MPS = 1852.0 / 3600.0

SL2_HEADER = 144
SL3_HEADER = 168
FILE_HEADER = 8

# Channel numbers from sonarlight's survey_dict. Other numbers are stored
# and ignored by the detector.
CHANNELS = {
    0: "primary",
    1: "secondary",
    2: "downscan",
    3: "left_sidescan",
    4: "right_sidescan",
    5: "sidescan",
}

FREQUENCIES = {
    0: "200kHz",
    1: "50kHz",
    2: "83kHz",
    3: "455kHz",
    4: "800kHz",
    5: "38kHz",
    6: "28kHz",
    7: "130-210kHz",
    8: "90-150kHz",
    9: "40-60kHz",
    10: "25-45kHz",
}

HAS_POSITION = 0x0010
HAS_GPS_SPEED = 0x0002


@dataclass(frozen=True)
class Ping:
    channel: int
    channel_name: str
    frequency: str
    upper_m: float
    lower_m: float
    depth_m: float
    latitude: float | None
    longitude: float | None
    speed_mps: float
    time: datetime | None
    samples: bytes
    frame_index: int


@dataclass(frozen=True)
class LogInfo:
    format: int
    device: int
    blocksize: int
    kind: str
    pings: tuple[Ping, ...]


def channel_name(channel: int) -> str:
    return CHANNELS.get(channel, f"channel_{channel}")


def lon_to_enc(longitude: float) -> int:
    return int(round(longitude * (math.pi / 180.0) * EARTH_RADIUS_M))


def lat_to_enc(latitude: float) -> int:
    rad = latitude * (math.pi / 180.0)
    return int(round(math.log(math.tan((rad + math.pi / 2.0) / 2.0)) * EARTH_RADIUS_M))


def enc_to_lon(encoded: int) -> float:
    return encoded / EARTH_RADIUS_M * (180.0 / math.pi)


def enc_to_lat(encoded: int) -> float:
    return (2.0 * math.atan(math.exp(encoded / EARTH_RADIUS_M)) - math.pi / 2.0) * (
        180.0 / math.pi
    )


def read_log(path: Path | str) -> LogInfo:
    data = Path(path).read_bytes()
    if len(data) < FILE_HEADER:
        raise ValueError(f"{path} is shorter than a Lowrance file header")
    fmt, device, blocksize, _reserved = struct.unpack_from("<4H", data, 0)
    if fmt == 2:
        kind = "sl2"
        header_size = SL2_HEADER
    elif fmt == 3:
        kind = "sl3"
        header_size = SL3_HEADER
    else:
        raise ValueError(f"{path} format {fmt} is not .sl2 (2) or .sl3 (3)")
    pings: list[Ping] = []
    pos = FILE_HEADER
    while pos + header_size <= len(data):
        framesize = _framesize(data, pos, fmt)
        if framesize < header_size or pos + framesize > len(data):
            break
        pings.append(_ping(data, pos, fmt, header_size, framesize))
        pos += framesize
    return LogInfo(
        format=fmt,
        device=device,
        blocksize=blocksize,
        kind=kind,
        pings=tuple(pings),
    )


def _framesize(data: bytes, pos: int, fmt: int) -> int:
    offset = 28 if fmt == 2 else 8
    return struct.unpack_from("<H", data, pos + offset)[0]


def _ping(data: bytes, pos: int, fmt: int, header_size: int, framesize: int) -> Ping:
    if fmt == 2:
        channel = struct.unpack_from("<H", data, pos + 32)[0]
        packetsize = struct.unpack_from("<H", data, pos + 34)[0]
        frame_index = struct.unpack_from("<I", data, pos + 36)[0]
        upper_ft, lower_ft = struct.unpack_from("<ff", data, pos + 40)
        frequency = data[pos + 50]
        hardware_time = struct.unpack_from("<I", data, pos + 60)[0]
        depth_ft = struct.unpack_from("<f", data, pos + 64)[0]
        gps_knots = struct.unpack_from("<f", data, pos + 100)[0]
        lon_enc, lat_enc = struct.unpack_from("<ii", data, pos + 108)
        flags = struct.unpack_from("<H", data, pos + 132)[0]
        time_ms = struct.unpack_from("<I", data, pos + 140)[0]
    else:
        channel = struct.unpack_from("<I", data, pos + 12)[0]
        frame_index = struct.unpack_from("<I", data, pos + 16)[0]
        upper_ft, lower_ft = struct.unpack_from("<ff", data, pos + 20)
        hardware_time = struct.unpack_from("<I", data, pos + 40)[0]
        packetsize = struct.unpack_from("<I", data, pos + 44)[0]
        depth_ft = struct.unpack_from("<f", data, pos + 48)[0]
        frequency = struct.unpack_from("<I", data, pos + 52)[0]
        gps_knots = struct.unpack_from("<f", data, pos + 84)[0]
        lon_enc, lat_enc = struct.unpack_from("<ii", data, pos + 92)
        flags = struct.unpack_from("<H", data, pos + 116)[0]
        time_ms = struct.unpack_from("<I", data, pos + 124)[0]
    available = max(0, framesize - header_size)
    count = min(max(0, packetsize), available)
    samples = data[pos + header_size : pos + header_size + count]
    has_fix = bool(flags & HAS_POSITION) and not (lat_enc == 0 and lon_enc == 0)
    speed = gps_knots * KNOTS_TO_MPS if flags & HAS_GPS_SPEED else 0.0
    if not math.isfinite(speed) or speed < 0:
        speed = 0.0
    return Ping(
        channel=channel,
        channel_name=channel_name(channel),
        frequency=FREQUENCIES.get(frequency, f"frequency_{frequency}"),
        upper_m=upper_ft * FEET_TO_M,
        lower_m=lower_ft * FEET_TO_M,
        depth_m=depth_ft * FEET_TO_M if math.isfinite(depth_ft) and depth_ft > 0 else 0.0,
        latitude=enc_to_lat(lat_enc) if has_fix else None,
        longitude=enc_to_lon(lon_enc) if has_fix else None,
        speed_mps=speed,
        time=_timestamp(hardware_time, time_ms),
        samples=samples,
        frame_index=frame_index,
    )


def _timestamp(hardware_time: int, time_ms: int) -> datetime | None:
    if not (1_400_000_000 <= hardware_time <= 2_100_000_000):
        return None
    base = datetime.fromtimestamp(hardware_time, timezone.utc)
    return base + timedelta(milliseconds=int(time_ms))


@dataclass
class Frame:
    """One sounding written by ``write_log`` for tests."""

    channel: int
    samples: bytes
    upper_ft: float = 0.0
    lower_ft: float = 32.0
    depth_ft: float = 20.0
    latitude: float = 41.38607
    longitude: float = -73.95496
    speed_knots: float = 0.0
    hardware_time: int = 1_714_521_600
    time_ms: int = 0
    frequency: int = 4
    frame_index: int = 0


def write_log(path: Path | str, frames: list[Frame], kind: str = "sl2") -> None:
    """Write a small .sl2 or .sl3. Used by tests. Not a full Lowrance recorder."""
    if kind not in ("sl2", "sl3"):
        raise ValueError("kind must be sl2 or sl3")
    fmt = 2 if kind == "sl2" else 3
    header_size = SL2_HEADER if kind == "sl2" else SL3_HEADER
    out = bytearray(struct.pack("<4H", fmt, 2, 3200, 1))
    previous: dict[int, int] = {}
    previous_size = 0
    for frame in frames:
        offset = len(out)
        packet = frame.samples
        framesize = header_size + len(packet)
        block = bytearray(header_size)
        flags = HAS_POSITION | HAS_GPS_SPEED
        if kind == "sl2":
            struct.pack_into("<I", block, 0, offset)
            for index, channel in enumerate((0, 1, 2, 3, 4, 5)):
                struct.pack_into("<I", block, 4 + 4 * index, previous.get(channel, 0))
            struct.pack_into("<H", block, 28, framesize)
            struct.pack_into("<H", block, 30, previous_size)
            struct.pack_into("<H", block, 32, frame.channel)
            struct.pack_into("<H", block, 34, len(packet))
            struct.pack_into("<I", block, 36, frame.frame_index)
            struct.pack_into("<ff", block, 40, frame.upper_ft, frame.lower_ft)
            block[50] = frame.frequency & 0xFF
            struct.pack_into("<I", block, 60, frame.hardware_time)
            struct.pack_into("<f", block, 64, frame.depth_ft)
            struct.pack_into("<f", block, 100, frame.speed_knots)
            struct.pack_into(
                "<ii",
                block,
                108,
                lon_to_enc(frame.longitude),
                lat_to_enc(frame.latitude),
            )
            struct.pack_into("<H", block, 132, flags)
            struct.pack_into("<I", block, 140, frame.time_ms)
        else:
            struct.pack_into("<I", block, 0, offset)
            struct.pack_into("<H", block, 8, framesize)
            struct.pack_into("<H", block, 10, previous_size)
            struct.pack_into("<I", block, 12, frame.channel)
            struct.pack_into("<I", block, 16, frame.frame_index)
            struct.pack_into("<ff", block, 20, frame.upper_ft, frame.lower_ft)
            struct.pack_into("<I", block, 40, frame.hardware_time)
            struct.pack_into("<I", block, 44, len(packet))
            struct.pack_into("<f", block, 48, frame.depth_ft)
            struct.pack_into("<I", block, 52, frame.frequency)
            struct.pack_into("<f", block, 84, frame.speed_knots)
            struct.pack_into(
                "<ii",
                block,
                92,
                lon_to_enc(frame.longitude),
                lat_to_enc(frame.latitude),
            )
            struct.pack_into("<H", block, 116, flags)
            struct.pack_into("<I", block, 124, frame.time_ms)
        out += block
        out += packet
        previous[frame.channel] = offset
        previous_size = framesize
    Path(path).write_bytes(out)
