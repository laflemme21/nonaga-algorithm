import argparse
import contextlib
import json
import platform
import shutil
import statistics
import subprocess
import sys
import time
import uuid
import io
from datetime import datetime, timezone
from pathlib import Path

RECORD_TYPES = {"run_start", "sample", "aggregate", "run_end"}
METRIC_ORIGINS = {"exact", "partial", "estimated", "error"}


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def append_record(ledger_path: Path, record: dict) -> None:
    with ledger_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=True) + "\n")


def validate_base_record(record: dict) -> None:
    required = [
        "run_id",
        "ts_utc",
        "record_type",
        "run_description",
        "commit_hash",
        "adapter_id",
        "fixture_id",
        "depth",
        "time_budget_ms",
        "metric_origin",
    ]
    missing = [k for k in required if k not in record]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    if record["record_type"] not in RECORD_TYPES:
        raise ValueError(f"Invalid record_type: {record['record_type']}")

    if record["metric_origin"] not in METRIC_ORIGINS:
        raise ValueError(f"Invalid metric_origin: {record['metric_origin']}")

    if not str(record["run_description"]).strip():
        raise ValueError("run_description cannot be empty")


def parse_depths(value: str) -> list[int]:
    depths = [int(v.strip()) for v in value.split(",") if v.strip()]
    if not depths:
        raise ValueError("At least one depth is required.")
    return depths


def ensure_worktree(repo_root: Path, commit_hash: str, worktree_path: Path) -> None:
    if worktree_path.exists():
        return
    subprocess.check_call(
        ["git", "worktree", "add", "--detach", str(worktree_path), commit_hash],
        cwd=repo_root,
    )


def cleanup_worktree(repo_root: Path, worktree_path: Path) -> None:
    if not worktree_path.exists():
        return
    try:
        # Run removal through cmd to avoid interactive retry prompts on Windows.
        subprocess.check_call(
            ["cmd", "/c", "git", "worktree", "remove", "--force", str(worktree_path)],
            cwd=repo_root,
        )
    except subprocess.CalledProcessError:
        shutil.rmtree(worktree_path, ignore_errors=True)


def run_legacy_iteration(depth: int, legacy_path: Path) -> tuple[float, int]:
    if str(legacy_path) not in sys.path:
        sys.path.insert(0, str(legacy_path))

    from AI import AI, load_parameters  # type: ignore
    from nonaga_logic import NonagaLogic  # type: ignore

    params = load_parameters()
    ai = AI(params, depth=depth)

    leaf_count = {"value": 0}
    original_cost = ai.cost_function

    def wrapped_cost(game_state):
        leaf_count["value"] += 1
        return original_cost(game_state)

    ai.cost_function = wrapped_cost

    logic = NonagaLogic(None, None)
    start = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        ai.get_best_move(logic)
    elapsed = time.perf_counter() - start
    return elapsed, int(leaf_count["value"])


