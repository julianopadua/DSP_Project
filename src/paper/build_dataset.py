"""Entry point para construir features A0-A3 do paper."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from src.config import PAPER_PROCESSED_DIR, ensure_data_dirs, mitdb_record_dir
from src.paper.constants import ABLATION_STAGES, PACED_HEAVY_RECORDS, VALID_BEAT_SYMBOLS
from src.paper.dataset import (
    assert_same_beat_population,
    build_stage_feature_frames,
    interpatient_record_split,
    selected_records,
)

logger = logging.getLogger(__name__)


def stage_filename(stage_key: str, stage_label: str) -> str:
    return f"features_{stage_key}_{stage_label}.csv"


def parse_record_list(value: str | None, split: str) -> tuple[str, ...]:
    if value:
        return tuple(part.strip() for part in value.split(",") if part.strip())
    return selected_records(split)


def write_outputs(stage_frames, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for stage in ABLATION_STAGES:
        frame = stage_frames[stage.key]
        path = output_dir / stage_filename(stage.key, stage.label)
        frame.to_csv(path, index=False)
        logger.info("Salvo %s linhas em %s", len(frame), path)

    manifest_cols = [
        "beat_id",
        "record",
        "split",
        "sample",
        "time_s",
        "ann_symbol",
        "label_binary",
        "channel",
        "fs_hz",
        "start_sample",
        "end_sample",
        "rr_prev_s",
        "rr_next_s",
    ]
    stage_frames["A0"][manifest_cols].to_csv(output_dir / "beat_manifest.csv", index=False)


def write_protocol_summary(stage_frames, output_dir: Path, records: tuple[str, ...]) -> None:
    groups = interpatient_record_split()
    summary = {
        "records": list(records),
        "train_records": list(groups["train"]),
        "test_records": list(groups["test"]),
        "excluded_paced_heavy_records": sorted(PACED_HEAVY_RECORDS),
        "valid_beat_symbols_v1": sorted(VALID_BEAT_SYMBOLS),
        "stage_rows": {stage: int(len(frame)) for stage, frame in stage_frames.items()},
        "label_counts": {
            str(k): int(v)
            for k, v in stage_frames["A0"]["label_binary"].value_counts().sort_index().items()
        },
        "symbol_counts": {
            str(k): int(v)
            for k, v in stage_frames["A0"]["ann_symbol"].value_counts().sort_index().items()
        },
    }
    (output_dir / "protocol_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Constroi features por batimento para as ablacoes A0-A3 do paper.",
    )
    parser.add_argument("--split", choices=("all", "train", "test"), default="all")
    parser.add_argument(
        "--records",
        default=None,
        help="Lista separada por virgula. Se omitida, usa o split informado.",
    )
    parser.add_argument("--max-records", type=int, default=None)
    parser.add_argument("--max-beats-per-record", type=int, default=None)
    parser.add_argument("--pre-s", type=float, default=0.25)
    parser.add_argument("--post-s", type=float, default=0.45)
    parser.add_argument("--output-dir", type=Path, default=PAPER_PROCESSED_DIR)
    parser.add_argument("-q", "--quiet", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ensure_data_dirs()
    try:
        base_dir = mitdb_record_dir()
        records = parse_record_list(args.records, args.split)
        if args.max_records is not None:
            records = records[: args.max_records]
        logger.info("Construindo dataset com %d registros em %s", len(records), base_dir)
        stage_frames = build_stage_feature_frames(
            records=records,
            base_dir=base_dir,
            pre_s=args.pre_s,
            post_s=args.post_s,
            max_beats_per_record=args.max_beats_per_record,
        )
        assert_same_beat_population(stage_frames)
        write_outputs(stage_frames, args.output_dir)
        write_protocol_summary(stage_frames, args.output_dir, records)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Falha ao construir dataset: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
