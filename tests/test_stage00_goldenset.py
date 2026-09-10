"""Stage 0 — 채점표. 코드보다 먼저 만든다.

⚠ 이 단계에는 사용자가 구현할 코드가 없다. **읽고 이해하는 것이 과업이다.**
  이 테스트는 「채점표가 채점표 구실을 하는가」를 확인한다 —
  나중에 골든셋을 늘릴 때 규격이 무너지지 않게 지키는 장치이기도 하다.

교본 RAG STEP 1 · 온톨로지 STEP 1 — **만들기 전에 채점표부터 만든다.**
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.stage0

VALID_TYPES = {"단일사실", "비교종합", "코드조회", "용어", "관계", "부재"}
VALID_SPLITS = {"dev", "holdout"}


def test_골든셋이_충분한_규모인가(golden_dev):
    """교본 권고는 30~100문항이다. 학습용이라 그보다 적지만 최소선은 지킨다."""
    from labkit.corpus import load_golden_set

    total = load_golden_set()
    assert len(total) >= 20, f"골든셋이 {len(total)}문항뿐입니다. 채점이 불안정해집니다"


def test_어려운_유형이_섞여_있는가():
    """⚠⚠ 쉬운 단일사실만 있는 골든셋은 아무것도 못 잰다 (교본 STEP 1).

    비교종합·관계처럼 **여러 청크를 합치거나 그래프를 걸어야** 하는 유형이 반드시 있어야 한다.
    """
    from labkit.corpus import load_golden_set

    types = {q["type"] for q in load_golden_set()}
    assert "비교종합" in types, "여러 청크를 합쳐야 하는 문항이 없습니다"
    assert "관계" in types, "그래프를 걸어야 하는 문항이 없습니다"


def test_자료부재_문항이_있는가():
    """⚠⚠ B형 실패(문서에 답이 없음)를 잴 수 없으면 A·B·C 분해가 성립하지 않는다.

    「확인되지 않습니다」가 정답인 문항이 있어야, 모르는 것을 모른다고 답하는지 잴 수 있다.
    """
    from labkit.corpus import load_golden_set

    absent = [q for q in load_golden_set() if q["type"] == "부재"]
    assert absent, "자료 부재(B형) 문항이 없습니다 — Stage 5 의 A·B·C 분해를 못 합니다"


def test_dev_holdout_이_나뉘어_있는가():
    """⚠⚠ CLAUDE.md §5-E' — 튜닝에 쓴 셋으로 평가하면 그 수치는 낙관 편향이다."""
    from labkit.corpus import load_golden_set

    dev = load_golden_set(split="dev")
    hold = load_golden_set(split="holdout")
    assert dev and hold, "dev/holdout 분할이 없습니다"
    assert len(hold) >= 5, f"holdout 이 {len(hold)}문항뿐이라 최종 확인이 불안정합니다"
    assert not ({q["id"] for q in dev} & {q["id"] for q in hold}), "dev 와 holdout 이 겹칩니다"


def test_모든_문항이_규격을_지키는가():
    """id · q · gold · type · split 이 전부 있어야 한다."""
    from labkit.corpus import load_golden_set

    for q in load_golden_set():
        qid = q.get("id", "(ID 없음)")
        for field in ("id", "q", "gold", "type", "split"):
            assert field in q, f"{qid}: '{field}' 누락"
        assert q["type"] in VALID_TYPES, f"{qid}: 알 수 없는 type '{q['type']}'"
        assert q["split"] in VALID_SPLITS, f"{qid}: 알 수 없는 split '{q['split']}'"


def test_근거가_실재하는_문서를_가리키는가(documents):
    """⚠ `must_cite` 가 없는 문서를 가리키면 그 문항은 **영원히 실패한다.**

    채점표 자체의 버그는 잡기 어렵다 — 검색기를 아무리 고쳐도 안 맞으니까.
    """
    from labkit.corpus import load_golden_set

    known = {d.doc_id for d in documents}
    for q in load_golden_set():
        for cite in q.get("must_cite") or []:
            doc_id = str(cite).split("#")[0]
            assert doc_id in known, f"{q['id']}: 없는 문서를 가리킵니다 — {doc_id}"


def test_역량질문이_홉수를_명시하는가():
    """온톨로지 채점표. ⚠ 몇 홉인지 적혀 있어야 「그래프가 필요한 질문」을 가릴 수 있다."""
    from labkit.corpus import load_competency_questions

    cqs = load_competency_questions()
    assert len(cqs) >= 10, f"역량질문이 {len(cqs)}건뿐입니다"
    assert any(c["hops"] >= 3 for c in cqs), "3홉 이상 질문이 없습니다 — Stage 7 을 못 잽니다"
    for c in cqs:
        assert "hops" in c and "path" in c, f"{c.get('id')}: hops/path 누락"


def test_개념사전에_문서에_없는_용어가_있는가(documents, concepts):
    """⚠⚠ 이 테스트가 Stage 6 의 존재 이유를 증명한다.

    「3망 해지」·「W코드」는 **어느 문서에도 정의가 없다.**
    그래서 문서 검색만으로는 그 질문에 답할 수 없고, 개념사전이 필요해진다.
    """
    all_text = "\n".join(d.text for d in documents)
    for term in ("3망 해지", "W코드"):
        assert term not in all_text, (
            f"'{term}' 이 문서에 있습니다. 코퍼스가 바뀌었다면 Stage 6 의 전제가 무너집니다"
        )

    internals: set[str] = set()
    for c in concepts["concepts"]:
        internals.update(c.get("internal") or [])
    assert "3망 해지" in internals, "개념사전에 '3망 해지' 가 없습니다"
    assert "W코드" in internals, "개념사전에 'W코드' 가 없습니다"
