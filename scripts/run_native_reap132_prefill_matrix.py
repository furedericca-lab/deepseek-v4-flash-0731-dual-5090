#!/usr/bin/env python3
"""Run the fail-fast GPU0-only native REAP132 prefill acceptance matrix."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_KERNEL = "7.0.0-28-generic"
FORBIDDEN_KERNEL_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"bad page state",
        r"BAD_PAGE",
        r"compound_head.*not consistent",
        r"corrupted mapping in tail page",
        r"kernel BUG at",
        r"general protection fault",
        r"\bsegfault at\b",
        r"NVRM: Xid",
        r"Xid \(PCI:",
        r"mce:.*hardware error",
        r"machine check events logged",
    )
)


@dataclass(frozen=True)
class Case:
    name: str
    tokens: int
    prompt: str


CASES = (
    Case("t1-1-token", 1, "Hello"),
    Case(
        "t2-16-token-chat",
        16,
        "User: Briefly explain why deterministic checkpoints matter. Assistant:",
    ),
    Case(
        "t3-32-token-code",
        32,
        "Write a Python function that validates a SHA256 digest, handles invalid input, "
        "and returns a clear boolean result. Include type annotations and one example.",
    ),
    Case(
        "t4-64-token-mixed",
        64,
        "请用中文和 English 分析 mixture-of-experts routing，并说明 why exact tensor "
        "provenance matters. Compare router rows, expert IDs, scales, packed weights, "
        "attention, tokenizer symbols, JSON fields, and deterministic file hashes. ",
    ),
    Case(
        "t5-128-token-bounded",
        128,
        (
            "A deterministic model checkpoint pipeline reads aligned safetensors payloads "
            "with direct I/O, remaps selected experts, preserves packed weights and scales, "
            "rewrites routing metadata, removes speculative prediction tensors, verifies "
            "every output tensor against its source provenance, and compares two complete "
            "build manifests. The runtime then streams one decoder layer at a time to a "
            "single visible GPU and checks finite hidden states and logits. Explain the "
            "invariants, possible failure modes, recovery gates, and why semantic generation "
            "quality belongs to the final deployment runtime rather than this bounded native "
            "prefill test. Include attention masks, position embeddings, token routing, "
            "device isolation, kernel logs, CUDA synchronization, memory limits, and artifact "
            "identity in the discussion. "
        ),
    ),
)
CASES_BY_NAME = {case.name: case for case in CASES}


def select_cases(names: list[str] | None) -> tuple[Case, ...]:
    if not names:
        return CASES
    return tuple(CASES_BY_NAME[name] for name in names)


def kernel_log() -> str:
    result = subprocess.run(
        ["journalctl", "-k", "-b", "--no-pager"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def forbidden_kernel_lines(log: str) -> list[str]:
    return [
        line
        for line in log.splitlines()
        if any(pattern.search(line) for pattern in FORBIDDEN_KERNEL_PATTERNS)
    ]


def enforce_boot_gate() -> dict[str, object]:
    kernel = subprocess.run(
        ["uname", "-r"], check=True, capture_output=True, text=True
    ).stdout.strip()
    tainted = int(Path("/proc/sys/kernel/tainted").read_text().strip())
    failures = forbidden_kernel_lines(kernel_log())
    if kernel != EXPECTED_KERNEL:
        raise RuntimeError(f"unexpected kernel: {kernel}, expected {EXPECTED_KERNEL}")
    if tainted != 4096:
        raise RuntimeError(f"unexpected kernel taint: {tainted}, expected 4096")
    if failures:
        raise RuntimeError("inadmissible current boot:\n" + "\n".join(failures[-20:]))
    return {"kernel": kernel, "tainted": tainted, "forbidden_events": 0}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    parser.add_argument(
        "--case",
        action="append",
        choices=tuple(CASES_BY_NAME),
        help="run only this case; repeat to set an explicit execution order",
    )
    parser.add_argument(
        "--cuda-launch-blocking",
        action="store_true",
        help="set CUDA_LAUNCH_BLOCKING=1 in each isolated case process",
    )
    parser.add_argument(
        "--trace-attention-layer",
        type=int,
        help="record read-only eager-attention operand diagnostics for this layer",
    )
    parser.add_argument(
        "--trace-values",
        action="store_true",
        help="include CUDA value reductions in attention traces; disabled by default",
    )
    parser.add_argument(
        "--qk-layout",
        choices=("original", "key-transposed-contiguous"),
        default="original",
        help="controlled QK key-layout diagnostic for the traced layer",
    )
    args = parser.parse_args()

    checkpoint = args.checkpoint.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    smoke = Path(__file__).with_name("native_reap132_smoke.py")
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "0"
    if args.cuda_launch_blocking:
        env["CUDA_LAUNCH_BLOCKING"] = "1"
    else:
        env.pop("CUDA_LAUNCH_BLOCKING", None)

    matrix = {
        "schema": "native-reap132-direct-prefill-matrix-v1",
        "checkpoint": str(checkpoint),
        "selected_cases": [case.name for case in select_cases(args.case)],
        "cuda_launch_blocking": args.cuda_launch_blocking,
        "trace_attention_layer": args.trace_attention_layer,
        "trace_values": args.trace_values,
        "qk_layout": args.qk_layout,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "cases": [],
        "status": "RUNNING",
    }
    matrix_path = output_dir / "matrix.json"

    def fail_case(case: Case, **details: object) -> None:
        matrix["cases"].append(
            {"name": case.name, "tokens": case.tokens, "status": "FAIL", **details}
        )
        matrix["completed_at"] = datetime.now(timezone.utc).isoformat()
        matrix["status"] = "FAIL"
        matrix_path.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")

    for case in select_cases(args.case):
        before = enforce_boot_gate()
        report = output_dir / f"{case.name}.json"
        log = output_dir / f"{case.name}.log"
        command = [
            str(args.python),
            "-X",
            "faulthandler",
            str(smoke),
            str(checkpoint),
            "--prompt",
            case.prompt,
            "--max-input-tokens",
            str(case.tokens),
            "--require-input-tokens",
            str(case.tokens),
            "--device",
            "cuda:0",
            "--report",
            str(report),
        ]
        if args.trace_attention_layer is not None:
            command.extend(
                [
                    "--trace-attention-layer",
                    str(args.trace_attention_layer),
                    "--attention-trace",
                    str(output_dir / f"{case.name}-attention-trace.jsonl"),
                ]
            )
        if args.trace_values:
            command.append("--trace-values")
        if args.qk_layout != "original":
            command.extend(["--qk-layout", args.qk_layout])
        print(f"running {case.name}: {case.tokens} tokens", flush=True)
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run(
                command,
                env=env,
                stdout=stream,
                stderr=subprocess.STDOUT,
                text=True,
            )
        try:
            after = enforce_boot_gate()
        except RuntimeError as exc:
            fail_case(
                case,
                report=report.name,
                log=log.name,
                exit_code=result.returncode,
                boot_gate_before=before,
                boot_gate_after={"status": "FAIL", "error": str(exc)},
                error="post-case boot gate failed",
            )
            raise
        if result.returncode != 0:
            fail_case(
                case,
                report=report.name,
                log=log.name,
                exit_code=result.returncode,
                boot_gate_before=before,
                boot_gate_after=after,
                error="case process exited nonzero",
            )
            raise RuntimeError(f"{case.name} exited {result.returncode}; see {log}")
        if not report.is_file():
            fail_case(
                case,
                report=report.name,
                log=log.name,
                exit_code=result.returncode,
                boot_gate_before=before,
                boot_gate_after=after,
                error="case report missing",
            )
            raise RuntimeError(f"{case.name} did not produce {report}")
        payload = json.loads(report.read_text(encoding="utf-8"))
        if payload.get("status") != "PASS" or payload.get("input_token_count") != case.tokens:
            fail_case(
                case,
                report=report.name,
                log=log.name,
                exit_code=result.returncode,
                boot_gate_before=before,
                boot_gate_after=after,
                error="case report invalid",
            )
            raise RuntimeError(f"{case.name} produced an invalid report")
        matrix["cases"].append(
            {
                "name": case.name,
                "tokens": case.tokens,
                "report": report.name,
                "log": log.name,
                "boot_gate_before": before,
                "boot_gate_after": after,
                "status": "PASS",
            }
        )
        matrix_path.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")

    matrix["completed_at"] = datetime.now(timezone.utc).isoformat()
    matrix["status"] = "PASS"
    matrix_path.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(matrix, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
