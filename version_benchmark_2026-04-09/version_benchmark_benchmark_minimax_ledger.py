import argparse
import json
import multiprocessing as mp
import platform
import statistics
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

RECORD_TYPES = {"run_start", "sample", "aggregate", "run_end"}
METRIC_ORIGINS = {"exact", "partial", "estimated", "error"}


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def get_commit_hash() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True)
        return out.strip()
    except Exception:
        return "workspace"


def get_commit_date_utc() -> str:
    try:
        out = subprocess.check_output(
            ["git", "show", "-s", "--format=%cI", "HEAD"], text=True)
        return out.strip()
    except Exception:
        return ""


def parse_csv_str(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def parse_depths(value: str) -> list[int]:
    depths = [int(v.strip()) for v in value.split(",") if v.strip()]
    if not depths:
        raise ValueError("At least one depth is required.")
    return depths


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


def load_logic_from_state(state_path: Path):
    from nonaga_constants import RED, PIECE_TO_MOVE
    from nonaga_logic import NonagaLogic

    with state_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    tiles = [(t[0], t[1]) for t in data["board"]["tiles"]]
    rp = [(p[0], p[1]) for p in data["board"]["pieces"] if p[3] == RED]
    bp = [(p[0], p[1]) for p in data["board"]["pieces"] if p[3] != RED]
    cp = data.get("current_player", 0)

    logic = NonagaLogic(None, None)
    logic.load_board_state(tiles, rp, bp, cp, PIECE_TO_MOVE)
    return logic


def _compute_total_nodes_worker(
    repo_root_str: str,
    fixture_path_str: str,
    depth: int,
    output_queue,
):
    try:
        repo_root = Path(repo_root_str)
        fixture_path = Path(fixture_path_str)
        nonaga_dir = repo_root / "NonagaGame"
        if str(nonaga_dir) not in sys.path:
            sys.path.insert(0, str(nonaga_dir))

        from AI import AI
        from nonaga_constants import AI_PARAM, BLACK

        ai = AI(AI_PARAM, depth=depth, color=BLACK)
        logic_for_total = load_logic_from_state(fixture_path)
        total_nodes = int(ai.count_total_nodes(logic_for_total))
        output_queue.put({"ok": True, "total_nodes": total_nodes})
    except Exception as exc:
        output_queue.put({"ok": False, "error": str(exc)})


def compute_total_nodes_with_timeout(
    repo_root: Path,
    fixture_path: Path,
    depth: int,
    timeout_seconds: float,
) -> tuple[int | None, str | None]:
    ctx = mp.get_context("spawn")
    output_queue = ctx.Queue()
    process = ctx.Process(
        target=_compute_total_nodes_worker,
        args=(str(repo_root), str(fixture_path), depth, output_queue),
    )
    process.start()
    process.join(timeout_seconds)

    if process.is_alive():
        process.terminate()
        process.join()
        return None, f"timeout_after_{timeout_seconds:.1f}s"

    if output_queue.empty():
        return None, "no_result"

    result = output_queue.get()
    if result.get("ok"):
        return int(result["total_nodes"]), None

    return None, result.get("error", "unknown_error")


def run_sample(ai, fixture_path: Path, depth: int, time_budget_ms: int, total_nodes_exact: int | None) -> dict:
    start = time.perf_counter()
    deadline = start + (time_budget_ms / 1000.0)
    iterations = 0

    ai.depth = depth
    ai.reset_search_counters()

    while True:
        logic = load_logic_from_state(fixture_path)
        ai.get_best_move(logic)
        iterations += 1

        if time.perf_counter() >= deadline:
            break

    elapsed = time.perf_counter() - start
    counters = ai.get_search_counters()
    evaluated_nodes = counters.get("evaluated_nodes")
    leaf_nodes = counters.get("leaf_nodes")
    total_nodes = total_nodes_exact

    nps = None
    if elapsed > 0 and evaluated_nodes is not None:
        nps = evaluated_nodes / elapsed

    coverage_ratio = None
    pruning_ratio = None
    if evaluated_nodes is not None and total_nodes is not None and total_nodes > 0 and iterations > 0:
        coverage_ratio = evaluated_nodes / (total_nodes * iterations)
        pruning_ratio = max(0.0, 1.0 - coverage_ratio)

    supports_exact_total_nodes = total_nodes is not None
    metric_origin = "exact" if supports_exact_total_nodes else "partial"

    return {
        "status": "ok",
        "version_search_iterations": iterations,
        "version_search_elapsed_seconds": elapsed,
        "evaluated_nodes": evaluated_nodes,
        "leaf_nodes": leaf_nodes,
        "total_nodes": total_nodes,
        "version_search_nps": nps,
        "coverage_ratio": coverage_ratio,
        "pruning_ratio": pruning_ratio,
        "supports_exact_evaluated_nodes": True,
        "supports_exact_total_nodes": supports_exact_total_nodes,
        "metric_origin": metric_origin,
        "error_stage": None,
        "error_msg": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fast JSONL benchmark ledger for minimax.")
    parser.add_argument("--description", type=str, default="",
                        help="User-authored run description.")
    parser.add_argument("--ledger", type=str, default="benchmark_ledger.jsonl")
    parser.add_argument("--fixtures", type=str,
                        default="saved_board.json,saved_board_backup.json")
    parser.add_argument("--depths", type=str, default="1,2,3")
    parser.add_argument("--time-budget-ms", type=int, default=6000)
    parser.add_argument("--samples", type=int, default=5)
    parser.add_argument(
        "--exact-total-nodes",
        action="store_true",
        help="Enable exact full-tree total node counting (can be expensive).",
    )
    parser.add_argument(
        "--max-total-node-seconds",
        type=float,
        default=10.0,
        help="Timeout for exact total-node computation per fixture/depth.",
    )
    parser.add_argument(
        "--max-exact-total-depth",
        type=int,
        default=2,
        help="Only compute exact total nodes up to this depth.",
    )
    args = parser.parse_args()

    run_description = args.description.strip()
    if not run_description:
        run_description = input("Type run description: ").strip()
    if not run_description:
        raise ValueError("run_description is required.")

    repo_root = Path(__file__).resolve().parent
    nonaga_dir = repo_root / "NonagaGame"
    if str(nonaga_dir) not in sys.path:
        sys.path.insert(0, str(nonaga_dir))

    from AI import AI
    from nonaga_constants import AI_PARAM, BLACK

    run_id = str(uuid.uuid4())
    commit_hash = get_commit_hash()
    commit_date_utc = get_commit_date_utc()
    ledger_path = (repo_root / args.ledger).resolve()
    fixture_paths = [repo_root / p for p in parse_csv_str(args.fixtures)]
    depths = parse_depths(args.depths)

    adapter_id = "current_engine"
    benchmark_version = "v0"

    ai = AI(AI_PARAM, depth=max(depths), color=BLACK)

    if not hasattr(ai, "reset_search_counters"):
        raise RuntimeError(
            "Loaded AI extension does not expose benchmark counter APIs. "
            "Rebuild and deploy extensions with: "
            "python -c \"import sys; sys.path.insert(0, 'NonagaGame'); import compiler; compiler.compile_cython_files()\""
        )

    if not hasattr(ai, "count_total_nodes"):
        raise RuntimeError(
            "Loaded AI extension does not expose exact total-node API. "
            "Rebuild and deploy extensions with: "
            "python -c \"import sys; sys.path.insert(0, 'NonagaGame'); import compiler; compiler.compile_cython_files()\""
        )

    run_start = {
        "run_id": run_id,
        "ts_utc": now_utc_iso(),
        "record_type": "run_start",
        "run_description": run_description,
        "commit_hash": commit_hash,
        "adapter_id": adapter_id,
        "fixture_id": "all",
        "depth": -1,
        "time_budget_ms": 0,
        "metric_origin": "exact",
        "commit_date_utc": commit_date_utc,
        "machine_os": platform.platform(),
        "python_version": sys.version.split()[0],
        "benchmark_version": benchmark_version,
        "fixture_manifest_id": "hardcoded_v0",
        "default_depths": depths,
        "default_time_budget_ms": args.time_budget_ms,
    }
    validate_base_record(run_start)
    append_record(ledger_path, run_start)

    samples_written = 0
    aggregates_written = 0

    for fixture_path in fixture_paths:
        if not fixture_path.exists():
            sample_error = {
                "run_id": run_id,
                "ts_utc": now_utc_iso(),
                "record_type": "sample",
                "run_description": run_description,
                "commit_hash": commit_hash,
                "adapter_id": adapter_id,
                "fixture_id": fixture_path.name,
                "depth": -1,
                "time_budget_ms": args.time_budget_ms,
                "metric_origin": "error",
                "sample_index": 0,
                "version_search_elapsed_seconds": 0.0,
                "evaluated_nodes": None,
                "leaf_nodes": None,
                "total_nodes": None,
                "version_search_nps": None,
                "coverage_ratio": None,
                "pruning_ratio": None,
                "status": "error",
                "error_stage": "fixture_load",
                "error_msg": f"Fixture not found: {fixture_path}",
                "supports_exact_evaluated_nodes": False,
                "supports_exact_total_nodes": False,
            }
            validate_base_record(sample_error)
            append_record(ledger_path, sample_error)
            samples_written += 1
            continue

        for depth in depths:
            total_nodes_exact = None
            if args.exact_total_nodes and depth <= args.max_exact_total_depth:
                total_nodes_exact, _ = compute_total_nodes_with_timeout(
                    repo_root=repo_root,
                    fixture_path=fixture_path,
                    depth=depth,
                    timeout_seconds=args.max_total_node_seconds,
                )

            sample_rows = []
            for idx in range(args.samples):
                try:
                    sample_data = run_sample(
                        ai, fixture_path, depth, args.time_budget_ms, total_nodes_exact)
                except Exception as exc:
                    sample_data = {
                        "status": "error",
                        "version_search_iterations": 0,
                        "version_search_elapsed_seconds": 0.0,
                        "evaluated_nodes": None,
                        "leaf_nodes": None,
                        "total_nodes": total_nodes_exact,
                        "version_search_nps": None,
                        "coverage_ratio": None,
                        "pruning_ratio": None,
                        "supports_exact_evaluated_nodes": False,
                        "supports_exact_total_nodes": total_nodes_exact is not None,
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
                    "fixture_id": fixture_path.name,
                    "depth": depth,
                    "time_budget_ms": args.time_budget_ms,
                    "metric_origin": sample_data["metric_origin"],
                    "sample_index": idx,
                    "version_search_elapsed_seconds": sample_data["version_search_elapsed_seconds"],
                    "evaluated_nodes": sample_data["evaluated_nodes"],
                    "leaf_nodes": sample_data["leaf_nodes"],
                    "total_nodes": sample_data["total_nodes"],
                    "version_search_nps": sample_data["version_search_nps"],
                    "coverage_ratio": sample_data["coverage_ratio"],
                    "pruning_ratio": sample_data["pruning_ratio"],
                    "status": sample_data["status"],
                    "error_stage": sample_data["error_stage"],
                    "error_msg": sample_data["error_msg"],
                    "supports_exact_evaluated_nodes": sample_data["supports_exact_evaluated_nodes"],
                    "supports_exact_total_nodes": sample_data["supports_exact_total_nodes"],
                    "version_search_iterations": sample_data["version_search_iterations"],
                }
                validate_base_record(sample_row)
                append_record(ledger_path, sample_row)
                samples_written += 1
                sample_rows.append(sample_row)

            ok_rows = [r for r in sample_rows if r["status"]
                       == "ok" and r["version_search_nps"] is not None]
            if ok_rows:
                nps_values = [r["version_search_nps"] for r in ok_rows]
                elapsed_values = [r["version_search_elapsed_seconds"] for r in ok_rows]
                eval_values = [r["evaluated_nodes"]
                               for r in ok_rows if r["evaluated_nodes"] is not None]
                total_values = [r["total_nodes"]
                                for r in ok_rows if r["total_nodes"] is not None]
                coverage_values = [r["coverage_ratio"]
                                   for r in ok_rows if r["coverage_ratio"] is not None]
                pruning_values = [r["pruning_ratio"]
                                  for r in ok_rows if r["pruning_ratio"] is not None]
                all_exact_total = all(
                    r["supports_exact_total_nodes"] for r in ok_rows)

                agg = {
                    "run_id": run_id,
                    "ts_utc": now_utc_iso(),
                    "record_type": "aggregate",
                    "run_description": run_description,
                    "commit_hash": commit_hash,
                    "adapter_id": adapter_id,
                    "fixture_id": fixture_path.name,
                    "depth": depth,
                    "time_budget_ms": args.time_budget_ms,
                    "metric_origin": "exact" if all_exact_total else "partial",
                    "sample_count": len(ok_rows),
                    "version_search_elapsed_seconds_mean": statistics.mean(elapsed_values),
                    "evaluated_nodes_mean": statistics.mean(eval_values) if eval_values else None,
                    "total_nodes_mean": statistics.mean(total_values) if total_values else None,
                    "version_search_nps_mean": statistics.mean(nps_values),
                    "version_search_nps_median": statistics.median(nps_values),
                    "version_search_nps_stdev": statistics.stdev(nps_values) if len(nps_values) > 1 else 0.0,
                    "coverage_ratio_mean": statistics.mean(coverage_values) if coverage_values else None,
                    "pruning_ratio_mean": statistics.mean(pruning_values) if pruning_values else None,
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
        "fixture_id": "all",
        "depth": -1,
        "time_budget_ms": 0,
        "metric_origin": "exact",
        "commits_attempted": 1,
        "commits_succeeded": 1,
        "commits_failed": 0,
        "samples_written": samples_written,
        "aggregates_written": aggregates_written,
    }
    validate_base_record(run_end)
    append_record(ledger_path, run_end)

    print(f"Ledger written to {ledger_path}")
    print(
        f"run_id={run_id}, samples={samples_written}, aggregates={aggregates_written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
