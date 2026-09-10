"""Stage 4 — BM25 · RRF · 메타데이터 필터. 통과 조건이자 명세다."""
from __future__ import annotations

import numpy as np
import pytest

pytestmark = pytest.mark.stage4

TOY_TOKENS = [
    ["해지", "해지", "요금", "요금", "요금"],   # 길다
    ["요금", "데이터"],
    ["요금", "청약철회"],
]


# ══════════════════════════════════════════════════════════════════════════
#  ① BM25
# ══════════════════════════════════════════════════════════════════════════

def test_점수_형태와_유한성():
    from raglab.retrieval import BM25

    s = BM25().fit(TOY_TOKENS).score(["요금"])
    assert s.shape == (3,)
    assert np.all(np.isfinite(s)), f"nan/inf 가 있습니다: {s}"


def test_드문_단어가_더_높은_점수를_주는가():
    """IDF 항이 하는 일. '청약철회'는 1문서에만 있다."""
    from raglab.retrieval import BM25

    bm = BM25().fit(TOY_TOKENS)
    rare = bm.score(["청약철회"])
    common = bm.score(["요금"])
    assert float(rare.max()) > float(common.max()), (
        "드문 단어가 흔한 단어보다 높은 점수를 못 냅니다 — IDF 항을 확인하십시오"
    )


def test_미등록_단어는_0점인가():
    from raglab.retrieval import BM25

    s = BM25().fit(TOY_TOKENS).score(["존재하지않는단어xyz"])
    assert float(np.abs(s).sum()) == 0.0


@pytest.mark.breaks
def test_TF_가_포화되는가():
    """⚠⚠ **BM25 가 단순 TF 와 다른 지점이다.**

    같은 단어가 100번 나와도 10번 나온 것의 10배 점수가 되면 안 된다.
    키워드 스터핑(같은 단어 반복)에 검색이 무너지기 때문이다.
    `k1` 이 그 포화 정도를 정한다.
    """
    from raglab.retrieval import BM25

    docs = [["요금"] * 1, ["요금"] * 10, ["요금"] * 100]
    s = BM25().fit(docs).score(["요금"])
    ratio_1_10 = s[1] / s[0] if s[0] else float("inf")
    ratio_10_100 = s[2] / s[1] if s[1] else float("inf")
    assert ratio_10_100 < ratio_1_10, (
        "빈도가 늘어도 점수 증가가 둔화되지 않습니다 — TF 포화 항(k1)이 빠졌습니다"
    )


@pytest.mark.breaks
def test_길이_정규화가_동작하는가():
    """⚠ 긴 문서가 **단지 길다는 이유로** 이기면 안 된다.

    두 문서가 '요금'을 같은 횟수 담고 있는데 하나가 훨씬 길다면,
    짧은 쪽이 더 「요금에 관한 문서」다.
    """
    from raglab.retrieval import BM25

    docs = [["요금"] + ["기타"] * 2, ["요금"] + ["기타"] * 200]
    s = BM25(b=0.75).fit(docs).score(["요금"])
    assert s[0] > s[1], "긴 문서가 이겼습니다 — 길이 정규화 항(b)을 확인하십시오"


@pytest.mark.breaks
def test_모든_문서에_있는_단어에서_음수가_안_나오는가():
    """⚠⚠ **이 코퍼스에서 실제로 나타나는 문제다.**

    BM25 원식의 IDF `log((N-df+0.5)/(df+0.5))` 는 df 가 N 에 가까우면 **음수**가 된다.
    음수 IDF 는 "그 단어가 일치하면 점수를 깎는다"는 뜻이라 직관에 어긋난다.

    ⚠ 문서가 15건뿐인 이 코퍼스에서는 '요금' 같은 단어가 바로 이 경우다.
      스무딩을 넣을지 결정하고, **그 결정을 주석과 PROGRESS.md 에 적어라.**
    """
    from raglab.retrieval import BM25

    docs = [["요금", "가"], ["요금", "나"], ["요금", "다"]]  # '요금'이 전 문서에
    s = BM25().fit(docs).score(["요금"])
    assert np.all(s >= 0), (
        f"모든 문서에 있는 단어에서 음수 점수가 나왔습니다: {s}\n"
        "IDF 스무딩을 넣을지 결정하고 주석에 이유를 적으십시오"
    )


def test_search_가_상위_k를_돌려주는가():
    from raglab.retrieval import BM25

    out = BM25().fit(TOY_TOKENS).search(["요금"], k=2)
    assert len(out) == 2
    assert out[0][1] >= out[1][1]


# ══════════════════════════════════════════════════════════════════════════
#  ② RRF
# ══════════════════════════════════════════════════════════════════════════

def test_두_랭킹을_합치는가():
    from raglab.retrieval import reciprocal_rank_fusion

    out = reciprocal_rank_fusion([[0, 1, 2], [2, 1, 0]], top=3)
    assert len(out) == 3
    # 1 번은 양쪽에서 2위 → 가장 안정적으로 높다
    assert out[0][0] == 1, f"양쪽에서 중간인 항목이 1위여야 합니다: {out}"


def test_양쪽_1위가_강하게_반영되는가():
    from raglab.retrieval import reciprocal_rank_fusion

    out = reciprocal_rank_fusion([[5, 0, 1], [5, 2, 3]], top=2)
    assert out[0][0] == 5, "양쪽 1위가 최종 1위가 아닙니다"


