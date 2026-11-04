"""Command line for the virtual (and later the Pi) hydrophone node."""

from __future__ import annotations

import argparse
import logging
import signal
import sys

from hydrophone_node import __version__
from hydrophone_node.config import load_config
from hydrophone_node.detect.registry import build_detector
from hydrophone_node.pipeline import run
from hydrophone_node.publish.dry_run import DryRunPublisher
from hydrophone_node.publish.rows import node_row
from hydrophone_node.publish.supabase import SupabasePublisher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hydrophone-node",
        description=(
            "Hudson River hydrophone node. Replays a folder or the public NOAA "
            "NCEI bucket, or synthesizes sturgeon, drum, and toadfish calls, "
            "then publishes 60 s segments. The same command runs on a Raspberry Pi "
            "with an Aquarian H2a when source.kind is device."
        ),
    )
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print and write JSON locally; do not call Supabase",
    )
    parser.add_argument(
        "--replay-speed",
        type=float,
        default=None,
        help="1 is real time, 10 is ten times faster, 0 is as fast as possible",
    )
    parser.add_argument(
        "--max-segments", type=int, default=None, help="stop after N segments"
    )
    parser.add_argument("--output-dir", default=None, help="dry-run output directory")
    parser.add_argument(
        "--version", action="version", version=f"hydrophone-node {__version__}"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    config = load_config(args.config)
    if args.replay_speed is not None:
        if args.replay_speed < 0:
            raise SystemExit("replay-speed must be >= 0")
        config.replay_speed = args.replay_speed
    if args.output_dir:
        config.output_dir = args.output_dir

    if args.dry_run:
        publisher = DryRunPublisher(config.output_dir)
    else:
        publisher = SupabasePublisher(
            config.supabase.url,
            config.supabase.service_role_key,
            config.supabase.audio_bucket,
        )

    detector = build_detector(config.detector.name, config.detector.entrypoint)

    def _shutdown(signum, _frame):
        logging.getLogger(__name__).info("signal %s, sending heartbeat", signum)
        try:
            publisher.heartbeat(node_row(config))
        finally:
            publisher.close()
            raise SystemExit(0)

    previous_handlers = {
        signal.SIGTERM: signal.getsignal(signal.SIGTERM),
        signal.SIGINT: signal.getsignal(signal.SIGINT),
    }
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    try:
        produced = run(config, publisher, detector, max_segments=args.max_segments)
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
    logging.getLogger(__name__).info("published %s segment(s)", produced)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
