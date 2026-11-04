"""Water-column marks in a Lowrance log.

Primary and secondary (2D CHIRP) keep a target only when the bright core
forms an arch: range falls, then rises, across consecutive pings. That is
the conical-beam geometry of a fish crossing the beam. DownScan and SideScan
keep a compact bright mark above the bottom.

Surface bins and the bottom return are excluded before the threshold, so a
bright surface band or a bright bottom line is not a fish. Nothing here is
a species call. Length is an estimate from boat motion or from the height of
the bright mark, and the size class is only a candidate.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from sonar.slx import Ping

DETECTOR_NAME = "lowrance_mark"
DETECTOR_VERSION = "0.1.0"

# Priority order for labels: striped bass, Atlantic sturgeon, river herring.
# American shad overlaps bass and is mentioned, not labeled.
SIZE_ENVELOPES = (
    ("striped_bass", 30.0, 120.0),
    ("atlantic_sturgeon", 100.0, 250.0),
    ("river_herring", 20.0, 35.0),
)
SHAD_CM = (40.0, 60.0)

DOWN_CHANNELS = {"primary", "secondary", "downscan"}
ARCH_CHANNELS = {"primary", "secondary"}
SIDE_CHANNELS = {"left_sidescan", "right_sidescan", "sidescan"}

SURFACE_M = 0.5
BOTTOM_MARGIN_M = 0.4
MIN_ARCH_PINGS = 3
MIN_MARK_PINGS = 2
LINK_BINS = 4
# Along-track length needs the boat to be moving. Below this, GPS speed is
# drift and the beam is effectively stationary.
MOVING_MPS = 0.4


@dataclass(frozen=True)
class Detection:
    channel_name: str
    frequency: str
    start: object
    end: object
    depth_m: float
    range_m: float
    length_cm: float
    size_method: str
    boat_speed_mps: float
    peak_intensity: int
    n_pings: int
    arch: bool
    latitude: float | None
    longitude: float | None
    detection_confidence: float


def detect(pings: list[Ping] | tuple[Ping, ...]) -> list[Detection]:
    by_channel: dict[str, list[Ping]] = {}
    for ping in pings:
        if ping.channel_name not in DOWN_CHANNELS and ping.channel_name not in SIDE_CHANNELS:
            continue
        if not ping.samples or ping.time is None:
            continue
        by_channel.setdefault(ping.channel_name, []).append(ping)
    found: list[Detection] = []
    for name, group in by_channel.items():
        group.sort(key=lambda ping: ping.time)
        found.extend(_channel(name, group))
    found.sort(key=lambda item: (item.start, item.channel_name))
    return found


def size_class(length_cm: float) -> tuple[str, bool, list[str]]:
    """Return (label, bass_candidate, overlap notes).

    A match is a candidate, not a species. Striped bass is flagged whenever
    the estimate falls in 30–120 cm, including where herring, shad, or small
    sturgeon overlap.
    """
    matches = [name for name, low, high in SIZE_ENVELOPES if low <= length_cm <= high]
    bass = "striped_bass" in matches
    if bass:
        label = "striped_bass_candidate"
    elif "atlantic_sturgeon" in matches:
        label = "sturgeon_sized"
    elif "river_herring" in matches:
        label = "herring_sized"
    else:
        label = "unknown"
    notes: list[str] = []
    if bass and "atlantic_sturgeon" in matches:
        notes.append("also inside the Atlantic sturgeon envelope (100–250 cm)")
    if bass and "river_herring" in matches:
        notes.append("also inside the river herring envelope (20–35 cm)")
    if bass and SHAD_CM[0] <= length_cm <= SHAD_CM[1]:
        notes.append("also inside the American shad envelope (40–60 cm); shad is not assigned")
    return label, bass, notes


@dataclass
class _Mark:
    ping_index: int
    start_bin: int
    end_bin: int
    peak: int
    center: float


def _channel(name: str, pings: list[Ping]) -> list[Detection]:
    marks_at: list[list[_Mark]] = []
    for index, ping in enumerate(pings):
        water_start, water_end = _water_window(name, ping)
        marks_at.append(_marks(ping.samples, water_start, water_end, index))
    used: set[tuple[int, int]] = set()
    detections: list[Detection] = []
    for ping_index, marks in enumerate(marks_at):
        for mark_index, mark in enumerate(marks):
            key = (ping_index, mark_index)
            if key in used:
                continue
            chain = [mark]
            used.add(key)
            cursor = mark
            for nxt in range(ping_index + 1, len(pings)):
                link = _link(cursor, marks_at[nxt], nxt, used)
                if link is None:
                    break
                chain.append(link)
                cursor = link
            detection = _accept(name, pings, chain)
            if detection is not None:
                detections.append(detection)
    return detections


def _link(previous: _Mark, marks: list[_Mark], ping_index: int, used: set[tuple[int, int]]) -> _Mark | None:
    best: _Mark | None = None
    best_key: tuple[int, int] | None = None
    best_dist = LINK_BINS + 1
    for mark_index, mark in enumerate(marks):
        key = (ping_index, mark_index)
        if key in used:
            continue
        dist = abs(mark.center - previous.center)
        overlaps = mark.start_bin <= previous.end_bin + 2 and previous.start_bin <= mark.end_bin + 2
        if dist <= LINK_BINS or overlaps:
            if dist < best_dist:
                best = mark
                best_key = key
                best_dist = dist
    if best is None or best_key is None:
        return None
    used.add(best_key)
    return best


def _accept(name: str, pings: list[Ping], chain: list[_Mark]) -> Detection | None:
    arch = _is_arch(chain)
    if name in ARCH_CHANNELS:
        if len(chain) < MIN_ARCH_PINGS or not arch:
            return None
    else:
        if len(chain) < MIN_MARK_PINGS:
            return None
        centers = [mark.center for mark in chain]
        if max(centers) - min(centers) > 6:
            return None
    selected = [pings[mark.ping_index] for mark in chain]
    depths = [ping.depth_m for ping in selected if ping.depth_m > 0]
    if not depths:
        return None
    ranges = [_range_m(pings[mark.ping_index], mark.center) for mark in chain]
    speeds = [ping.speed_mps for ping in selected]
    boat_speed = statistics.fmean(speeds)
    start = selected[0].time
    end = selected[-1].time
    duration = max(0.0, (end - start).total_seconds())
    thickness_cm = statistics.fmean(
        _thickness_cm(pings[mark.ping_index], mark) for mark in chain
    )
    if boat_speed >= MOVING_MPS and duration > 0:
        length_cm = boat_speed * duration * 100.0
        method = "along_track"
    else:
        length_cm = thickness_cm
        method = "vertical_extent"
    if length_cm <= 0:
        return None
    peak = max(mark.peak for mark in chain)
    # Contrast against the water column of the brightest ping. Capped well
    # below 1: this is an uncalibrated consumer image, not a reviewed id.
    contrast = min(1.0, max(0.0, (peak - 30) / 220.0))
    ping_factor = min(1.0, len(chain) / 5.0)
    confidence = min(0.8, 0.25 + 0.35 * contrast + 0.2 * ping_factor)
    latitudes = [ping.latitude for ping in selected if ping.latitude is not None]
    longitudes = [ping.longitude for ping in selected if ping.longitude is not None]
    return Detection(
        channel_name=name,
        frequency=selected[0].frequency,
        start=start,
        end=end,
        depth_m=statistics.fmean(depths),
        range_m=statistics.fmean(ranges),
        length_cm=length_cm,
        size_method=method,
        boat_speed_mps=boat_speed,
        peak_intensity=peak,
        n_pings=len(chain),
        arch=arch,
        latitude=statistics.fmean(latitudes) if latitudes else None,
        longitude=statistics.fmean(longitudes) if longitudes else None,
        detection_confidence=round(confidence, 3),
    )


def _is_arch(chain: list[_Mark]) -> bool:
    if len(chain) < MIN_ARCH_PINGS:
        return False
    centers = [mark.center for mark in chain]
    apex = min(range(len(centers)), key=lambda index: centers[index])
    if apex == 0 or apex == len(centers) - 1:
        return False
    rise = centers[0] - centers[apex]
    fall = centers[-1] - centers[apex]
    return rise >= 2 and fall >= 2


def _water_window(name: str, ping: Ping) -> tuple[int, int]:
    samples = ping.samples
    count = len(samples)
    if count < 8:
        return 0, 0
    if name in SIDE_CHANNELS:
        surface_end = max(2, int(count * 0.05))
        bottom = _sidescan_bottom(samples, surface_end)
        return surface_end, max(surface_end, bottom - 2)
    surface_end, bottom_start = _depth_window(ping)
    return surface_end, bottom_start


def _depth_window(ping: Ping) -> tuple[int, int]:
    count = len(ping.samples)
    span = ping.lower_m - ping.upper_m
    if span <= 0 or ping.depth_m <= 0:
        return 0, 0

    def bin_at(depth_m: float) -> int:
        fraction = (depth_m - ping.upper_m) / span
        return int(fraction * count)

    surface_end = max(1, bin_at(ping.upper_m + SURFACE_M))
    bottom_start = bin_at(ping.depth_m - BOTTOM_MARGIN_M)
    bottom_start = max(surface_end + 1, min(count, bottom_start))
    surface_end = min(surface_end, bottom_start)
    return surface_end, bottom_start


def _sidescan_bottom(samples: bytes, surface_end: int) -> int:
    """First strong return in the outer half of a side-looking ping.

    The near-field and a fish mark sit closer to the transducer. The bottom
    return on a sidescan ping is farther out. A bright sample only in the
    inner half is left in the water column.
    """
    count = len(samples)
    outer_from = max(surface_end + 1, int(count * 0.45))
    if outer_from >= count:
        return count
    segment = samples[outer_from:]
    peak_at = max(range(len(segment)), key=lambda index: segment[index])
    if segment[peak_at] < 140:
        return count
    return outer_from + peak_at


def _marks(samples: bytes, water_start: int, water_end: int, ping_index: int) -> list[_Mark]:
    if water_end - water_start < 4:
        return []
    column = list(samples[water_start:water_end])
    median = statistics.median(column)
    threshold = max(median + 50, 90)
    found: list[_Mark] = []
    index = water_start
    water = water_end - water_start
    while index < water_end:
        if samples[index] < threshold:
            index += 1
            continue
        end = index + 1
        while end < water_end and samples[end] >= threshold:
            end += 1
        span = end - index
        peak = max(samples[index:end])
        if span <= max(4, int(0.25 * water)) and peak >= median + 70:
            found.append(
                _Mark(
                    ping_index=ping_index,
                    start_bin=index,
                    end_bin=end - 1,
                    peak=int(peak),
                    center=(index + end - 1) / 2.0,
                )
            )
        index = end
    return found


def _range_m(ping: Ping, center: float) -> float:
    count = len(ping.samples)
    if count <= 0:
        return 0.0
    fraction = center / count
    return ping.upper_m + (ping.lower_m - ping.upper_m) * fraction


def _thickness_cm(ping: Ping, mark: _Mark) -> float:
    count = len(ping.samples)
    if count <= 0:
        return 0.0
    meters = (mark.end_bin - mark.start_bin + 1) / count * abs(ping.lower_m - ping.upper_m)
    return meters * 100.0
