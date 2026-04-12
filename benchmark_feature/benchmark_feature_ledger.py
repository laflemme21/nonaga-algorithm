import argparse
import contextlib
import io
import json
import os
import platform
import random
import re
import shutil
import statistics
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


RECORD_TYPES = {"run_start", "sample", "aggregate", "run_end"}
METRIC_ORIGINS = {"exact", "partial", "estimated", "error"}


@dataclass(frozen=True)
class Scenario:
    commit_hash: str
    engine: str
    ab_enabled: bool
    tt_enabled: bool

    @property
    def id(self) -> str:
        tt_tag = "na" if self.engine == "legacy_python" else ("on" if self.tt_enabled else "off")
        return f"{self.commit_hash}_ab_{'on' if self.ab_enabled else 'off'}_tt_{tt_tag}"

    @property
    def adapter_id(self) -> str:
        return f"feature_{self.engine}"


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_depths(value: str) -> list[int]:
    depths = [int(v.strip()) for v in value.split(",") if v.strip()]
    if not depths:
        raise ValueError("At least one depth is required.")
    return depths


def parse_csv_str(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _read_fixture_board_payload(state_path: Path):
    with state_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # Fixture format mirrors version benchmark board-state schema.
    tiles = [(t[0], t[1]) for t in data["board"]["tiles"]]
    current_player = int(data.get("current_player", 0))

    red_pieces = []
    black_pieces = []
    for piece in data["board"]["pieces"]:
        q = piece[0]
        r = piece[1]
        color = piece[3]
        if color == 0:
            red_pieces.append((q, r))
        else:
            black_pieces.append((q, r))

    return tiles, red_pieces, black_pieces, current_player


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


def _git_output(repo_root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo_root, text=True)


def get_commit_date_utc(repo_root: Path, commit_hash: str) -> str:
    try:
        return _git_output(repo_root, "show", "-s", "--format=%cI", commit_hash).strip()
    except Exception:
        return ""


def ensure_worktree(repo_root: Path, commit_hash: str, worktree_path: Path) -> None:
    if worktree_path.exists():
        cleanup_worktree(repo_root, worktree_path)
    subprocess.check_call(
        ["git", "worktree", "add", "--detach", str(worktree_path), commit_hash],
        cwd=repo_root,
    )


def cleanup_worktree(repo_root: Path, worktree_path: Path) -> None:
    if not worktree_path.exists():
        return
    try:
        subprocess.check_call(
            ["cmd", "/c", "git", "worktree", "remove", "--force", str(worktree_path)],
            cwd=repo_root,
        )
    except subprocess.CalledProcessError:
        shutil.rmtree(worktree_path, ignore_errors=True)


def detect_engine(repo_root: Path, commit_hash: str) -> str:
    files = _git_output(repo_root, "ls-tree", "-r", "--name-only", commit_hash)
    if "My Nonaga/AI.py" in files:
        return "legacy_python"
    if "NonagaGame/AI_core.c" in files:
        return "cython_core"
    raise RuntimeError(f"Unsupported commit layout for {commit_hash}")


def build_extensions(worktree_path: Path) -> None:
    env = os.environ.copy()
    env.pop("VSCMD_ARG_TGT_ARCH", None)
    env.pop("VSCMD_ARG_HOST_ARCH", None)
    env.pop("Platform", None)
    env.pop("PreferredToolArchitecture", None)
    subprocess.check_call(
        [sys.executable, "setup.py", "build_ext", "--inplace"],
        cwd=worktree_path,
        env=env,
    )


def _replace_or_raise(text: str, old: str, new: str, min_count: int, label: str) -> str:
    count = text.count(old)
    if count < min_count:
        raise RuntimeError(f"Expected at least {min_count} replacements for '{label}', got {count}.")
    return text.replace(old, new)


def patch_legacy_ai(worktree_path: Path, enable_ab: bool) -> None:
    if enable_ab:
        return

    ai_path = worktree_path / "My Nonaga" / "AI.py"
    text = ai_path.read_text(encoding="utf-8")
    patched, count = re.subn(
        r"if alpha >= beta:\n(\s*)break",
        r"if False and alpha >= beta:\n\1break",
        text,
    )
    if count < 2:
        raise RuntimeError(f"Expected to disable >=2 alpha-beta cutoffs in legacy AI, got {count}.")
    ai_path.write_text(patched, encoding="utf-8")


def ensure_cython_counter_instrumentation(worktree_path: Path) -> None:
    ai_core_h_path = worktree_path / "NonagaGame" / "AI_core.h"
    ai_core_c_path = worktree_path / "NonagaGame" / "AI_core.c"
    ai_pyx_path = worktree_path / "NonagaGame" / "AI.pyx"
    ai_pxd_path = worktree_path / "NonagaGame" / "AI.pxd"

    h_text = ai_core_h_path.read_text(encoding="utf-8")
    if "typedef struct AiSearchCounters" not in h_text:
        h_text = h_text.replace(
            "    Move2D ai_empty_move(void);\n",
            "    typedef struct AiSearchCounters\n"
            "    {\n"
            "        unsigned long long evaluated_nodes;\n"
            "        unsigned long long leaf_nodes;\n"
            "    } AiSearchCounters;\n\n"
            "    Move2D ai_empty_move(void);\n",
            1,
        )

    if "void ai_reset_search_counters(void);" not in h_text:
        h_text = h_text.replace(
            "    Move2D ai_empty_move(void);\n",
            "    Move2D ai_empty_move(void);\n"
            "    void ai_reset_search_counters(void);\n"
            "    AiSearchCounters ai_get_search_counters(void);\n",
            1,
        )

    ai_core_h_path.write_text(h_text, encoding="utf-8")

    c_text = ai_core_c_path.read_text(encoding="utf-8")
    if "static AiSearchCounters ai_search_counters" not in c_text:
        marker = "static int ai_tt_initialized = 0;\n"
        if marker not in c_text:
            raise RuntimeError("Unable to locate ai_tt_initialized marker for counter instrumentation")
        c_text = c_text.replace(
            marker,
            marker
            + "static AiSearchCounters ai_search_counters = {0ULL, 0ULL};\n\n"
            + "void ai_reset_search_counters(void)\n"
            + "{\n"
            + "    ai_search_counters.evaluated_nodes = 0ULL;\n"
            + "    ai_search_counters.leaf_nodes = 0ULL;\n"
            + "}\n\n"
            + "AiSearchCounters ai_get_search_counters(void)\n"
            + "{\n"
            + "    return ai_search_counters;\n"
            + "}\n\n",
            1,
        )

    if "ai_search_counters.evaluated_nodes += 1ULL;" not in c_text:
        c_text, replaced = re.subn(
            r"(int ai_cost_function\s*\(.*?\)\s*\{)",
            r"\1\n    ai_search_counters.evaluated_nodes += 1ULL;\n    ai_search_counters.leaf_nodes += 1ULL;",
            c_text,
            count=1,
            flags=re.S,
        )
        if replaced != 1:
            raise RuntimeError("Unable to inject ai_cost_function counter increments")

    ai_core_c_path.write_text(c_text, encoding="utf-8")

    ai_text = ai_pyx_path.read_text(encoding="utf-8")
    if "import time\n" not in ai_text:
        ai_text = ai_text.replace(
            "from nonaga_constants import RED, BLACK\n\n",
            "from nonaga_constants import RED, BLACK\nimport time\n\n",
            1,
        )

    if "ctypedef struct AiSearchCounters" not in ai_text:
        ai_text = ai_text.replace(
            "    ctypedef struct MinimaxResult:\n"
            "        int cost\n"
            "        Move2D piece_move\n"
            "        Move2D tile_move\n\n",
            "    ctypedef struct MinimaxResult:\n"
            "        int cost\n"
            "        Move2D piece_move\n"
            "        Move2D tile_move\n\n"
            "    ctypedef struct AiSearchCounters:\n"
            "        unsigned long long evaluated_nodes\n"
            "        unsigned long long leaf_nodes\n\n",
            1,
        )

    if "void ai_reset_search_counters()" not in ai_text:
        ai_text = ai_text.replace(
            "    void ai_init_tt()\n",
            "    void ai_init_tt()\n"
            "    void ai_reset_search_counters()\n"
            "    AiSearchCounters ai_get_search_counters()\n",
            1,
        )

    if "cpdef void reset_search_counters(self):" not in ai_text:
        ai_text = ai_text.replace(
            "    def execute_best_move(self, game_state: object):\n",
            "    cpdef void reset_search_counters(self):\n"
            "        ai_reset_search_counters()\n\n"
            "    cpdef dict get_search_counters(self):\n"
            "        cdef AiSearchCounters counters = ai_get_search_counters()\n"
            "        return {\n"
            "            \"evaluated_nodes\": int(counters.evaluated_nodes),\n"
            "            \"leaf_nodes\": int(counters.leaf_nodes),\n"
            "        }\n\n"
            "    def execute_best_move(self, game_state: object):\n",
            1,
        )

    if "cpdef tuple get_best_move_benchmark(self, game_state):" not in ai_text:
        ai_text = ai_text.replace(
            "    cpdef void reset_search_counters(self):\n",
            "    cpdef tuple get_best_move_benchmark(self, game_state):\n"
            "        cdef MinimaxResult result\n"
            "        cdef object best_piece_move = None\n"
            "        cdef object best_tile_move = None\n"
            "        cdef double t0\n"
            "        cdef double t1\n"
            "        cdef double t2\n\n"
            "        t0 = time.perf_counter()\n"
            "        ai_init_tt()\n"
            "        t1 = time.perf_counter()\n\n"
            "        result = self.search_iterative_deepening(\n"
            "            game_state,\n"
            "            self.depth,\n"
            "            True,\n"
            "            game_state.get_current_player()\n"
            "        )\n"
            "        t2 = time.perf_counter()\n\n"
            "        if result.piece_move.is_set:\n"
            "            best_piece_move = (\n"
            "                (result.piece_move.from_q, result.piece_move.from_r),\n"
            "                (result.piece_move.to_q, result.piece_move.to_r),\n"
            "            )\n"
            "        if result.tile_move.is_set:\n"
            "            best_tile_move = (\n"
            "                (result.tile_move.from_q, result.tile_move.from_r),\n"
            "                (result.tile_move.to_q, result.tile_move.to_r),\n"
            "            )\n\n"
            "        return (best_piece_move, best_tile_move, float(t1 - t0), float(t2 - t1))\n\n"
            "    cpdef void reset_search_counters(self):\n",
            1,
        )

    ai_pyx_path.write_text(ai_text, encoding="utf-8")

    if ai_pxd_path.exists():
        pxd_text = ai_pxd_path.read_text(encoding="utf-8")
        if "cpdef tuple get_best_move_benchmark(self, game_state)" not in pxd_text:
            pxd_text = pxd_text.replace(
                "    cpdef tuple get_best_move(self, game_state)\n",
                "    cpdef tuple get_best_move(self, game_state)\n"
                "    cpdef tuple get_best_move_benchmark(self, game_state)\n",
                1,
            )
        if "cpdef void reset_search_counters(self)" not in pxd_text:
            pxd_text = pxd_text.replace(
                "    cpdef tuple get_best_move(self, game_state)\n",
                "    cpdef tuple get_best_move(self, game_state)\n"
                "    cpdef void reset_search_counters(self)\n"
                "    cpdef dict get_search_counters(self)\n",
                1,
            )
        ai_pxd_path.write_text(pxd_text, encoding="utf-8")


def patch_cython_core(worktree_path: Path, enable_ab: bool, enable_tt: bool) -> None:
    ai_core_path = worktree_path / "NonagaGame" / "AI_core.c"
    ai_pyx_path = worktree_path / "NonagaGame" / "AI.pyx"

    # Backfill counter instrumentation for historical commits that expose no usable counters.
    ensure_cython_counter_instrumentation(worktree_path)

    core_text = ai_core_path.read_text(encoding="utf-8")

    if not enable_ab:
        core_text = _replace_or_raise(
            core_text,
            "if (alpha >= beta)",
            "if (0 && alpha >= beta)",
            min_count=4,
            label="alpha-beta cutoff",
        )

    if not enable_tt:
        core_text = _replace_or_raise(
            core_text,
            "current_hash = ai_compute_hash(board, *current_player, *turn_phase);",
            "current_hash = 0ULL;",
            min_count=2,
            label="tt hash compute",
        )
        core_text = _replace_or_raise(
            core_text,
            "if (tt_entry->hash == current_hash)",
            "if (0 && tt_entry->hash == current_hash)",
            min_count=2,
            label="tt hit check",
        )

    ai_core_path.write_text(core_text, encoding="utf-8")

    if not enable_tt:
        ai_text = ai_pyx_path.read_text(encoding="utf-8")
        ai_text = _replace_or_raise(
            ai_text,
            "        ai_init_tt()\n",
            "        # TT init disabled for this benchmark variant.\n",
            min_count=1,
            label="ai_init_tt call",
        )
        ai_pyx_path.write_text(ai_text, encoding="utf-8")


def prepare_variant_sources(scenario: Scenario, worktree_path: Path) -> None:
    if scenario.engine == "legacy_python":
        patch_legacy_ai(worktree_path, enable_ab=scenario.ab_enabled)
    elif scenario.engine == "cython_core":
        patch_cython_core(
            worktree_path,
            enable_ab=scenario.ab_enabled,
            enable_tt=scenario.tt_enabled,
        )
    else:
        raise RuntimeError(f"Unsupported engine for patching: {scenario.engine}")


def _position_key(pos_obj) -> tuple[int, int, int]:
    if hasattr(pos_obj, "get_position"):
        pos = pos_obj.get_position()
    else:
        pos = pos_obj

    if not isinstance(pos, (tuple, list)):
        raise RuntimeError(f"Unsupported coordinate type: {type(pos)}")

    if len(pos) >= 3:
        return int(pos[0]), int(pos[1]), int(pos[2])
    if len(pos) == 2:
        q = int(pos[0])
        r = int(pos[1])
        return q, r, -q - r

    raise RuntimeError(f"Unsupported coordinate length: {len(pos)}")


def _choose_first_mapping_move(move_map: dict):
    candidates = []
    for origin, destinations in move_map.items():
        if not destinations:
            continue
        sorted_destinations = sorted(list(destinations), key=_position_key)
        candidates.append((
            _position_key(origin),
            origin,
            sorted_destinations,
        ))

    if not candidates:
        return None, None

    candidates.sort(key=lambda item: item[0])
    _, origin, destinations = candidates[0]
    return origin, destinations[0]


def _worker_load_legacy_logic():
    from nonaga_logic import NonagaLogic

    # Use engine-native initial position for reproducible, fixture-independent runs.
    return NonagaLogic(None, None, new_game=True)


def _worker_load_legacy_logic_from_state(state_path: Path):
    from nonaga_constants import PIECE_TO_MOVE

    logic = _worker_load_legacy_logic()
    if not hasattr(logic, "load_board_state"):
        raise RuntimeError("legacy_logic_missing_load_board_state")

    tiles, rp, bp, cp = _read_fixture_board_payload(state_path)
    logic.load_board_state(tiles, rp, bp, cp, PIECE_TO_MOVE)
    return logic


def _worker_advance_first_turn_legacy(logic) -> bool:
    piece_origin, piece_dest = _choose_first_mapping_move(logic.get_all_valid_piece_moves_ai())
    if piece_origin is None:
        return False
    logic.move_piece(piece_origin, piece_dest)

    tile_origin, tile_dest = _choose_first_mapping_move(logic.get_all_valid_tile_moves_ai())
    if tile_origin is None:
        return False
    logic.move_tile(tile_origin, tile_dest)
    return True


def _worker_apply_ai_move_legacy(logic, best_piece_move, best_tile_move) -> bool:
    if best_piece_move is None or best_tile_move is None:
        return False
    try:
        piece_obj, piece_dest = best_piece_move
        tile_obj, tile_dest = best_tile_move
        logic.move_piece(piece_obj, piece_dest)
        logic.move_tile(tile_obj, tile_dest)
        return True
    except Exception:
        return False


def _worker_legacy_search_once(ai, logic) -> tuple[float, int, object, object]:
    leaf_count = {"value": 0}
    original_cost = ai.cost_function

    def wrapped_cost(game_state):
        leaf_count["value"] += 1
        return original_cost(game_state)

    ai.cost_function = wrapped_cost
    start = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        best_piece, best_tile = ai.get_best_move(logic)
    elapsed = time.perf_counter() - start
    ai.cost_function = original_cost
    return elapsed, int(leaf_count["value"]), best_piece, best_tile


def _worker_should_stop(
    *,
    fixed_iterations: int,
    iterations: int,
    budget_mode: str,
    budget_seconds: float,
    search_budget_consumed: float,
    wall_deadline: float,
) -> bool:
    if fixed_iterations > 0:
        return iterations >= fixed_iterations
    if budget_mode == "search":
        return search_budget_consumed >= budget_seconds
    return time.perf_counter() >= wall_deadline


def _worker_run_legacy(payload: dict) -> list[dict]:
    depths = list(payload["depths"])
    samples = int(payload["samples"])
    time_budget_ms = int(payload["time_budget_ms"])
    deterministic_turns_per_iteration = int(payload["deterministic_turns_per_iteration"])
    max_moves_per_game = int(payload["max_moves_per_game"])
    fixed_iterations = int(payload.get("fixed_iterations", 0))
    budget_mode = str(payload.get("budget_mode", "wall")).strip().lower()
    position_source = str(payload.get("position_source", "initial_position_only")).strip().lower()
    fixture_paths = [Path(p) for p in payload.get("fixture_paths", [])]
    if budget_mode not in {"wall", "search"}:
        raise RuntimeError(f"Unsupported budget_mode: {budget_mode}")
    if position_source not in {"initial_position_only", "fixture_replay"}:
        raise RuntimeError(f"Unsupported position_source: {position_source}")
    if position_source == "fixture_replay" and not fixture_paths:
        raise RuntimeError("fixture_replay requires non-empty fixture_paths")

    from AI import AI, load_parameters
    from nonaga_constants import RED

    params = load_parameters()
    results = []

    for depth in depths:
        ai = AI(params, depth=depth)

        for sample_index in range(samples):
            logic = _worker_load_legacy_logic()
            moves_played = 0
            fixture_index = 0

            elapsed_total = 0.0
            evaluated_nodes_total = 0
            iterations = 0
            minimax_elapsed_total = 0.0
            tt_init_elapsed_total = 0.0
            search_budget_consumed = 0.0

            budget_seconds = time_budget_ms / 1000.0
            wall_deadline = time.perf_counter() + budget_seconds

            while True:
                if position_source == "fixture_replay":
                    state_path = fixture_paths[fixture_index % len(fixture_paths)]
                    fixture_index += 1
                    logic = _worker_load_legacy_logic_from_state(state_path)
                else:
                    for _ in range(deterministic_turns_per_iteration):
                        if not _worker_advance_first_turn_legacy(logic):
                            logic = _worker_load_legacy_logic()
                            moves_played = 0
                            break
                        moves_played += 1
                        if logic.check_win_condition(RED) or logic.check_win_condition(1 - RED) or moves_played >= max_moves_per_game:
                            logic = _worker_load_legacy_logic()
                            moves_played = 0
                            break

                elapsed, leaves, best_piece, best_tile = _worker_legacy_search_once(ai, logic)
                elapsed_total += elapsed
                minimax_elapsed_total += elapsed
                search_budget_consumed += elapsed
                evaluated_nodes_total += leaves
                iterations += 1

                if position_source != "fixture_replay":
                    if not _worker_apply_ai_move_legacy(logic, best_piece, best_tile):
                        logic = _worker_load_legacy_logic()
                        moves_played = 0
                    else:
                        moves_played += 1
                        if logic.check_win_condition(RED) or logic.check_win_condition(1 - RED) or moves_played >= max_moves_per_game:
                            logic = _worker_load_legacy_logic()
                            moves_played = 0

                if _worker_should_stop(
                    fixed_iterations=fixed_iterations,
                    iterations=iterations,
                    budget_mode=budget_mode,
                    budget_seconds=budget_seconds,
                    search_budget_consumed=search_budget_consumed,
                    wall_deadline=wall_deadline,
                ):
                    break

            sps = (iterations / elapsed_total) if elapsed_total > 0 else None
            seconds_per_iteration = (elapsed_total / iterations) if iterations > 0 else None
            nps = (evaluated_nodes_total / elapsed_total) if elapsed_total > 0 else None
            nps_minimax = (evaluated_nodes_total / minimax_elapsed_total) if minimax_elapsed_total > 0 else None
            elapsed_seconds_nonminimax = max(0.0, elapsed_total - minimax_elapsed_total)
            results.append(
                {
                    "depth": depth,
                    "sample_index": sample_index,
                    "status": "ok",
                    "iterations": iterations,
                    "elapsed_seconds": elapsed_total,
                    "evaluated_nodes": evaluated_nodes_total,
                    "leaf_nodes": evaluated_nodes_total,
                    "total_nodes": None,
                    "nps": nps,
                    "nps_minimax": nps_minimax,
                    "sps": sps,
                    "seconds_per_iteration": seconds_per_iteration,
                    "elapsed_seconds_minimax": minimax_elapsed_total,
                    "elapsed_seconds_tt_init": tt_init_elapsed_total,
                    "elapsed_seconds_nonminimax": elapsed_seconds_nonminimax,
                    "coverage_ratio": None,
                    "pruning_ratio": None,
                    "supports_exact_evaluated_nodes": False,
                    "supports_exact_total_nodes": False,
                    "metric_origin": "estimated",
                    "nps_basis": "estimated_evaluated_nodes",
                    "nps_reason": "estimated_nodes_from_cost_calls",
                    "node_counter_status": "estimated_from_cost_calls",
                    "evaluated_nodes_counter_raw": None,
                    "leaf_nodes_counter_raw": None,
                    "error_stage": None,
                    "error_msg": None,
                }
            )

    return results


def _worker_load_cython_logic():
    from nonaga_logic import NonagaLogic

    # Use engine-native initial position for reproducible, fixture-independent runs.
    return NonagaLogic(None, None)


def _worker_load_cython_logic_from_state(state_path: Path):
    from nonaga_constants import PIECE_TO_MOVE

    logic = _worker_load_cython_logic()
    tiles, rp, bp, cp = _read_fixture_board_payload(state_path)
    logic.load_board_state(tiles, rp, bp, cp, PIECE_TO_MOVE)
    return logic


def _worker_advance_first_turn_cython(logic) -> bool:
    piece_origin, piece_dest = _choose_first_mapping_move(logic.get_all_valid_piece_moves())
    if piece_origin is None:
        return False
    logic.move_piece_py((piece_origin[0], piece_origin[1]), (piece_dest[0], piece_dest[1]))

    tile_origin, tile_dest = _choose_first_mapping_move(logic.get_all_valid_tile_moves())
    if tile_origin is None:
        return False
    logic.move_tile_py((tile_origin[0], tile_origin[1]), (tile_dest[0], tile_dest[1]))
    return True


def _worker_apply_ai_move_cython(logic, best_piece_move, best_tile_move) -> bool:
    if best_piece_move is None or best_tile_move is None:
        return False
    try:
        logic.move_piece_py(best_piece_move[0], best_piece_move[1])
        logic.move_tile_py(best_tile_move[0], best_tile_move[1])
        return True
    except Exception:
        return False


def _worker_run_cython(payload: dict) -> list[dict]:
    depths = list(payload["depths"])
    samples = int(payload["samples"])
    time_budget_ms = int(payload["time_budget_ms"])
    deterministic_turns_per_iteration = int(payload["deterministic_turns_per_iteration"])
    max_moves_per_game = int(payload["max_moves_per_game"])
    fixed_iterations = int(payload.get("fixed_iterations", 0))
    budget_mode = str(payload.get("budget_mode", "wall")).strip().lower()
    position_source = str(payload.get("position_source", "initial_position_only")).strip().lower()
    fixture_paths = [Path(p) for p in payload.get("fixture_paths", [])]
    if budget_mode not in {"wall", "search"}:
        raise RuntimeError(f"Unsupported budget_mode: {budget_mode}")
    if position_source not in {"initial_position_only", "fixture_replay"}:
        raise RuntimeError(f"Unsupported position_source: {position_source}")
    if position_source == "fixture_replay" and not fixture_paths:
        raise RuntimeError("fixture_replay requires non-empty fixture_paths")

    from AI import AI
    from nonaga_constants import AI_PARAM, BLACK, RED

    results = []

    for depth in depths:
        ai = AI(AI_PARAM, depth=depth, color=BLACK)

        for sample_index in range(samples):
            logic = _worker_load_cython_logic()
            moves_played = 0
            fixture_index = 0

            elapsed_total = 0.0
            evaluated_nodes_total = 0
            leaf_nodes_total = 0
            iterations = 0
            minimax_elapsed_total = 0.0
            tt_init_elapsed_total = 0.0
            search_budget_consumed = 0.0

            budget_seconds = time_budget_ms / 1000.0
            wall_deadline = time.perf_counter() + budget_seconds

            while True:
                if position_source == "fixture_replay":
                    state_path = fixture_paths[fixture_index % len(fixture_paths)]
                    fixture_index += 1
                    logic = _worker_load_cython_logic_from_state(state_path)
                else:
                    for _ in range(deterministic_turns_per_iteration):
                        if not _worker_advance_first_turn_cython(logic):
                            logic = _worker_load_cython_logic()
                            moves_played = 0
                            break
                        moves_played += 1
                        if logic.check_win_condition_py(RED) or logic.check_win_condition_py(BLACK) or moves_played >= max_moves_per_game:
                            logic = _worker_load_cython_logic()
                            moves_played = 0
                            break

                if hasattr(ai, "reset_search_counters"):
                    ai.reset_search_counters()
                if hasattr(ai, "get_best_move_benchmark"):
                    start = time.perf_counter()
                    best_piece, best_tile, tt_init_elapsed, minimax_elapsed = ai.get_best_move_benchmark(logic)
                    elapsed = time.perf_counter() - start
                else:
                    start = time.perf_counter()
                    best_piece, best_tile = ai.get_best_move(logic)
                    elapsed = time.perf_counter() - start
                    tt_init_elapsed = 0.0
                    minimax_elapsed = elapsed

                counters = ai.get_search_counters() if hasattr(ai, "get_search_counters") else {}
                evaluated_nodes_total += int(counters.get("evaluated_nodes", 0))
                leaf_nodes_total += int(counters.get("leaf_nodes", 0))
                elapsed_total += elapsed
                minimax_elapsed_total += float(minimax_elapsed)
                tt_init_elapsed_total += float(tt_init_elapsed)
                search_budget_consumed += elapsed
                iterations += 1

                if position_source != "fixture_replay":
                    if not _worker_apply_ai_move_cython(logic, best_piece, best_tile):
                        logic = _worker_load_cython_logic()
                        moves_played = 0
                    else:
                        moves_played += 1
                        if logic.check_win_condition_py(RED) or logic.check_win_condition_py(BLACK) or moves_played >= max_moves_per_game:
                            logic = _worker_load_cython_logic()
                            moves_played = 0

                if _worker_should_stop(
                    fixed_iterations=fixed_iterations,
                    iterations=iterations,
                    budget_mode=budget_mode,
                    budget_seconds=budget_seconds,
                    search_budget_consumed=search_budget_consumed,
                    wall_deadline=wall_deadline,
                ):
                    break

            sps = (iterations / elapsed_total) if elapsed_total > 0 else None
            seconds_per_iteration = (elapsed_total / iterations) if iterations > 0 else None
            elapsed_seconds_nonminimax = max(0.0, elapsed_total - minimax_elapsed_total)
            raw_evaluated_nodes = evaluated_nodes_total
            raw_leaf_nodes = leaf_nodes_total
            counters_nonzero = (raw_evaluated_nodes > 0) or (raw_leaf_nodes > 0)

            if counters_nonzero:
                evaluated_nodes_value = raw_evaluated_nodes
                leaf_nodes_value = raw_leaf_nodes
                nps = (evaluated_nodes_value / elapsed_total) if elapsed_total > 0 else None
                nps_minimax = (evaluated_nodes_value / minimax_elapsed_total) if minimax_elapsed_total > 0 else None
                supports_exact_evaluated_nodes = True
                nps_basis = "native_evaluated_nodes"
                nps_reason = "native_node_counters"
                node_counter_status = "native_counter_nonzero"
            else:
                # Some historical binaries expose counter APIs but never increment them.
                evaluated_nodes_value = None
                leaf_nodes_value = None
                nps = None
                nps_minimax = None
                supports_exact_evaluated_nodes = False
                nps_basis = "unavailable"
                nps_reason = "native_node_counters_zero"
                node_counter_status = "native_counter_zero_unusable"

            results.append(
                {
                    "depth": depth,
                    "sample_index": sample_index,
                    "status": "ok",
                    "iterations": iterations,
                    "elapsed_seconds": elapsed_total,
                    "evaluated_nodes": evaluated_nodes_value,
                    "leaf_nodes": leaf_nodes_value,
                    "total_nodes": None,
                    "nps": nps,
                    "nps_minimax": nps_minimax,
                    "sps": sps,
                    "seconds_per_iteration": seconds_per_iteration,
                    "elapsed_seconds_minimax": minimax_elapsed_total,
                    "elapsed_seconds_tt_init": tt_init_elapsed_total,
                    "elapsed_seconds_nonminimax": elapsed_seconds_nonminimax,
                    "coverage_ratio": None,
                    "pruning_ratio": None,
                    "supports_exact_evaluated_nodes": supports_exact_evaluated_nodes,
                    "supports_exact_total_nodes": False,
                    "metric_origin": "partial",
                    "nps_basis": nps_basis,
                    "nps_reason": nps_reason,
                    "node_counter_status": node_counter_status,
                    "evaluated_nodes_counter_raw": raw_evaluated_nodes,
                    "leaf_nodes_counter_raw": raw_leaf_nodes,
                    "error_stage": None,
                    "error_msg": None,
                }
            )

    return results


def worker_entry(worker_json: str) -> int:
    payload = json.loads(worker_json)
    worktree_path = Path(payload["worktree_path"])

    sys.path.insert(0, str(worktree_path))
    sys.path.insert(0, str(worktree_path / "NonagaGame"))
    sys.path.insert(0, str(worktree_path / "My Nonaga"))

    try:
        if payload["engine"] == "legacy_python":
            results = _worker_run_legacy(payload)
        elif payload["engine"] == "cython_core":
            results = _worker_run_cython(payload)
        else:
            raise RuntimeError(f"Unsupported worker engine: {payload['engine']}")

        print(json.dumps({"ok": True, "results": results}, ensure_ascii=True))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=True))
        return 0