def test_한쪽에만_있는_항목도_포함되는가():
    """⚠ 합집합이어야 한다. 교집합만 남기면 하이브리드의 의미가 없다."""
    from raglab.retrieval import reciprocal_rank_fusion

    ids = {i for i, _ in reciprocal_rank_fusion([[0, 1], [2, 3]], top=4)}
    assert ids == {0, 1, 2, 3}, f"합집합이 아닙니다: {ids}"


@pytest.mark.breaks
def test_RRF_는_점수_차이를_버리는가():
    """⚠⚠ **RRF 의 한계다. 알고 써야 한다.**

    한 검색기가 압도적으로 확신해도(1위 0.99, 2위 0.01)
    RRF 는 **순위만** 보므로 그 확신이 반영되지 않는다.
    두 랭킹의 순서가 같으면 원래 점수가 무엇이었든 결과가 같다.

    → 이 한계를 `docs/stages/04-*.md` 「깨지는 조건」에 적어라.
    """
    from raglab.retrieval import reciprocal_rank_fusion

    a = reciprocal_rank_fusion([[0, 1, 2], [0, 1, 2]], top=3)
    b = reciprocal_rank_fusion([[0, 1, 2], [0, 1, 2]], top=3)
    assert a == b
    # 순위가 같으면 원 점수와 무관하게 결과가 동일하다는 사실을 고정한다
    assert [i for i, _ in a] == [0, 1, 2]


# ══════════════════════════════════════════════════════════════════════════
#  ③ 메타데이터 필터 — ⚠⚠ 구버전 문서를 걷어낸다
# ══════════════════════════════════════════════════════════════════════════

def test_구버전_문서를_걸러내는가(documents):
    """⚠⚠ 교본 §1-6 함정 03 — **구버전 문서가 최신 답변을 이겨버린다.**

    `plans_2025.md` 는 5G스탠다드 데이터를 100GB 라고 한다. 2026 판은 110GB 다.
    필터가 없으면 틀린 답이 나온다.
    """
    from raglab.chunking import chunk_documents
    from raglab.retrieval import filter_candidates

    chunks = chunk_documents(documents)
    all_idx = list(range(len(chunks)))
    kept = filter_candidates(chunks, all_idx, exclude_superseded=True)
    kept_docs = {chunks[i].doc_id for i in kept}
    assert "PLANS-2025" not in kept_docs, "구버전 요금안내가 안 걸러졌습니다"
    assert "PLANS-2026" in kept_docs, "신버전까지 걸러졌습니다"


def test_권한_등급으로_거르는가(documents):
    """⚠⚠ **필터는 검색 단계에서 건다. 생성 후에 거르면 이미 늦다** (교본 STEP 5).

    권한 없는 문서가 LLM 컨텍스트에 들어간 시점에 이미 유출이다.
    """
    from raglab.chunking import chunk_documents
    from raglab.retrieval import filter_candidates

    chunks = chunk_documents(documents)
    kept = filter_candidates(chunks, list(range(len(chunks))), acl="PUBLIC")
    kept_docs = {chunks[i].doc_id for i in kept}
    assert "MAN-TERM" not in kept_docs, "CS_AGENT 전용 상담매뉴얼이 PUBLIC 에 노출됩니다"
    assert "PEN-RULE" not in kept_docs, "CS_AGENT 전용 내부규정이 PUBLIC 에 노출됩니다"
    assert "TERMS-2026" in kept_docs, "공개 약관까지 걸러졌습니다"


def test_유효일자로_거르는가(documents):
    from raglab.chunking import chunk_documents
    from raglab.retrieval import filter_candidates

    chunks = chunk_documents(documents)
    kept = filter_candidates(
        chunks, list(range(len(chunks))), exclude_superseded=False, as_of="2025-06-01"
    )
    kept_docs = {chunks[i].doc_id for i in kept}
    assert "PLANS-2025" in kept_docs, "2025년 시점인데 2025 요금안내가 빠졌습니다"
    assert "PLANS-2026" not in kept_docs, "2025년 시점에 2026 요금안내가 유효하면 안 됩니다"


@pytest.mark.breaks
def test_필터_후_후보가_0개가_될_수_있는가(documents):
    """⚠ 조건을 세게 걸면 후보가 사라진다. 그때 조용히 터지지 말고 빈 목록을 돌려줘야 한다.

    호출부가 "검색 결과 없음"을 사용자에게 알릴 수 있어야 한다.
    """
    from raglab.chunking import chunk_documents
    from raglab.retrieval import filter_candidates

    chunks = chunk_documents(documents)
    kept = filter_candidates(chunks, list(range(len(chunks))), as_of="1999-01-01")
    assert kept == [], f"1999년에 유효한 문서가 있으면 안 됩니다: {len(kept)}건"


# ══════════════════════════════════════════════════════════════════════════
#  ④ 하이브리드가 실제로 낫는가 — ⚠ 이게 이 단계의 능력 목표다
# ══════════════════════════════════════════════════════════════════════════

def test_BM25_는_요금제_코드를_찾는가(documents):
    """⚠⚠ **Stage 3 에서 벡터가 못 하던 것을 BM25 가 한다.**

    글자가 일치하는 것을 찾는 검색이 왜 따로 필요한지가 여기서 드러난다.
    """
    from raglab.embedding import tokenize
    from raglab.retrieval import BM25

    toks = [tokenize(d.text) for d in documents]
    hits = BM25().fit(toks).search(tokenize("5G-STD-69"), k=3)
    top_ids = [documents[i].doc_id for i, _ in hits]
    assert any(t.startswith("PLANS") for t in top_ids), (
        f"요금제 코드로 요금안내를 못 찾았습니다: {top_ids}"
    )
