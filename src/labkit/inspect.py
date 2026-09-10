"""중간 결과를 **눈으로 보는** 도구. 학습 대상이 아닌 배관이다.

⚠⚠ 왜 이 모듈이 있는가 (CLAUDE.md §7-4)
    블랙박스 한 방 호출은 이 프로젝트에서 금지다.
    **눈으로 본 적 없는 값은 이해한 값이 아니다.**

    테스트가 초록색이 됐다는 것은 명세를 만족했다는 뜻이지, 왜 그런지 안다는 뜻이 아니다.
    청크가 어디서 잘렸는지, 어떤 단어가 왜 높은 가중치를 받았는지, 왜 저 문서가 1등인지를
    **직접 찍어 봐야** 다음 단계의 판단이 선다.

⚠ 여기 있는 함수는 전부 「보여주기」다. 계산은 `raglab` 에서 사용자가 한다.
"""
from __future__ import annotations

import shutil
from typing import Any, Sequence

# 터미널 폭. 표가 밀리지 않게 한 번만 잰다.
_WIDTH = min(shutil.get_terminal_size((100, 24)).columns, 120)


def _trim(s: str, n: int) -> str:
    """줄바꿈을 없애고 n 자로 자른다. 표가 깨지지 않게."""
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def rule(title: str = "") -> None:
    if title:
        pad = max(0, _WIDTH - len(title) - 4)
        print(f"── {title} " + "─" * pad)
    else:
        print("─" * _WIDTH)


def show_chunks(chunks: Sequence[Any], limit: int = 10, text_attr: str = "text") -> None:
    """청크 목록을 보여준다. **어디서 잘렸는지**가 핵심이다 (Stage 1).

    Args:
        chunks: 청크 객체 또는 문자열의 시퀀스
        limit: 몇 개까지 보여줄지
        text_attr: 객체일 때 본문이 담긴 속성 이름

    ⚠ 표가 잘렸는지 보려면 **끝부분**을 봐야 한다. 앞 40자만 보면 안 보인다.
      그래서 앞뒤를 같이 찍는다.
    """
    rule(f"청크 {len(chunks)}개 (앞 {min(limit, len(chunks))}개)")
    for i, c in enumerate(chunks[:limit]):
        text = getattr(c, text_attr, None) if not isinstance(c, str) else c
        text = str(text if text is not None else c)
        head, tail = _trim(text[:60], 60), _trim(text[-40:], 40)
        meta = ""
        for attr in ("doc_id", "path_label", "section"):
            v = getattr(c, attr, None)
            if v:
                meta = f"[{v}] "
                break
        print(f" {i:3d} ({len(text):4d}자) {meta}{head}")
        if len(text) > 100:
            print(f"      …끝▸ {tail}")
    if len(chunks) > limit:
        print(f" … 외 {len(chunks) - limit}개")
    print()


def show_lengths(chunks: Sequence[Any], text_attr: str = "text") -> None:
    """청크 길이 분포. **극단값이 문제를 만든다** (Stage 1)."""
    lens = sorted(
        len(str(getattr(c, text_attr, c) if not isinstance(c, str) else c)) for c in chunks
    )
    if not lens:
        print("(청크 없음)")
        return
    n = len(lens)
    rule("청크 길이 분포")
    print(f"  개수 {n} · 최소 {lens[0]} · 중앙 {lens[n // 2]} · 최대 {lens[-1]}")
    print(f"  평균 {sum(lens) / n:.0f}자")
    tiny = [x for x in lens if x < 50]
    if tiny:
        print(f"  ⚠ 50자 미만 {len(tiny)}개 — 조각만 봐서는 뜻을 알 수 없는 청크일 수 있습니다")
    print()


