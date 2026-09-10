"""측정 결과 저장·비교 — 학습 대상이 아닌 배관이다. (CLAUDE.md §5-D' · §7-5)

⚠⚠ 왜 파일로 남기는가
    대화는 요약되면 사라지지만 파일은 남는다.
    그리고 **이게 쌓인 것이 README 의 결과 표가 된다** (§13-2).
    측정하고 어디에도 안 적으면 그 단계는 측정하지 않은 것과 같다.

⚠ 이 모듈은 **저장과 형식**만 한다. 지표 계산은 Stage 5 에서 사용자가 `raglab` 에 짠다.
"""
from __future__ import annotations

import json
import pathlib
from datetime import date
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
METRICS = ROOT / "outputs" / "metrics"


def save_metrics(
    stage: int,
    *,
    method: str,
    metrics: dict[str, float],
    baseline: dict[str, float],
    n_questions: int,
    split: str,
    notes: str = "",
) -> pathlib.Path:
    """한 단계의 측정 결과를 남긴다.

    Args:
        stage: 단계 번호
        method: 무엇을 쟀는가 ("TF-IDF + 코사인", "BM25 + RRF 하이브리드")
        metrics: 이번 결과 {"recall@5": 0.72, ...}
        baseline: ⚠⚠ **필수.** 직전 단계 또는 무작위 기준선.
            §5-D' — 개선은 기준선과 나란히 보고한다
        n_questions: ⚠⚠ **분모.** 몇 문항으로 쟀는가 (§4)
        split: "dev" | "holdout" — 어느 쪽으로 쟀는가 (§5-E')

    Raises:
        ValueError: baseline 이 비었거나 n_questions 가 0 이하일 때.
            ⚠ 분모 없는 점추정치와 기준선 없는 개선 주장은 규격 미달이다.

    Returns:
        쓴 파일 경로
    """
    if not baseline:
        raise ValueError(
            "⛔ baseline 이 비어 있습니다 (CLAUDE.md §5-D').\n"
            "   개선을 주장하려면 직전 수치 또는 무작위 기준선을 같이 넣으십시오.\n"
            "   '좋아졌다'만 있고 이전 값이 없는 보고는 결함입니다."
        )
    if n_questions <= 0:
        raise ValueError(
            "⛔ n_questions 가 없습니다 (CLAUDE.md §4).\n"
            "   모든 비율에는 분모가 붙습니다. 'Recall 0.72' 가 아니라 "
            "'0.72 (16문항 중 11.5)' 입니다."
        )

    # ⚠ 이상하게 좋은 수치는 축하가 아니라 경보다 (§5-E')
    warnings: list[str] = []
    for k, v in metrics.items():
        if v >= 0.95:
            warnings.append(
                f"{k}={v:.3f} — 0.95 이상입니다. 골든셋 오염을 먼저 의심하십시오 (§5-E')"
            )
    # ⚠ 떨어진 지표를 감추지 않는다 (§5-D')
    regressed = {k: (baseline[k], metrics[k])
                 for k in metrics if k in baseline and metrics[k] < baseline[k] - 1e-9}

    payload: dict[str, Any] = {
        "stage": stage,
        "method": method,
        "split": split,
        "n_questions": n_questions,
        "metrics": metrics,
        "baseline": baseline,
        "delta": {k: round(metrics[k] - baseline[k], 6) for k in metrics if k in baseline},
        "regressed": regressed,
        "warnings": warnings,
        "synthetic": True,
        "measured_on": date.today().isoformat(),
        "notes": notes,
    }

    METRICS.mkdir(parents=True, exist_ok=True)
    path = METRICS / f"stage{stage:02d}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if warnings:
        print("⚠⚠ 경보:")
        for w in warnings:
            print(f"   {w}")
    if regressed:
        print(f"⚠ 떨어진 지표 {len(regressed)}건 — 보고에 함께 실으십시오: {list(regressed)}")
    return path


def load_metrics(stage: int) -> dict[str, Any] | None:
    """저장된 단계 결과를 읽는다. 없으면 None."""
    p = METRICS / f"stage{stage:02d}.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def history() -> list[dict[str, Any]]:
    """지금까지 측정된 모든 단계. README 결과 표의 재료다."""
    if not METRICS.exists():
        return []
    out = []
    for p in sorted(METRICS.glob("stage*.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def history_table() -> str:
    """진행 상황을 표로. ⚠ 측정 안 된 칸은 빈칸으로 둔다 — 추정치로 메우지 않는다 (§13-5)."""
    rows = history()
    if not rows:
        return "(측정 결과 없음 — outputs/metrics/ 가 비어 있습니다)"

    keys: list[str] = []
    for r in rows:
        for k in r["metrics"]:
            if k not in keys:
                keys.append(k)

    head = f"{'단계':<6}{'방법':<28}{'분모':<8}" + "".join(f"{k:>12}" for k in keys)
    lines = [head, "─" * len(head)]
    for r in rows:
        line = f"{r['stage']:<6}{r['method'][:26]:<28}{r['n_questions']:<8}"
        for k in keys:
            v = r["metrics"].get(k)
            line += f"{'—':>12}" if v is None else f"{v:>12.4f}"
        lines.append(line)
    lines.append("")
    lines.append("⚠ 합성 코퍼스 기준입니다. 실세계 성능이 아닙니다 (§3-S).")
    return "\n".join(lines)


if __name__ == "__main__":
    print(history_table())
