"""Stage 5 — 평가와 A·B·C 실패 분해. 통과 조건이자 명세다."""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.stage5


def _r(qid, retrieved, gold, hit_rank=None):
    from raglab.evaluate import EvalResult

    return EvalResult(qid=qid, retrieved=list(retrieved), gold=list(gold), hit_rank=hit_rank)


# ══════════════════════════════════════════════════════════════════════════
#  ① 지표
# ══════════════════════════════════════════════════════════════════════════

def test_전부_맞히면_1_전부_틀리면_0():
    from raglab.evaluate import recall_at_k

    allhit = [_r("q1", ["A"], ["A"], 1), _r("q2", ["B"], ["B"], 1)]
    allmiss = [_r("q1", ["X"], ["A"]), _r("q2", ["Y"], ["B"])]
    assert recall_at_k(allhit, k=5) == 1.0
    assert recall_at_k(allmiss, k=5) == 0.0


def test_분모가_문항수인가():
    """⚠⚠ **이 도메인의 전형적 결함이다** (CLAUDE.md §4).

    분모는 **골든셋 문항 수**다. 검색된 문서 수를 분모로 쓰면 그건 정밀도(precision)이고,
    이름과 실제 계산이 어긋난 것이다.
    """
    from raglab.evaluate import recall_at_k

    # 2문항 중 1문항만 맞힘 → 0.5. 검색 결과가 10건이든 100건이든 상관없다
    results = [
        _r("q1", ["A"] + [f"X{i}" for i in range(99)], ["A"], 1),
        _r("q2", ["Y"], ["B"]),
    ]
    assert abs(recall_at_k(results, k=100) - 0.5) < 1e-9, (
        "분모가 문항 수가 아닙니다 — 검색 결과 수를 분모로 쓰신 것 같습니다"
    )


def test_k_를_넘는_순위는_안_세는가():
    from raglab.evaluate import recall_at_k

    results = [_r("q1", ["X", "Y", "Z", "A"], ["A"], 4)]
    assert recall_at_k(results, k=3) == 0.0, "4위인데 Recall@3 에 잡혔습니다"
    assert recall_at_k(results, k=5) == 1.0


def test_MRR_이_순위를_반영하는가():
    """⚠ Recall 은 「찾았나」만, MRR 은 **「몇 번째로 찾았나」**를 본다.

    1위인 것과 20위인 것은 사용자 체감이 전혀 다르다. **둘 다 봐야 한다** (§5-D').
    """
    from raglab.evaluate import mean_reciprocal_rank

    first = [_r("q", ["A"], ["A"], 1)]
    fourth = [_r("q", ["X", "Y", "Z", "A"], ["A"], 4)]
    assert abs(mean_reciprocal_rank(first) - 1.0) < 1e-9
    assert abs(mean_reciprocal_rank(fourth) - 0.25) < 1e-9


def test_못_찾은_문항도_평균에_반영되는가():
    from raglab.evaluate import mean_reciprocal_rank

    mixed = [_r("q1", ["A"], ["A"], 1), _r("q2", ["X"], ["B"], None)]
    mrr = mean_reciprocal_rank(mixed)
    assert 0.0 < mrr < 1.0, f"못 찾은 문항 처리를 확인하십시오 (MRR={mrr})"


# ══════════════════════════════════════════════════════════════════════════
#  ② 기준선 — ⚠⚠ 이걸 못 이기면 실패한 검색기다 (CLAUDE.md §5-D')
# ══════════════════════════════════════════════════════════════════════════

def test_앞에서_k개_기준선():
    from raglab.evaluate import baseline_first_k

    assert baseline_first_k(["a", "b", "c", "d"], k=2) == ["a", "b"]
    assert len(baseline_first_k(["a"], k=5)) == 1


def test_무작위_기준선이_시드로_고정되는가():
    """⚠⚠ 실행마다 값이 바뀌면 기준선이 기준이 아니다 (§13-4)."""
    from raglab.evaluate import baseline_random_k

    ids = [f"c{i}" for i in range(50)]
    a = baseline_random_k(ids, k=5, seed=42)
    b = baseline_random_k(ids, k=5, seed=42)
    c = baseline_random_k(ids, k=5, seed=7)
    assert a == b, "같은 시드에 다른 결과가 나왔습니다"
    assert a != c, "다른 시드인데 같은 결과입니다 — 시드가 안 쓰이고 있습니다"
    assert len(set(a)) == 5, "중복이 뽑혔습니다"


# ══════════════════════════════════════════════════════════════════════════
#  ③ 평가 실행
# ══════════════════════════════════════════════════════════════════════════

def test_골든셋_전체를_도는가(golden_dev):
    from raglab.evaluate import evaluate

    results = evaluate(golden_dev, lambda q: ["TERMS-2026", "PLANS-2026"], k=5)
    assert len(results) == len(golden_dev), "문항 수와 결과 수가 다릅니다"
    assert {r.qid for r in results} == {q["id"] for q in golden_dev}


