"""Stage 3 — 벡터 검색 (코사인 유사도). 통과 조건이자 명세다."""
from __future__ import annotations

import numpy as np
import pytest

pytestmark = pytest.mark.stage3


def test_동일_벡터의_유사도는_1인가():
    from raglab.retrieval import cosine_similarity

    m = np.array([[1.0, 2.0, 3.0]])
    s = cosine_similarity(m, np.array([1.0, 2.0, 3.0]))
    assert s.shape == (1,)
    assert abs(float(s[0]) - 1.0) < 1e-9


def test_직교_벡터의_유사도는_0인가():
    from raglab.retrieval import cosine_similarity

    m = np.array([[1.0, 0.0], [0.0, 1.0]])
    s = cosine_similarity(m, np.array([1.0, 0.0]))
    assert abs(float(s[0]) - 1.0) < 1e-9
    assert abs(float(s[1])) < 1e-9


def test_크기에_흔들리지_않는가():
    """⚠⚠ **왜 각도인가** — 이 테스트가 그 답이다.

    같은 방향이면 길이가 10배여도 유사도는 같아야 한다.
    안 그러면 긴 문서가 내용과 무관하게 항상 이긴다.
    """
    from raglab.retrieval import cosine_similarity

    m = np.array([[1.0, 1.0], [10.0, 10.0]])
    s = cosine_similarity(m, np.array([1.0, 1.0]))
    assert abs(float(s[0]) - float(s[1])) < 1e-9, (
        "벡터 크기가 유사도를 바꿉니다 — 정규화가 빠졌거나 내적을 반환하고 있습니다"
    )


def test_손으로_계산한_값과_맞는가():
    """⚠ 종이에서 굴러간 숫자와 코드가 맞아야 이 단계가 닫힌다.

    [1,0] 과 [1,1] 의 각도는 45도 → cos45 = 1/√2 ≈ 0.7071
    """
    from raglab.retrieval import cosine_similarity

    s = cosine_similarity(np.array([[1.0, 1.0]]), np.array([1.0, 0.0]))
    assert abs(float(s[0]) - 1 / np.sqrt(2)) < 1e-9


@pytest.mark.breaks
def test_0벡터에서_nan_이_안_나오는가():
    """⚠⚠ **실제로 일어나는 경우다.**

    · 질의의 모든 단어가 어휘에 없으면 질의 벡터가 0
    · 빈 청크의 문서 벡터도 0

    0 으로 나누면 nan 이 나오고, **nan 은 정렬에서 조용히 이상하게 행동한다.**
    (`np.argsort` 는 nan 을 가장 큰 값으로 취급해 맨 뒤로 보낸다 — 또는 앞으로)
    """
    from raglab.retrieval import cosine_similarity

    m = np.array([[0.0, 0.0], [1.0, 1.0]])
    s = cosine_similarity(m, np.array([1.0, 1.0]))
    assert np.all(np.isfinite(s)), f"nan/inf 가 나왔습니다: {s}"

    s2 = cosine_similarity(m, np.array([0.0, 0.0]))
    assert np.all(np.isfinite(s2)), f"0 질의에서 nan/inf 가 나왔습니다: {s2}"


def test_top_k_가_내림차순인가():
    """⚠ `np.argsort` 는 오름차순이 기본이다. 그대로 쓰면 가장 안 맞는 것부터 나온다."""
    from raglab.retrieval import top_k

    scores = np.array([0.1, 0.9, 0.5, 0.7])
    assert top_k(scores, k=2) == [1, 3], "점수 높은 순이 아닙니다"


def test_top_k_가_후보보다_클_때_안_터지는가():
    from raglab.retrieval import top_k

    idx = top_k(np.array([0.3, 0.1]), k=10)
    assert len(idx) == 2, "후보보다 큰 k 에서 목록이 늘어나면 안 됩니다"


def test_동점에서_재현되는가():
    """⚠⚠ 동점 순서가 실행마다 바뀌면 측정이 재현되지 않는다 (§13-4)."""
    from raglab.retrieval import top_k

    scores = np.array([0.5, 0.5, 0.5, 0.5, 0.5])
    runs = [top_k(scores, k=3) for _ in range(5)]
    assert all(r == runs[0] for r in runs), "같은 입력에 다른 순서가 나왔습니다"


def test_검색이_점수와_함께_돌아오는가():
    """⚠ 점수 없이 순위만 보면 1등과 2등의 차이가 0.001 인지 0.5 인지 모른다."""
    from raglab.retrieval import search_dense

    m = np.array([[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]])
    out = search_dense(m, np.array([1.0, 0.0]), k=2)
    assert len(out) == 2
    assert all(isinstance(i, (int, np.integer)) and isinstance(s, float) for i, s in out)
    assert out[0][1] >= out[1][1], "점수 내림차순이 아닙니다"


# ══════════════════════════════════════════════════════════════════════════
#  실제 코퍼스 — 여기서 처음으로 「검색이 된다」를 본다
# ══════════════════════════════════════════════════════════════════════════

def test_실제_코퍼스에서_관련_문서를_찾는가(documents):
    """국제전화를 물으면 약관이 상위에 와야 한다."""
    from raglab.embedding import TfidfVectorizer
    from raglab.retrieval import search_dense

    texts = [d.text for d in documents]
    v = TfidfVectorizer().fit(texts)
    mat = v.transform(texts)
    q = v.transform(["국제전화 요금은 어떻게 부과되나요"])[0]

    hits = search_dense(mat, q, k=3)
    top_ids = [documents[i].doc_id for i, _ in hits]
    assert "TERMS-2026" in top_ids, f"약관이 상위 3위 안에 없습니다: {top_ids}"


@pytest.mark.breaks
def test_요금제_코드는_벡터로_잘_안_찾아지는가(documents):
    """⚠⚠ **이 테스트가 Stage 4 의 존재 이유다.**

    `5G-STD-69` 같은 코드는 임베딩이 「비슷한 뜻」으로 뭉갠다.
    벡터 검색만으로는 **정확히 그 코드**를 집어내기 어렵다.

    ⚠ 이 테스트는 「어렵다」를 확인하는 것이지 「불가능하다」를 주장하지 않는다.
      토큰화 방식에 따라 통과할 수도 있다 — 그러면 **그 사실을 PROGRESS.md 에 적고**
      왜 그런지(하이픈을 살렸는가?) 설명한 뒤 이 테스트를 갱신하라.
      그것도 유효한 학습이다.
    """
    from raglab.embedding import TfidfVectorizer, tokenize
    from raglab.retrieval import search_dense

    texts = [d.text for d in documents]
    v = TfidfVectorizer().fit(texts)
    mat = v.transform(texts)
    q = v.transform(["5G-STD-69"])[0]

    # 질의가 어휘에 하나도 안 걸리면 0 벡터 → 검색 자체가 무의미하다.
    # 그 경우도 「벡터로는 못 찾는다」의 한 형태다.
    if float(np.abs(q).sum()) == 0.0:
        pytest.skip("코드가 어휘에 없어 0 벡터입니다 — 그 자체가 Stage 4 의 근거입니다")

    hits = search_dense(mat, q, k=3)
    top_ids = [documents[i].doc_id for i, _ in hits]
    # 구버전과 신버전을 구분 못 하는 것이 전형적 증상이다
    assert not (top_ids[0] == "PLANS-2026" and hits[0][1] > 0.5), (
        f"벡터 검색이 코드를 정확히 집어냈습니다 (상위: {top_ids}). "
        "토큰화에서 하이픈을 어떻게 다루셨는지 PROGRESS.md 에 적고 이 테스트를 갱신하십시오"
    )