def _worker_invoke(script_path: Path, payload: dict, timeout_seconds: float = 0.0) -> dict:
    cmd = [
        sys.executable,
        str(script_path),
        "--worker-json",
        json.dumps(payload, ensure_ascii=True),
    ]
    timeout = None if timeout_seconds <= 0 else timeout_seconds
    try:
        output = subprocess.check_output(cmd, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        timeout_desc = "disabled" if timeout is None else f"{timeout:.1f}s"
        return {
            "ok": False,
            "error": f"worker_timeout_after_{timeout_desc}",
        }

    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("Worker produced no output")
    return json.loads(lines[-1])


def scenario_matrix(commits: list[str], repo_root: Path) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for commit_hash in commits:
        engine = detect_engine(repo_root, commit_hash)
        if engine == "legacy_python":
            scenarios.extend(
                [
                    Scenario(commit_hash=commit_hash, engine=engine, ab_enabled=True, tt_enabled=False),
                    Scenario(commit_hash=commit_hash, engine=engine, ab_enabled=False, tt_enabled=False),
                ]
            )
        elif engine == "cython_core":
            scenarios.extend(
                [
                    Scenario(commit_hash=commit_hash, engine=engine, ab_enabled=True, tt_enabled=True),
                    Scenario(commit_hash=commit_hash, engine=engine, ab_enabled=False, tt_enabled=True),
                    Scenario(commit_hash=commit_hash, engine=engine, ab_enabled=True, tt_enabled=False),
                    Scenario(commit_hash=commit_hash, engine=engine, ab_enabled=False, tt_enabled=False),
                ]
            )
    return scenarios


def order_scenarios(scenarios: list[Scenario], mode: str, seed: int) -> list[Scenario]:
    mode_normalized = mode.strip().lower()
    if mode_normalized == "default":
        return list(scenarios)

    rng = random.Random(seed)

    if mode_normalized == "random":
        ordered = list(scenarios)
        rng.shuffle(ordered)
        return ordered

    if mode_normalized == "paired":
        grouped: dict[tuple[str, str], list[Scenario]] = {}
        key_order: list[tuple[str, str]] = []
        for scenario in scenarios:
            key = (scenario.commit_hash, scenario.engine)
            if key not in grouped:
                grouped[key] = []
                key_order.append(key)
            grouped[key].append(scenario)

        ordered: list[Scenario] = []
        for key in key_order:
            engine_group = grouped[key]
            if key[1] != "cython_core":
                ordered.extend(engine_group)
                continue

            by_ab: dict[bool, dict[bool, Scenario]] = {True: {}, False: {}}
            for scenario in engine_group:
                by_ab[scenario.ab_enabled][scenario.tt_enabled] = scenario

            for ab_flag in (True, False):
                tt_on = by_ab[ab_flag].get(True)
                tt_off = by_ab[ab_flag].get(False)

                if tt_on and tt_off:
                    if rng.random() < 0.5:
                        ordered.extend([tt_on, tt_off])
                    else:
                        ordered.extend([tt_off, tt_on])
                elif tt_on:
                    ordered.append(tt_on)
                elif tt_off:
                    ordered.append(tt_off)

        return ordered

    raise ValueError(f"Unsupported scenario order mode: {mode}")


def emit_rank_disagreement_summary(sample_rows: list[dict]) -> list[int]:
    depth_to_rows: dict[int, list[dict]] = {}
    for row in sample_rows:
        if row.get("status") != "ok":
            continue
        depth = int(row["depth"])
        depth_to_rows.setdefault(depth, []).append(row)

    if not depth_to_rows:
        print("Ranking summary: no successful sample rows available.")
        return []

    disagreement_depths: list[int] = []
    print("Ranking summary (primary=seconds_per_iteration, diagnostic=feature_search_nps):")

    for depth in sorted(depth_to_rows.keys()):
        per_scenario: dict[str, dict[str, list[float]]] = {}
        for row in depth_to_rows[depth]:
            scenario_id = str(row.get("scenario_id", "unknown"))
            bucket = per_scenario.setdefault(scenario_id, {"sec": [], "nps": []})
            sec_val = row.get("seconds_per_iteration")
            nps_val = row.get("feature_search_nps")
            if sec_val is not None:
                bucket["sec"].append(float(sec_val))
            if nps_val is not None:
                bucket["nps"].append(float(nps_val))

        sec_rank = [
            (statistics.mean(values["sec"]), scenario_id)
            for scenario_id, values in per_scenario.items()
            if values["sec"]
        ]
        nps_rank = [
            (statistics.mean(values["nps"]), scenario_id)
            for scenario_id, values in per_scenario.items()
            if values["nps"]
        ]

        if not sec_rank or not nps_rank:
            print(f"  depth={depth}: insufficient data for latency/feature_search_nps comparison")
            continue

        sec_rank.sort(key=lambda item: item[0])
        nps_rank.sort(key=lambda item: item[0], reverse=True)

        latency_best = sec_rank[0][1]
        nps_best = nps_rank[0][1]
        disagrees = latency_best != nps_best
        if disagrees:
            disagreement_depths.append(depth)

        print(
            f"  depth={depth}: latency_best={latency_best}, "
            f"feature_search_nps_best={nps_best}, disagreement={'yes' if disagrees else 'no'}"
        )

    return disagreement_depths


def run_main(args: argparse.Namespace) -> int:
    run_description = args.description.strip()
    if not run_description:
        run_description = input("Type run description: ").strip()
    if not run_description:
        raise ValueError("run_description is required.")

    # Script now lives under benchmark_feature/, so project root is one level up.
    repo_root = Path(__file__).resolve().parent.parent
    ledger_path = (repo_root / args.ledger).resolve()
    depths = parse_depths(args.depths)
    commits = parse_csv_str(args.commits)
    fixture_paths = [(repo_root / p).resolve() for p in parse_csv_str(args.fixtures)]

    position_source = args.position_source.strip().lower()
    if position_source == "fixture_replay":
        if not fixture_paths:
            raise RuntimeError("fixture_replay requires at least one fixture path")
        missing = [str(p) for p in fixture_paths if not p.exists()]
        if missing:
            raise RuntimeError(f"Missing fixture file(s): {missing}")

    fixture_id = "initial_position" if position_source == "initial_position_only" else "fixtures_replay"

    scenarios = order_scenarios(
        scenario_matrix(commits=commits, repo_root=repo_root),
        mode=args.scenario_order,
        seed=args.scenario_seed,
    )
    if not scenarios:
        raise RuntimeError("No benchmark scenarios were generated.")

    run_id = str(uuid.uuid4())
    run_start = {
        "run_id": run_id,
        "ts_utc": now_utc_iso(),
        "record_type": "run_start",
        "run_description": run_description,
        "commit_hash": "multi",
        "adapter_id": "feature_benchmark",
        "fixture_id": fixture_id,
        "depth": -1,
        "time_budget_ms": 0,
        "metric_origin": "partial",
        "machine_os": platform.platform(),
        "python_version": sys.version.split()[0],
        "benchmark_version": "feature_v1",
        "commit_set": commits,
        "default_depths": depths,
        "default_time_budget_ms": args.time_budget_ms,
        "budget_mode": args.budget_mode,
        "fixed_iterations": args.fixed_iterations,
        "scenario_order": args.scenario_order,
        "scenario_seed": args.scenario_seed,
        "samples": args.samples,
        "write_aggregates": args.write_aggregates,
        "position_source": position_source,
        "fixture_manifest": [str(p) for p in fixture_paths],
        "deterministic_turns_per_iteration": args.deterministic_turns_per_iteration,
        "max_moves_per_game": args.max_moves_per_game,
        "measurement_manifest": {
            "feature_search_nps": "nodes_per_second based on evaluated_nodes divided by minimax-only feature_search_elapsed_seconds when node counters are usable",
            "nps_minimax": "nodes_per_second based on evaluated_nodes/minimax_only_seconds when both are usable",
            "sps": "searches_per_second (feature_search_iterations/feature_search_elapsed_seconds)",
            "seconds_per_iteration": "feature_search_elapsed_seconds/feature_search_iterations",
            "feature_search_elapsed_seconds": "sum of minimax-only durations captured inside the feature harness (TT init excluded)",
            "feature_search_iterations": "number of search calls executed by the feature harness loop",
            "elapsed_seconds_minimax": "time spent in minimax iterative deepening only",
            "elapsed_seconds_tt_init": "time spent initializing transposition table structures",
            "elapsed_seconds_nonminimax": "feature_search_elapsed_seconds - elapsed_seconds_minimax",
            "evaluated_nodes_counter_raw": "raw evaluated node counter total before usability filtering",
            "leaf_nodes_counter_raw": "raw leaf node counter total before usability filtering",
            "nps_basis": "data source used for nps",
            "nps_reason": "explanation for nps availability/unavailability",
            "node_counter_status": "node counter quality status",
        },
    }
    validate_base_record(run_start)
    append_record(ledger_path, run_start)

    samples_written = 0
    aggregates_written = 0
    scenarios_succeeded = 0
    succeeded_commits: set[str] = set()
    successful_sample_rows: list[dict] = []

    for scenario in scenarios:
        worktree_dir = (repo_root / f".tmp_feature_{scenario.id}").resolve()
        scenario_rows: list[dict] = []

        try:
            ensure_worktree(repo_root, scenario.commit_hash, worktree_dir)
            prepare_variant_sources(scenario, worktree_dir)
            build_extensions(worktree_dir)

            worker_payload = {
                "engine": scenario.engine,
                "worktree_path": str(worktree_dir),
                "depths": depths,
                "samples": args.samples,
                "time_budget_ms": args.time_budget_ms,
                "deterministic_turns_per_iteration": args.deterministic_turns_per_iteration,
                "max_moves_per_game": args.max_moves_per_game,
                "fixed_iterations": args.fixed_iterations,
                "budget_mode": args.budget_mode,
                "position_source": position_source,
                "fixture_paths": [str(p) for p in fixture_paths],
            }
            worker_result = _worker_invoke(
                Path(__file__).resolve(),
                worker_payload,
                timeout_seconds=float(args.worker_timeout_seconds),
            )
            if not worker_result.get("ok"):
                raise RuntimeError(worker_result.get("error", "unknown worker error"))

            for sample_data in worker_result["results"]:
                row = {
                    "run_id": run_id,
                    "ts_utc": now_utc_iso(),
                    "record_type": "sample",
                    "run_description": run_description,
                    "commit_hash": scenario.commit_hash,
                    "adapter_id": scenario.adapter_id,
                    "fixture_id": fixture_id,
                    "depth": int(sample_data["depth"]),
                    "time_budget_ms": args.time_budget_ms,
                    "metric_origin": sample_data["metric_origin"],
                    "sample_index": int(sample_data["sample_index"]),
                    "feature_search_elapsed_seconds": sample_data["elapsed_seconds_minimax"],
                    "evaluated_nodes": sample_data["evaluated_nodes"],
                    "leaf_nodes": sample_data["leaf_nodes"],
                    "total_nodes": sample_data["total_nodes"],
                    "feature_search_nps": sample_data["nps_minimax"] if sample_data.get("nps_minimax") is not None else sample_data["nps"],
                    "nps_minimax": sample_data["nps_minimax"],
                    "sps": sample_data["sps"],
                    "seconds_per_iteration": sample_data["seconds_per_iteration"],
                    "elapsed_seconds_minimax": sample_data["elapsed_seconds_minimax"],
                    "elapsed_seconds_tt_init": sample_data["elapsed_seconds_tt_init"],
                    "elapsed_seconds_nonminimax": sample_data["elapsed_seconds_nonminimax"],
                    "nps_basis": sample_data["nps_basis"],
                    "nps_reason": sample_data["nps_reason"],
                    "node_counter_status": sample_data["node_counter_status"],
                    "evaluated_nodes_counter_raw": sample_data["evaluated_nodes_counter_raw"],
                    "leaf_nodes_counter_raw": sample_data["leaf_nodes_counter_raw"],
                    "coverage_ratio": sample_data["coverage_ratio"],
                    "pruning_ratio": sample_data["pruning_ratio"],
                    "status": sample_data["status"],
                    "error_stage": sample_data["error_stage"],
                    "error_msg": sample_data["error_msg"],
                    "supports_exact_evaluated_nodes": sample_data["supports_exact_evaluated_nodes"],
                    "supports_exact_total_nodes": sample_data["supports_exact_total_nodes"],
                    "feature_search_iterations": sample_data["iterations"],
                    "scenario_id": scenario.id,
                    "feature_ab_pruning_enabled": scenario.ab_enabled,
                    "feature_tt_hashing_enabled": None if scenario.engine == "legacy_python" else scenario.tt_enabled,
                    "engine": scenario.engine,
                    "commit_date_utc": get_commit_date_utc(repo_root, scenario.commit_hash),
                    "budget_mode": args.budget_mode,
                    "fixed_iterations": args.fixed_iterations,
                }
                validate_base_record(row)
                append_record(ledger_path, row)
                scenario_rows.append(row)
                successful_sample_rows.append(row)
                samples_written += 1

            if args.write_aggregates:
                for depth in depths:
                    depth_rows = [
                        r
                        for r in scenario_rows
                        if r["depth"] == depth and r["status"] == "ok"
                    ]
                    # Single-sample aggregates are redundant with the sample row.
                    if len(depth_rows) <= 1:
                        continue

                    nps_values = [r["feature_search_nps"] for r in depth_rows if r["feature_search_nps"] is not None]
                    sps_values = [r["sps"] for r in depth_rows if r.get("sps") is not None]
                    sec_iter_values = [
                        r["seconds_per_iteration"]
                        for r in depth_rows
                        if r.get("seconds_per_iteration") is not None
                    ]
                    nps_minimax_values = [r["nps_minimax"] for r in depth_rows if r.get("nps_minimax") is not None]
                    elapsed_values = [r["feature_search_elapsed_seconds"] for r in depth_rows]
                    elapsed_minimax_values = [
                        r["elapsed_seconds_minimax"]
                        for r in depth_rows
                        if r.get("elapsed_seconds_minimax") is not None
                    ]
                    elapsed_tt_init_values = [
                        r["elapsed_seconds_tt_init"]
                        for r in depth_rows
                        if r.get("elapsed_seconds_tt_init") is not None
                    ]
                    elapsed_nonminimax_values = [
                        r["elapsed_seconds_nonminimax"]
                        for r in depth_rows
                        if r.get("elapsed_seconds_nonminimax") is not None
                    ]
                    eval_values = [r["evaluated_nodes"] for r in depth_rows if r["evaluated_nodes"] is not None]
                    eval_raw_values = [
                        r["evaluated_nodes_counter_raw"]
                        for r in depth_rows
                        if r.get("evaluated_nodes_counter_raw") is not None
                    ]
                    leaf_raw_values = [
                        r["leaf_nodes_counter_raw"]
                        for r in depth_rows
                        if r.get("leaf_nodes_counter_raw") is not None
                    ]
                    usable_counter_rows = [
                        r
                        for r in depth_rows
                        if r.get("node_counter_status") == "native_counter_nonzero"
                    ]

                    agg = {
                        "run_id": run_id,
                        "ts_utc": now_utc_iso(),
                        "record_type": "aggregate",
                        "run_description": run_description,
                        "commit_hash": scenario.commit_hash,
                        "adapter_id": scenario.adapter_id,
                        "fixture_id": fixture_id,
                        "depth": depth,
                        "time_budget_ms": args.time_budget_ms,
                        "metric_origin": "partial" if scenario.engine == "cython_core" else "estimated",
                        "sample_count": len(depth_rows),
                        "feature_search_elapsed_seconds_mean": statistics.mean(elapsed_values),
                        "evaluated_nodes_mean": statistics.mean(eval_values) if eval_values else None,
                        "evaluated_nodes_counter_raw_mean": statistics.mean(eval_raw_values) if eval_raw_values else None,
                        "leaf_nodes_counter_raw_mean": statistics.mean(leaf_raw_values) if leaf_raw_values else None,
                        "total_nodes_mean": None,
                        "feature_search_nps_mean": statistics.mean(nps_values) if nps_values else None,
                        "feature_search_nps_median": statistics.median(nps_values) if nps_values else None,
                        "feature_search_nps_stdev": statistics.stdev(nps_values) if len(nps_values) > 1 else 0.0,
                        "nps_minimax_mean": statistics.mean(nps_minimax_values) if nps_minimax_values else None,
                        "sps_mean": statistics.mean(sps_values) if sps_values else None,
                        "seconds_per_iteration_mean": statistics.mean(sec_iter_values) if sec_iter_values else None,
                        "elapsed_seconds_minimax_mean": (
                            statistics.mean(elapsed_minimax_values) if elapsed_minimax_values else None
                        ),
                        "elapsed_seconds_tt_init_mean": (
                            statistics.mean(elapsed_tt_init_values) if elapsed_tt_init_values else None
                        ),
                        "elapsed_seconds_nonminimax_mean": (
                            statistics.mean(elapsed_nonminimax_values) if elapsed_nonminimax_values else None
                        ),
                        "coverage_ratio_mean": None,
                        "pruning_ratio_mean": None,
                        "node_counter_usable_sample_count": len(usable_counter_rows),
                        "scenario_id": scenario.id,
                        "feature_ab_pruning_enabled": scenario.ab_enabled,
                        "feature_tt_hashing_enabled": None if scenario.engine == "legacy_python" else scenario.tt_enabled,
                        "engine": scenario.engine,
                        "budget_mode": args.budget_mode,
                        "fixed_iterations": args.fixed_iterations,
                    }
                    validate_base_record(agg)
                    append_record(ledger_path, agg)
                    aggregates_written += 1

            scenarios_succeeded += 1
            succeeded_commits.add(scenario.commit_hash)

        except Exception:
            error_msg = str(sys.exc_info()[1]) if sys.exc_info()[1] is not None else "unknown_error"
            err_row = {
                "info": "failed",
                "run_id": run_id,
                "ts_utc": now_utc_iso(),
                "record_type": "scenario_error",
                "run_description": run_description,
                "commit_hash": scenario.commit_hash,
                "engine": scenario.engine,
                "scenario_id": scenario.id,
                "feature_ab_pruning_enabled": scenario.ab_enabled,
                "feature_tt_hashing_enabled": None if scenario.engine == "legacy_python" else scenario.tt_enabled,
                "error_stage": "scenario_execution",
                "error_msg": error_msg,
            }
            append_record(ledger_path, err_row)
            samples_written += 1
        finally:
            if args.cleanup_worktrees:
                cleanup_worktree(repo_root, worktree_dir)

    disagreement_depths = emit_rank_disagreement_summary(successful_sample_rows)

    run_end = {
        "run_id": run_id,
        "ts_utc": now_utc_iso(),
        "record_type": "run_end",
        "run_description": run_description,
        "commit_hash": "multi",
        "adapter_id": "feature_benchmark",
        "fixture_id": fixture_id,
        "depth": -1,
        "time_budget_ms": 0,
        "metric_origin": "partial",
        "commits_attempted": len(commits),
        "commits_succeeded": len(succeeded_commits),
        "commits_failed": max(0, len(commits) - len(succeeded_commits)),
        "scenarios_attempted": len(scenarios),
        "scenarios_succeeded": scenarios_succeeded,
        "scenarios_failed": len(scenarios) - scenarios_succeeded,
        "samples_written": samples_written,
        "aggregates_written": aggregates_written,
        "ranking_disagreement_depths": disagreement_depths,
        "ranking_disagreement_count": len(disagreement_depths),
    }
    validate_base_record(run_end)
    append_record(ledger_path, run_end)

    print(f"Feature ledger written to {ledger_path}")
    print(
        "run_id={run_id}, scenarios={scenario_count}, samples={samples}, aggregates={aggregates}".format(
            run_id=run_id,
            scenario_count=len(scenarios),
            samples=samples_written,
            aggregates=aggregates_written,
        )
    )

    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Feature benchmark runner for non-a11 commits. "
            "Defaults to b65b781 (AB only) and d096981 (AB + TT), "
            "with feature variants benchmarked via temporary worktree patching."
        )
    )
    parser.add_argument("--description", type=str, default="", help="User-authored run description.")
    parser.add_argument("--ledger", type=str, default="benchmark_feature/benchmark_feature_ledger.jsonl")
    parser.add_argument("--fixtures", type=str, default="saved_board.json,saved_board_backup.json")
    parser.add_argument("--depths", type=str, default="3,4")
    parser.add_argument("--time-budget-ms", type=int, default=8000)
    parser.add_argument(
        "--budget-mode",
        type=str,
        choices=["wall", "search"],
        default="wall",
        help=(
            "Budget stopping clock. 'wall' uses outer loop wall time; "
            "'search' uses cumulative measured AI call time only."
        ),
    )
    parser.add_argument(
        "--fixed-iterations",
        type=int,
        default=0,
        help="If >0, run exactly this many AI search iterations per sample and ignore time-budget stopping.",
    )
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument(
        "--worker-timeout-seconds",
        type=float,
        default=90.0,
        help="Hard timeout for each scenario worker subprocess; 0 disables timeout.",
    )
    parser.add_argument(
        "--write-aggregates",
        action="store_true",
        help="Write aggregate rows (only emitted when there are at least 2 successful samples per depth).",
    )
    parser.add_argument("--commits", type=str, default="b65b781,d096981")
    parser.add_argument(
        "--deterministic-turns-per-iteration",
        type=int,
        default=1,
        help="How many deterministic first-legal full turns to play before each AI search iteration.",
    )
    parser.add_argument(
        "--max-moves-per-game",
        type=int,
        default=5,
        help="Terminate and restart from initial position after this many full moves.",
    )
    parser.add_argument(
        "--cleanup-worktrees",
        action="store_true",
        help="Remove temporary scenario worktrees at the end.",
    )
    parser.add_argument(
        "--position-source",
        type=str,
        choices=["initial_position_only", "fixture_replay"],
        default="initial_position_only",
        help=(
            "Workload source for each AI call. initial_position_only preserves existing feature benchmark behavior; "
            "fixture_replay reloads board fixtures per iteration for version-benchmark comparability."
        ),
    )
    parser.add_argument(
        "--scenario-order",
        type=str,
        choices=["default", "paired", "random"],
        default="default",
        help=(
            "Scenario execution order: default matrix order, paired TT-on/off adjacency, "
            "or full random shuffle."
        ),
    )
    parser.add_argument(
        "--scenario-seed",
        type=int,
        default=1337,
        help="Seed used when --scenario-order is paired or random.",
    )
    parser.add_argument("--worker-json", type=str, default="", help=argparse.SUPPRESS)
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.worker_json:
        return worker_entry(args.worker_json)

    return run_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