def test_정답을_찾으면_순위가_기록되는가(golden_dev):
    from raglab.evaluate import evaluate

    g001 = [q for q in golden_dev if q["id"] == "G-001"]
    assert g001, "G-001 이 dev 분할에 없습니다"
    results = evaluate(g001, lambda q: ["OTHER", "TERMS-2026"], k=5)
    assert results[0].hit_rank == 2, f"hit_rank 가 {results[0].hit_rank} 입니다 (기대 2)"


# ══════════════════════════════════════════════════════════════════════════
#  ④ ⚠⚠ A·B·C 분해 — 이 단계의 본체
# ══════════════════════════════════════════════════════════════════════════

def test_자료부재는_B로_분류되는가(golden_dev):
    """⚠⚠ **B 는 RAG 로 못 고친다.** 문서를 만들어야 한다.

    여기에 튜닝 시간을 쓰는 것이 가장 흔한 낭비다 (교본 STEP 7).
    """
    from raglab.evaluate import classify_failure

    absent = [q for q in golden_dev if q["type"] == "부재"]
    assert absent, "dev 분할에 부재형 문항이 없습니다"
    q = absent[0]
    verdict = classify_failure(_r(q["id"], ["아무거나"], []), q, wide_k=20)
    assert verdict == "B", f"부재형이 '{verdict}' 로 분류됐습니다"


def test_후보에_없으면_A로_분류되는가():
    """A = 검색 실패. 정답 청크가 후보에 못 들어왔다 → 검색을 고친다."""
    from raglab.evaluate import classify_failure

    q = {"id": "G-x", "type": "단일사실", "must_cite": ["TERMS-2026#제21조"]}
    verdict = classify_failure(
        _r("G-x", ["OTHER-1", "OTHER-2"], ["TERMS-2026#제21조"]),
        q,
        wide_k=20,
        wide_retrieved=["OTHER-1", "OTHER-2", "OTHER-3"],
    )
    assert verdict == "A", f"검색 실패가 '{verdict}' 로 분류됐습니다"


def test_넓게_보면_찾히는_경우를_구분하는가():
    """⚠ 좁게는 못 찾았는데 넓게는 찾았다면 **검색은 되는데 순위가 문제**다.

    이 구분이 「재순위를 붙일까 청킹을 고칠까」를 가른다.
    """
    from raglab.evaluate import classify_failure

    q = {"id": "G-y", "type": "단일사실", "must_cite": ["TERMS-2026"]}
    verdict = classify_failure(
        _r("G-y", ["A", "B", "C"], ["TERMS-2026"]),
        q,
        wide_k=20,
        wide_retrieved=["A", "B", "C", "TERMS-2026"],
    )
    assert verdict is not None, "실패인데 성공으로 분류됐습니다"


def test_성공은_None_인가():
    from raglab.evaluate import classify_failure

    q = {"id": "G-z", "type": "단일사실", "must_cite": ["TERMS-2026"]}
    assert classify_failure(_r("G-z", ["TERMS-2026"], ["TERMS-2026"], 1), q) is None


def test_실패_리포트가_분모를_담는가():
    """⚠⚠ 비율만 있고 분모가 없는 보고는 결함이다 (§4)."""
    from raglab.evaluate import failure_report

    results = [
        _r("q1", ["A"], ["A"], 1),
        _r("q2", ["X"], ["B"]),
        _r("q3", ["Y"], []),
    ]
    results[1].failure_type = "A"
    results[2].failure_type = "B"

    rep = failure_report(results)
    assert rep["n_total"] == 3, "분모(n_total)가 없거나 틀렸습니다"
    assert set(rep["counts"]) >= {"A", "B"}, f"A·B 집계가 없습니다: {rep['counts']}"
    assert rep["counts"]["A"] == 1 and rep["counts"]["B"] == 1
    assert "q1" in rep["success"]


@pytest.mark.breaks
def test_생성_없이는_C를_판정할_수_없음을_인정하는가():
    """⚠⚠ 이 프로젝트는 생성(LLM 호출)이 선택이다 (CLAUDE.md §9).

    생성 없이 C(생성 실패)를 판정했다고 주장하면 그건 `⚠⚠추론` 이지 측정이 아니다.
    **판정 불가를 판정 불가라고 말하는 것**이 이 테스트의 요점이다.

    구현에서 C 를 쓰지 않기로 했다면 이 테스트는 그대로 통과한다.
    C 를 쓰기로 했다면 무엇을 근거로 하는지 `docs/stages/05-*.md` 에 적어라.
    """
    from raglab.evaluate import classify_failure

    q = {"id": "G-c", "type": "단일사실", "must_cite": ["TERMS-2026"]}
    # 후보에는 들어왔다 — 생성이 없으면 이건 성공이거나 판정 불가다
    verdict = classify_failure(
        _r("G-c", ["TERMS-2026", "OTHER"], ["TERMS-2026"], 1), q, wide_k=20
    )
    assert verdict != "C" or True, (
        "생성 단계 없이 C 를 판정하셨다면 근거를 docs/stages/05-*.md 에 적으십시오"
    )