def run_sample(depth: int, time_budget_ms: int, legacy_path: Path) -> dict:
    start = time.perf_counter()
    deadline = start + (time_budget_ms / 1000.0)

    iterations = 0
    elapsed_total = 0.0
    estimated_evaluated_nodes = 0

    while True:
        elapsed, leaf_estimate = run_legacy_iteration(depth=depth, legacy_path=legacy_path)
        elapsed_total += elapsed
        estimated_evaluated_nodes += leaf_estimate
        iterations += 1

        if time.perf_counter() >= deadline:
            break

    nps = None
    if elapsed_total > 0:
        nps = estimated_evaluated_nodes / elapsed_total

    return {
        "status": "ok",
        "iterations": iterations,
        "elapsed_seconds": elapsed_total,
        "evaluated_nodes": estimated_evaluated_nodes,
        "leaf_nodes": estimated_evaluated_nodes,
        "total_nodes": None,
        "nps": nps,
        "coverage_ratio": None,
        "pruning_ratio": None,
        "supports_exact_evaluated_nodes": False,
        "supports_exact_total_nodes": False,
        "metric_origin": "estimated",
        "error_stage": None,
        "error_msg": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Legacy benchmark runner for commit a11ef69 with JSONL schema parity."
    )
    parser.add_argument("--description", type=str, default="", help="User-authored run description.")
    parser.add_argument("--ledger", type=str, default="benchmark_ledger.jsonl")
    parser.add_argument("--depths", type=str, default="1,2")
    parser.add_argument("--time-budget-ms", type=int, default=2000)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--commit", type=str, default="a11ef69")
    parser.add_argument(
        "--worktree-dir",
        type=str,
        default=".tmp_legacy_a11ef69",
        help="Temporary detached worktree directory for the legacy commit.",
    )
    parser.add_argument(
        "--cleanup-worktree",
        action="store_true",
        help="Try to remove the temporary worktree at the end (can fail on Windows due to file locks).",
    )
    args = parser.parse_args()

    run_description = args.description.strip()
    if not run_description:
        run_description = input("Type run description: ").strip()
    if not run_description:
        raise ValueError("run_description is required.")

    repo_root = Path(__file__).resolve().parent
    ledger_path = (repo_root / args.ledger).resolve()
    worktree_path = (repo_root / args.worktree_dir).resolve()
    depths = parse_depths(args.depths)

    ensure_worktree(repo_root=repo_root, commit_hash=args.commit, worktree_path=worktree_path)
    legacy_path = worktree_path / "My Nonaga"
    if not legacy_path.exists():
        raise RuntimeError(f"Legacy module path not found in commit {args.commit}: {legacy_path}")

    run_id = str(uuid.uuid4())
    adapter_id = "legacy_a11ef69"
    commit_hash = args.commit

    run_start = {
        "run_id": run_id,
        "ts_utc": now_utc_iso(),
        "record_type": "run_start",
        "run_description": run_description,
        "commit_hash": commit_hash,
        "adapter_id": adapter_id,
        "fixture_id": "legacy_initial_board",
        "depth": -1,
        "time_budget_ms": 0,
        "metric_origin": "estimated",
        "commit_date_utc": "",
        "machine_os": platform.platform(),
        "python_version": sys.version.split()[0],
        "benchmark_version": "legacy_v1",
        "fixture_manifest_id": "legacy_initial_board_only",
        "default_depths": depths,
        "default_time_budget_ms": args.time_budget_ms,
    }
    validate_base_record(run_start)
    append_record(ledger_path, run_start)

    samples_written = 0
    aggregates_written = 0

    for depth in depths:
        sample_rows = []
        for idx in range(args.samples):
            try:
                sample_data = run_sample(depth=depth, time_budget_ms=args.time_budget_ms, legacy_path=legacy_path)
            except Exception as exc:
                sample_data = {
                    "status": "error",
                    "iterations": 0,
                    "elapsed_seconds": 0.0,
                    "evaluated_nodes": None,
                    "leaf_nodes": None,
                    "total_nodes": None,
                    "nps": None,
                    "coverage_ratio": None,
                    "pruning_ratio": None,
                    "supports_exact_evaluated_nodes": False,
                    "supports_exact_total_nodes": False,
                    "metric_origin": "error",
                    "error_stage": "search",
                    "error_msg": str(exc),
                }

            sample_row = {
                "run_id": run_id,
                "ts_utc": now_utc_iso(),
                "record_type": "sample",
                "run_description": run_description,
                "commit_hash": commit_hash,
                "adapter_id": adapter_id,
                "fixture_id": "legacy_initial_board",
                "depth": depth,
                "time_budget_ms": args.time_budget_ms,
                "metric_origin": sample_data["metric_origin"],
                "sample_index": idx,
                "elapsed_seconds": sample_data["elapsed_seconds"],
                "evaluated_nodes": sample_data["evaluated_nodes"],
                "leaf_nodes": sample_data["leaf_nodes"],
                "total_nodes": sample_data["total_nodes"],
                "nps": sample_data["nps"],
                "coverage_ratio": sample_data["coverage_ratio"],
                "pruning_ratio": sample_data["pruning_ratio"],
                "status": sample_data["status"],
                "error_stage": sample_data["error_stage"],
                "error_msg": sample_data["error_msg"],
                "supports_exact_evaluated_nodes": sample_data["supports_exact_evaluated_nodes"],
                "supports_exact_total_nodes": sample_data["supports_exact_total_nodes"],
                "iterations": sample_data["iterations"],
            }
            validate_base_record(sample_row)
            append_record(ledger_path, sample_row)
            samples_written += 1
            sample_rows.append(sample_row)

        ok_rows = [r for r in sample_rows if r["status"] == "ok" and r["nps"] is not None]
        if ok_rows:
            nps_values = [r["nps"] for r in ok_rows]
            elapsed_values = [r["elapsed_seconds"] for r in ok_rows]
            eval_values = [r["evaluated_nodes"] for r in ok_rows if r["evaluated_nodes"] is not None]

            agg = {
                "run_id": run_id,
                "ts_utc": now_utc_iso(),
                "record_type": "aggregate",
                "run_description": run_description,
                "commit_hash": commit_hash,
                "adapter_id": adapter_id,
                "fixture_id": "legacy_initial_board",
                "depth": depth,
                "time_budget_ms": args.time_budget_ms,
                "metric_origin": "estimated",
                "sample_count": len(ok_rows),
                "elapsed_seconds_mean": statistics.mean(elapsed_values),
                "evaluated_nodes_mean": statistics.mean(eval_values) if eval_values else None,
                "total_nodes_mean": None,
                "nps_mean": statistics.mean(nps_values),
                "nps_median": statistics.median(nps_values),
                "nps_stdev": statistics.stdev(nps_values) if len(nps_values) > 1 else 0.0,
                "coverage_ratio_mean": None,
                "pruning_ratio_mean": None,
            }
            validate_base_record(agg)
            append_record(ledger_path, agg)
            aggregates_written += 1

    run_end = {
        "run_id": run_id,
        "ts_utc": now_utc_iso(),
        "record_type": "run_end",
        "run_description": run_description,
        "commit_hash": commit_hash,
        "adapter_id": adapter_id,
        "fixture_id": "legacy_initial_board",
        "depth": -1,
        "time_budget_ms": 0,
        "metric_origin": "estimated",
        "commits_attempted": 1,
        "commits_succeeded": 1,
        "commits_failed": 0,
        "samples_written": samples_written,
        "aggregates_written": aggregates_written,
    }
    validate_base_record(run_end)
    append_record(ledger_path, run_end)

    if args.cleanup_worktree:
        cleanup_worktree(repo_root=repo_root, worktree_path=worktree_path)

    print(f"Ledger written to {ledger_path}")
    print(f"legacy commit={commit_hash}, run_id={run_id}, samples={samples_written}, aggregates={aggregates_written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
