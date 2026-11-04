"""Command line for the synthetic sonar node."""

from __future__ import annotations

import argparse
import logging
import sys

from sonar_node import __version__
from sonar_node.classify.registry import build_classifier
from sonar_node.config import load_config
from sonar_node.pipeline import run
from sonar_node.publish.dry_run import DryRunPublisher
from sonar_node.publish.supabase import SupabasePublisher


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sonar-node",
        description=(
            "Synthetic Hudson River sonar node. Draws tracks for Atlantic "
            "sturgeon, striped bass, river herring, and American shad, "
            "classifies them, and publishes sonar_tracks. No ARIS is attached."
        ),
    )
    parser.add_argument("--config", required=True, help="YAML config path")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="write JSON locally; do not call Supabase",
    )
    parser.add_argument(
        "--max-tracks",
        type=int,
        default=None,
        help="stop after N tracks (the hour window is still generated)",
    )
    parser.add_argument("--output-dir", default=None, help="dry-run output directory")
    parser.add_argument(
        "--version", action="version", version=f"sonar-node {__version__}"
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
    if args.output_dir:
        config.output_dir = args.output_dir
    if args.dry_run:
        publisher = DryRunPublisher(config.output_dir)
    else:
        publisher = SupabasePublisher(
            config.supabase.url,
            config.supabase.service_role_key,
            config.supabase.sonar_bucket,
        )
    classifier = build_classifier(config.classifier.name, config.classifier.entrypoint)
    produced = run(config, publisher, classifier, max_tracks=args.max_tracks)
    logging.getLogger(__name__).info("published %s track(s)", produced)
    return 0
