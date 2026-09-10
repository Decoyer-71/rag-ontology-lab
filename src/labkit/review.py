"""복습 카드 스케줄러 — 학습 대상이 아닌 배관이다. (CLAUDE.md §14)

⚠⚠ 왜 이 모듈이 있는가
────────────────────────────────────────────────────────────────────────────
단계를 통과했다는 것은 **그날 이해했다**는 뜻이지 **한 달 뒤에도 안다**는 뜻이 아니다.
포트폴리오 관점에서 그 차이는 결정적이다 — 면접은 마지막 커밋 3개월 뒤에 온다.

⚠⚠ 근거에 대해 정직할 것 (§4 · §13-5)
────────────────────────────────────────────────────────────────────────────
2026-09-10 조사 결과, 「망각 곡선 기반 최적 복습 주기」는 **만들 수 없다**:

  · 에빙하우스(1885)는 **피험자 1명(본인)·무의미 음절** 실험이다. Murre & Dros(2015)
    재현도 피험자 1명이다. 개념·코드 학습의 **일수 근거로 쓰면 과잉 일반화**다  ⛔
  · 확장 간격(1→3→7→14)이 우월하다는 통설은 Karpicke & Roediger(2007)이 지지하지
    않는다 — 확장 간격은 단기에만 유리했고 **장기에는 균등 간격이 더 나았다**  ⚠논쟁중
  · SM-2(Anki)는 Wozniak 이 시행착오로 만든 **휴리스틱**이다. 통제실험 검증이 아니다  ⛔
  · 근거가 강한 것은 둘뿐이다: **간격을 둬라**, **다시 읽지 말고 스스로 인출해라**
    (Dunlosky et al. 2013 에서 인출 연습·분산 연습 최고 등급 / 다시 읽기 최저 등급)  ✅
  ⚠2차 — 원문 PDF 접근이 막혀 2차 요약 경유다. 이 등급 그대로 쓴다.

그래서 이 모듈은 **일수를 근거로 포장하지 않는다.**
`GROW`·`FLOOR_DAYS` 는 **근거 없는 임의 파라미터**이고, 그렇게 파일에 적혀 있다.
대신 **모든 인출 결과를 로그로 남긴다** — 나중에 「간격에 따른 내 실제 회상률」을
자기 데이터로 그릴 수 있다. 그게 §13-2 의 차별점이 되는 지점이다.

사용 (스킬 `review` 와 `checkpoint` 가 부른다):

    .venv/Scripts/python.exe src/labkit/review.py status
    .venv/Scripts/python.exe src/labkit/review.py due
    .venv/Scripts/python.exe src/labkit/review.py add --stage 1 --kind code \\
        --target "src/raglab/chunking.py::chunk_by_chars" \\
        --test "tests/test_stage01_chunking.py" --question "왜 겹침이 필요한가"
    .venv/Scripts/python.exe src/labkit/review.py grade --id s01-chunk_by_chars --ok
    .venv/Scripts/python.exe src/labkit/review.py skip --days 1 --reason "출장"

⚠ `-m labkit.review` 가 아니라 **파일 경로로** 부른다. `src/` 를 import 경로에 넣는 것은
  `conftest.py` 뿐이라 pytest 밖에서는 안 걸리고, `PYTHONPATH=` 접두사를 붙이면
  `.claude/settings.json` 의 허용 규칙에 안 걸려 권한이 거부된다 (§6 지뢰 10).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import date, datetime, timedelta
from typing import Any, Literal

ROOT = pathlib.Path(__file__).resolve().parents[2]
STATE = ROOT / ".claude" / "state" / "review.json"
SESSION = ROOT / ".claude" / "state" / "review_session.json"
LOG = ROOT / "outputs" / "metrics" / "review_log.json"

Kind = Literal["code", "concept"]

# ── ⚠⚠ 근거 없는 임의 파라미터 ────────────────────────────────────────────
#   조사 결과 「정답인 일수」는 존재하지 않는다(모듈 독스트링).
#   여기 숫자는 **출발점일 뿐**이고, review_log.json 이 쌓이면 그 데이터로 조정한다.
#   ⛔ 이 값을 논문 근거처럼 문서에 적지 마라 (§13-5).
DEFAULT_PARAMS: dict[str, Any] = {
    "grow": 2.0,             # 인출 성공 시 간격에 곱하는 값
    "floor_days": 1,         # 인출 실패 시 되돌릴 간격
    "first_interval_days": 1,  # 카드가 처음 만들어질 때의 간격
    "max_interval_days": 60,   # 간격 상한 — 무한정 벌어지면 사실상 사라진다
    "max_cards_per_session": 5,  # ⚠ 사용자 시간이 가장 비싸다 (§9). 벽을 세우지 않는다
    "long_gap_days": 30,     # 이 이상 쉬면 카드가 아니라 「단계 재방문」을 처방한다
}

_PARAM_NOTE = (
    "⚠⚠ grow·floor_days 등은 근거 없는 임의 파라미터다. "
    "「망각 곡선이 정한 최적값」이 아니다 — 그런 것은 없다(labkit/review.py 독스트링). "
    "outputs/metrics/review_log.json 이 쌓이면 그 데이터로 조정한다."
)


# ══════════════════════════════════════════════════════════════════════════
#  상태 입출력
# ══════════════════════════════════════════════════════════════════════════

def _today() -> date:
    return date.today()


def _read_json(path: pathlib.Path, fallback: dict[str, Any]) -> dict[str, Any]:
    """읽고, 없거나 깨졌으면 fallback. ⚠ 인코딩을 명시한다 (§6 지뢰 5)."""
    if not path.exists():
        return dict(fallback)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(fallback)


def _write_json(path: pathlib.Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def empty_state() -> dict[str, Any]:
    """빈 상태. ⚠ 스키마를 바꾸면 `review_due.ps1`·`guard_review.ps1` 도 같이 고쳐야 한다."""
    return {
        "_comment": (
            "복습 카드 상태. 손으로 고치지 말고 `python -m labkit.review` 로 갱신한다. "
            "훅 review_due.ps1 · guard_review.ps1 이 이 파일을 읽는다."
        ),
        "schema_version": 1,
        "params": dict(DEFAULT_PARAMS),
        "_params_note": _PARAM_NOTE,
        "cards": [],
        "skip_until": None,
        "skip_log": [],
        "last_learning_commit": None,
        "last_learning_at": None,
    }


def load_state() -> dict[str, Any]:
    state = _read_json(STATE, empty_state())
    # 파라미터가 빠진 옛 파일도 받아들인다 — 훅이 죽는 것이 더 나쁘다
    params = dict(DEFAULT_PARAMS)
    params.update(state.get("params") or {})
    state["params"] = params
    state.setdefault("cards", [])
    state.setdefault("skip_log", [])
    return state


def save_state(state: dict[str, Any]) -> None:
    _write_json(STATE, state)


# ══════════════════════════════════════════════════════════════════════════
#  카드
# ══════════════════════════════════════════════════════════════════════════

def make_card_id(stage: int, target: str) -> str:
    """`s01-chunk_by_chars` 처럼 사람이 읽을 수 있는 id.

    ⚠ 같은 대상에 카드가 두 장 생기면 복습이 중복된다. id 로 막는다.
    """
    leaf = target.split("::")[-1].split("/")[-1]
    leaf = "".join(ch if (ch.isalnum() or ch in "._-") else "_" for ch in leaf)
    return f"s{stage:02d}-{leaf}"


def add_card(
    state: dict[str, Any],
    *,
    stage: int,
    kind: Kind,
    target: str,
    question: str,
    test: str = "",
) -> tuple[dict[str, Any], bool]:
    """카드를 등록한다. 이미 있으면 그대로 둔다.

    Args:
        stage: 이 카드가 속한 단계
        kind: "code" = 함수를 빈칸으로 되돌리고 다시 짜기 (인출)
              "concept" = checkpoint 가 물었던 「왜」 질문 다시 답하기 (인출)
        target: code 면 `src/raglab/파일.py::함수`, concept 면 개념 이름
        question: 사용자에게 실제로 던질 문장
        test: code 카드의 채점표. ⚠ 채점을 사람 감으로 하지 않기 위해 필요하다

    Returns:
        (카드, 새로 만들었는가)
    """
    cid = make_card_id(stage, target)
    for card in state["cards"]:
        if card["id"] == cid:
            return card, False

    first = int(state["params"]["first_interval_days"])
    card = {
        "id": cid,
        "kind": kind,
        "stage": stage,
        "target": target,
        "test": test,
        "question": question,
        "interval_days": first,
        "due": (_today() + timedelta(days=first)).isoformat(),
        "created": _today().isoformat(),
        "history": [],
    }
    state["cards"].append(card)
    return card, True


def due_cards(state: dict[str, Any], *, on: date | None = None) -> list[dict[str, Any]]:
    """만기 카드를 오래 밀린 순으로. ⚠ 상한은 여기서 자르지 않는다 — 세는 쪽과 내는 쪽을 나눈다."""
    on = on or _today()
    out = [c for c in state["cards"] if date.fromisoformat(c["due"]) <= on]
    out.sort(key=lambda c: (c["due"], c["stage"]))
    return out


def grade(state: dict[str, Any], card_id: str, ok: bool) -> dict[str, Any]:
    """인출 결과를 반영해 다음 만기를 정한다.

    성공 → 간격 × grow / 실패 → floor_days 로 되돌림.

    ⚠⚠ 이 규칙 자체에 논문 근거는 없다(모듈 독스트링). **적응형이라는 형태**만
       근거가 지지한다 — 구체적 배수는 임의값이고 로그로 조정할 대상이다.

    Raises:
        KeyError: 없는 카드 id
    """
    params = state["params"]
    for card in state["cards"]:
        if card["id"] != card_id:
            continue

        before = int(card["interval_days"])
        if ok:
            nxt = min(int(round(before * float(params["grow"]))), int(params["max_interval_days"]))
            nxt = max(nxt, before + 1)  # grow 가 1.0 이어도 앞으로는 간다
        else:
            nxt = int(params["floor_days"])

        card["history"].append(
            {"date": _today().isoformat(), "ok": bool(ok), "interval_before": before}
        )
        card["interval_days"] = nxt
        card["due"] = (_today() + timedelta(days=nxt)).isoformat()
        _append_log(card, ok=ok, interval_before=before, interval_after=nxt)
        return card

    raise KeyError(f"그런 카드가 없습니다: {card_id}")


def _append_log(
    card: dict[str, Any], *, ok: bool, interval_before: int, interval_after: int
) -> None:
    """⚠⚠ 모든 인출 결과를 남긴다. 이게 쌓여야 파라미터를 감이 아니라 데이터로 고친다."""
    log = _read_json(LOG, {"_comment": "복습 인출 기록 (labkit.review). 분석용.", "entries": []})
    log.setdefault("entries", []).append(
        {
            "at": datetime.now().isoformat(timespec="seconds"),
            "card": card["id"],
            "kind": card["kind"],
            "stage": card["stage"],
            "ok": bool(ok),
            "interval_before_days": interval_before,
            "interval_after_days": interval_after,
            "n_reviews": len(card["history"]),
        }
    )
    _write_json(LOG, log)


# ══════════════════════════════════════════════════════════════════════════
#  공백기간
# ══════════════════════════════════════════════════════════════════════════

def gap_days(state: dict[str, Any], *, on: date | None = None) -> int | None:
    """마지막 학습 이후 며칠 쉬었는가. 학습 기록이 없으면 None."""
    raw = state.get("last_learning_at")
    if not raw:
        return None
    try:
        last = datetime.fromisoformat(raw).date()
    except ValueError:
        return None
    return max(0, ((on or _today()) - last).days)


def plan(state: dict[str, Any], *, on: date | None = None) -> dict[str, Any]:
    """이번 세션 복습 계획.

    ⚠ 공백이 길다고 카드를 무한정 쌓지 않는다 — 그러면 재시작 자체를 막는다.
      상한을 넘기면 나머지는 이월하고, 아주 긴 공백은 **카드가 아니라 단계 재방문**을 처방한다.
    """
    params = state["params"]
    due = due_cards(state, on=on)
    cap = int(params["max_cards_per_session"])
    gap = gap_days(state, on=on)

    skip_until = state.get("skip_until")
    skipping = False
    if skip_until:
        try:
            skipping = (on or _today()) <= date.fromisoformat(skip_until)
        except ValueError:
            skipping = False

    revisit: int | None = None
    if gap is not None and gap >= int(params["long_gap_days"]) and due:
        revisit = min(c["stage"] for c in due)

    return {
        "computed_at": datetime.now().isoformat(timespec="seconds"),
        "gap_days": gap,
        "due_total": len(due),
        "cards": [c["id"] for c in due[:cap]],
        "deferred": max(0, len(due) - cap),
        "revisit_stage": revisit,
        "skipping": skipping,
        "skip_until": skip_until,
        # ⚠⚠ guard_review.ps1 이 읽는 값이다. 이름을 바꾸면 훅도 같이 고쳐라.
        "gate": "open" if (skipping or not due) else "blocked",
    }


def write_session(state: dict[str, Any]) -> dict[str, Any]:
    """세션 계획을 파일로 내려 훅이 읽게 한다."""
    p = plan(state)
    p["reviewed"] = []
    _write_json(SESSION, p)
    return p


def mark_reviewed(card_id: str) -> None:
    """이번 세션에 이 카드를 실제로 돌았다고 기록 → 게이트가 열린다."""
    sess = _read_json(SESSION, {})
    if not sess:
        return
    done = set(sess.get("reviewed") or [])
    done.add(card_id)
    sess["reviewed"] = sorted(done)
    remaining = [c for c in (sess.get("cards") or []) if c not in done]
    sess["gate"] = "open" if not remaining else "blocked"
    _write_json(SESSION, sess)


# ══════════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════════

def _fmt_card(c: dict[str, Any]) -> str:
    kind = "코드 인출" if c["kind"] == "code" else "개념 인출"
    n = len(c["history"])
    ok = sum(1 for h in c["history"] if h["ok"])
    return (
        f"  [{c['id']}] Stage {c['stage']} · {kind} · 만기 {c['due']} "
        f"(간격 {c['interval_days']}일 · 이력 {ok}/{n})\n"
        f"      대상: {c['target']}\n"
        f"      질문: {c['question']}"
    )


def main(argv: list[str] | None = None) -> int:
    # ⚠ 윈도우 콘솔은 cp949 라 한글 print 가 죽는다 (§6 지뢰 9)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

    ap = argparse.ArgumentParser(prog="labkit.review", description="복습 카드 스케줄러")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="전체 상태")
    sub.add_parser("due", help="오늘 만기 카드")
    sub.add_parser("session", help="이번 세션 계획을 다시 계산해 파일로 내린다")

    a = sub.add_parser("add", help="카드 등록 (checkpoint 스킬이 부른다)")
    a.add_argument("--stage", type=int, required=True)
    a.add_argument("--kind", choices=["code", "concept"], required=True)
    a.add_argument("--target", required=True)
    a.add_argument("--question", required=True)
    a.add_argument("--test", default="")

    g = sub.add_parser("grade", help="인출 결과 반영 (review 스킬이 부른다)")
    g.add_argument("--id", required=True)
    m = g.add_mutually_exclusive_group(required=True)
    m.add_argument("--ok", action="store_true")
    m.add_argument("--fail", action="store_true")

    s = sub.add_parser("skip", help="⚠ 건너뛰기. 기록이 남는다")
    s.add_argument("--days", type=int, default=1)
    s.add_argument("--reason", required=True)

    t = sub.add_parser("touch", help="학습 시각 갱신 (commit_watch 훅이 부른다)")
    t.add_argument("--commit", required=True)
    t.add_argument("--at", required=True, help="ISO 시각")

    ns = ap.parse_args(argv)
    state = load_state()

    if ns.cmd == "status":
        p = plan(state)
        gap = "기록 없음" if p["gap_days"] is None else f"{p['gap_days']}일"
        print(f"카드 {len(state['cards'])}장 · 만기 {p['due_total']}장 · 공백 {gap} · 게이트 {p['gate']}")
        for c in state["cards"]:
            print(_fmt_card(c))
        return 0

    if ns.cmd == "due":
        p = plan(state)
        cards = {c["id"]: c for c in state["cards"]}
        if not p["cards"]:
            print("만기 카드 없음")
            return 0
        print(f"만기 {p['due_total']}장 중 이번 세션 {len(p['cards'])}장 (이월 {p['deferred']}장)")
        if p["revisit_stage"] is not None:
            print(
                f"⚠ 공백 {p['gap_days']}일 — 카드보다 **Stage {p['revisit_stage']} 재방문**이 맞습니다"
            )
        for cid in p["cards"]:
            print(_fmt_card(cards[cid]))
        return 0

    if ns.cmd == "session":
        p = write_session(state)
        print(f"게이트 {p['gate']} · 이번 세션 {len(p['cards'])}장 · 이월 {p['deferred']}장")
        return 0

    if ns.cmd == "add":
        card, created = add_card(
            state,
            stage=ns.stage,
            kind=ns.kind,
            target=ns.target,
            question=ns.question,
            test=ns.test,
        )
        save_state(state)
        print(("✅ 등록: " if created else "= 이미 있음: ") + card["id"] + f" (만기 {card['due']})")
        return 0

    if ns.cmd == "grade":
        card = grade(state, ns.id, ok=bool(ns.ok))
        save_state(state)
        mark_reviewed(ns.id)
        verdict = "성공" if ns.ok else "실패"
        print(f"{card['id']} · {verdict} → 다음 간격 {card['interval_days']}일 (만기 {card['due']})")
        return 0

    if ns.cmd == "skip":
        until = _today() + timedelta(days=max(1, ns.days))
        state["skip_until"] = until.isoformat()
        state["skip_log"].append(
            {"at": _today().isoformat(), "days": ns.days, "reason": ns.reason}
        )
        save_state(state)
        write_session(state)
        print(f"⚠ {until.isoformat()} 까지 건너뜁니다. 사유: {ns.reason}")
        print(f"  건너뛴 횟수 누적 {len(state['skip_log'])}회 — 이것도 데이터입니다")
        return 0

    if ns.cmd == "touch":
        state["last_learning_commit"] = ns.commit
        state["last_learning_at"] = ns.at
        save_state(state)
        print(f"학습 시각 갱신: {ns.at} ({ns.commit[:8]})")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