def show_vector(
    vec: Sequence[float], vocab: Sequence[str] | None = None, top: int = 10
) -> None:
    """벡터에서 값이 큰 차원을 보여준다 (Stage 2).

    ⚠ 「의미가 숫자가 됐다」는 말이 실감 나는 유일한 순간이다.
      어떤 단어가 왜 높은 가중치를 받았는지 확인하라.
    """
    pairs = list(enumerate(vec))
    pairs.sort(key=lambda kv: -abs(kv[1]))
    nz = sum(1 for v in vec if v != 0)
    rule(f"벡터 {len(vec)}차원 (0이 아닌 값 {nz}개) — 상위 {top}")
    for idx, val in pairs[:top]:
        name = vocab[idx] if vocab is not None and idx < len(vocab) else f"dim[{idx}]"
        bar = "█" * int(abs(val) / (abs(pairs[0][1]) or 1) * 30)
        print(f"  {name:>16} {val:+.4f} {bar}")
    print()


def show_ranking(
    results: Sequence[tuple[Any, float]],
    limit: int = 10,
    gold_ids: Sequence[str] | None = None,
    id_attr: str = "doc_id",
) -> None:
    """검색 결과와 **점수**를 보여준다 (Stage 3·4).

    Args:
        results: (문서/청크, 점수) 목록. 이미 정렬돼 있다고 가정하지 않고 여기서 정렬한다
        gold_ids: 정답 ID 목록. 주면 ✅ 표시가 붙는다

    ⚠⚠ 점수를 안 보고 순위만 보면 「1등과 2등의 차이가 0.001 인지 0.5 인지」를 모른다.
      그 차이가 재순위가 필요한지 아닌지를 가른다.
    """
    ranked = sorted(results, key=lambda kv: -kv[1])
    gold = set(gold_ids or [])
    rule(f"검색 결과 {len(ranked)}건 (상위 {min(limit, len(ranked))})")
    for i, (item, score) in enumerate(ranked[:limit], 1):
        ident = str(getattr(item, id_attr, item))
        mark = " ✅" if gold and any(g in ident for g in gold) else "   "
        title = getattr(item, "title", "")
        text = getattr(item, "text", "")
        preview = _trim(str(title or text), 50)
        print(f" {i:2d}.{mark} {score:8.4f}  {_trim(ident, 18):<18} {preview}")
    if gold:
        found = [
            i
            for i, (item, _) in enumerate(ranked[:limit], 1)
            if any(g in str(getattr(item, id_attr, item)) for g in gold)
        ]
        print(f"  → 정답 위치: {found or '상위 %d위 안에 없음 ⛔' % limit}")
    print()


def show_path(path: Sequence[tuple[str, str, str]]) -> None:
    """그래프에서 걸어간 경로를 보여준다 (Stage 7).

    ⚠ **문서 검색으로는 못 가는 경로**라는 것이 이 그림의 요점이다.
    """
    rule(f"그래프 경로 ({len(path)}홉)")
    for i, (s, p, o) in enumerate(path, 1):
        print(f"  {i}. ({s}) -[{p}]-> ({o})")
    print()


def compare_metrics(before: dict[str, float], after: dict[str, float], label: str = "") -> None:
    """기준선과 결과를 **나란히** 보여준다 (CLAUDE.md §5-D').

    ⚠⚠ 개선폭만 적힌 표는 규격 미달이다. 그리고 **바뀐 지표 전부**를 본다 —
      하나만 좋아진 것을 보고하는 것이 이 도메인의 교과서적 실수다.
    """
    rule(f"기준선 대조 {label}".strip())
    keys = sorted(set(before) | set(after))
    print(f"  {'지표':<16} {'기준선':>10} {'결과':>10} {'변화':>10}")
    for k in keys:
        b, a = before.get(k), after.get(k)
        if b is None or a is None:
            print(f"  {k:<16} {('—' if b is None else f'{b:.4f}'):>10}"
                  f" {('—' if a is None else f'{a:.4f}'):>10} {'—':>10}")
            continue
        d = a - b
        flag = "" if abs(d) < 1e-9 else ("▲" if d > 0 else "▼")
        print(f"  {k:<16} {b:>10.4f} {a:>10.4f} {d:>+9.4f}{flag}")
    worse = [k for k in keys if k in before and k in after and after[k] < before[k] - 1e-9]
    if worse:
        print(f"  ⚠ 떨어진 지표: {', '.join(worse)} — 이것도 함께 보고하십시오 (§5-D')")
    print()
