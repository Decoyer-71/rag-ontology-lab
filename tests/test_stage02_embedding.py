"""Stage 2 — 임베딩 (TF-IDF). 통과 조건이자 명세다."""
from __future__ import annotations

import math

import numpy as np
import pytest

pytestmark = pytest.mark.stage2


# ── 손으로 따라갈 수 있는 장난감 코퍼스 ────────────────────────────────────
# ⚠ 문서 3건 · 단어 몇 개. **종이에서 숫자가 굴러가야** 이 단계가 닫힌다.
TOY = [
    "해지 해지 요금",   # '해지'가 2번 — TF 가 높다
    "요금 데이터",
    "요금 청약철회",    # '청약철회'는 여기만 — IDF 가 높다
]


# ══════════════════════════════════════════════════════════════════════════
#  ① 토크나이즈
# ══════════════════════════════════════════════════════════════════════════

def test_기본_토큰화():
    from raglab.embedding import tokenize

    assert tokenize("요금제 안내") == ["요금제", "안내"]
    assert tokenize("") == []
    assert tokenize("   ") == []


def test_구두점을_털어내는가():
    from raglab.embedding import tokenize

    toks = tokenize("해지, 청약철회. 그리고 (환불)!")
    assert "해지" in toks and "청약철회" in toks and "환불" in toks
    assert not any("," in t or "." in t or "(" in t for t in toks), (
        "구두점이 토큰에 붙어 있습니다 — '환불)' 은 '환불' 과 다른 단어가 됩니다"
    )


def test_대소문자를_통일하는가():
    from raglab.embedding import tokenize

    assert tokenize("LTE") == tokenize("lte"), "대소문자가 다른 단어로 취급됩니다"


@pytest.mark.breaks
def test_한국어_조사_한계가_실재하는가():
    """⚠⚠ **이 테스트는 「실패를 고정」한다.**

    형태소 분석기 없이 공백으로 자르면 "요금제는" 과 "요금제" 는 다른 단어가 된다.
    이건 이 프로젝트의 알려진 근사(approximation)이고, **고치지 않는다** (§2 — 형태소 분석기 없음).

    중요한 것은 **그 사실을 아는 채로 그렇게 하는 것**이다.
    Stage 5 에서 이 근사가 어떤 질의를 망가뜨리는지 측정으로 확인한다.
    """
    from raglab.embedding import tokenize

    assert tokenize("요금제는") != tokenize("요금제"), (
        "조사가 분리됐습니다. 형태소 분석기를 넣으셨다면 "
        "docs/PROGRESS.md 에 그 결정과 이유를 적고 이 테스트를 갱신하십시오"
    )


# ══════════════════════════════════════════════════════════════════════════
#  ② 어휘
# ══════════════════════════════════════════════════════════════════════════

def test_어휘가_정렬돼_있는가():
    """⚠⚠ 순서가 실행마다 바뀌면 벡터가 달라지고 측정이 재현되지 않는다 (§13-4)."""
    from raglab.embedding import build_vocabulary, tokenize

    toks = [tokenize(t) for t in TOY]
    vocab = build_vocabulary(toks)
    assert vocab == sorted(vocab), "어휘가 정렬돼 있지 않습니다 (set 을 그대로 list 로 만드셨나요?)"
    assert set(vocab) == {"해지", "요금", "데이터", "청약철회"}


def test_min_df_가_동작하는가():
    """⚠ DF 는 **문서 빈도**다. 총 등장 횟수가 아니다."""
    from raglab.embedding import build_vocabulary, tokenize

    toks = [tokenize(t) for t in TOY]
    vocab = build_vocabulary(toks, min_df=2)
    # '요금'은 3문서 전부에 있고, '해지'는 1문서에만 (2번 나오지만 DF=1)
    assert "요금" in vocab
    assert "해지" not in vocab, "DF 를 문서 수가 아니라 등장 횟수로 세신 것 같습니다"


# ══════════════════════════════════════════════════════════════════════════
#  ③ TF · IDF
# ══════════════════════════════════════════════════════════════════════════

def test_TF_행렬의_형태가_문서by단어인가():
    """⚠ 이 방향을 헷갈리면 뒤 계산이 전부 틀린다."""
    from raglab.embedding import build_vocabulary, compute_tf, tokenize

    toks = [tokenize(t) for t in TOY]
    vocab = build_vocabulary(toks)
    tf = compute_tf(toks, vocab)
    assert tf.shape == (len(TOY), len(vocab)), (
        f"형태가 {tf.shape} 입니다. (문서 {len(TOY)}, 어휘 {len(vocab)}) 여야 합니다"
    )


def test_TF_가_빈도를_반영하는가():
    from raglab.embedding import build_vocabulary, compute_tf, tokenize

    toks = [tokenize(t) for t in TOY]
    vocab = build_vocabulary(toks)
    tf = compute_tf(toks, vocab)
    i해지, i요금 = vocab.index("해지"), vocab.index("요금")
    # 문서 0 은 '해지' 2번, '요금' 1번
    assert tf[0, i해지] > tf[0, i요금], "같은 문서 안에서 더 많이 나온 단어가 더 커야 합니다"
    assert tf[1, i해지] == 0, "안 나온 단어는 0 이어야 합니다"


def test_IDF_가_흔한_단어를_깎는가():
    """⚠⚠ **IDF 가 무엇을 보정하는가** — 이 단계의 핵심 질문이다.

    '요금'은 3문서 전부에 있다 → 일치해도 정보가 거의 없다 → 낮아야 한다
    '청약철회'는 1문서에만 있다 → 일치하면 강한 신호다 → 높아야 한다
    """
    from raglab.embedding import build_vocabulary, compute_idf, tokenize

    toks = [tokenize(t) for t in TOY]
    vocab = build_vocabulary(toks)
    idf = compute_idf(toks, vocab)
    assert idf.shape == (len(vocab),)
    assert idf[vocab.index("청약철회")] > idf[vocab.index("요금")], (
        "드문 단어의 IDF 가 흔한 단어보다 높지 않습니다"
    )


def test_IDF_에_nan_이나_inf_가_없는가():
    """⚠ `log(0)` 이나 0 나눗셈이 들어가면 조용히 nan 이 퍼진다."""
    from raglab.embedding import build_vocabulary, compute_idf, tokenize

    toks = [tokenize(t) for t in TOY]
    idf = compute_idf(toks, build_vocabulary(toks))
    assert np.all(np.isfinite(idf)), f"IDF 에 nan/inf 가 있습니다: {idf}"


# ══════════════════════════════════════════════════════════════════════════
#  ④ 벡터라이저
# ══════════════════════════════════════════════════════════════════════════

def test_fit_전_transform_은_거부하는가():
    """⚠ `NotImplementedError` 는 `RuntimeError` 의 **하위 클래스**다.

    그래서 `pytest.raises(RuntimeError)` 만 쓰면 **미구현 상태에서도 통과한다** —
    가짜 통과는 진도를 잘못 알린다. 미구현과 정상 거부를 구분해야 한다.
    """
    from raglab.embedding import TfidfVectorizer

    with pytest.raises(RuntimeError) as exc:
        TfidfVectorizer().transform(["아무거나"])
    assert not isinstance(exc.value, NotImplementedError), (
        "아직 구현되지 않았습니다 (NotImplementedError). "
        "fit 전 호출을 RuntimeError 로 거부하도록 구현하십시오"
    )


def test_fit_transform_형태():
    from raglab.embedding import TfidfVectorizer

    v = TfidfVectorizer()
    m = v.fit_transform(TOY)
    assert m.shape == (len(TOY), len(v.vocab))
    assert np.all(np.isfinite(m))


def test_질의_변환이_같은_차원인가():
    """⚠⚠ 질의를 `fit` 에 넣으면 안 된다 — 어휘와 IDF 가 오염된다 (§5-E' 와 같은 병)."""
    from raglab.embedding import TfidfVectorizer

    v = TfidfVectorizer().fit(TOY)
    q = v.transform(["해지 요금"])
    assert q.shape == (1, len(v.vocab)), "질의 벡터의 차원이 문서와 다릅니다"


@pytest.mark.breaks
def test_미등록_질의는_0벡터가_되는가():
    """⚠⚠ **이 경우가 Stage 3 에서 0 나눗셈을 만든다.**

    어휘에 없는 단어는 조용히 버려진다. 전부 미등록이면 0 벡터다.
    그 상태로 코사인을 계산하면 0/0 이다 — Stage 3 에서 처리해야 한다.
    """
    from raglab.embedding import TfidfVectorizer

    v = TfidfVectorizer().fit(TOY)
    q = v.transform(["존재하지않는단어xyz"])
    assert float(np.abs(q).sum()) == 0.0, "미등록 단어인데 0 벡터가 아닙니다"


def test_실제_코퍼스에서_동작하는가(documents):
    """장난감이 아니라 진짜 15건에서. ⚠ 여기서 처음으로 규모가 드러난다."""
    from raglab.embedding import TfidfVectorizer

    v = TfidfVectorizer(min_df=1)
    m = v.fit_transform([d.text for d in documents])
    assert m.shape[0] == len(documents)
    assert len(v.vocab) > 300, f"어휘가 {len(v.vocab)}개뿐입니다 — 토큰화를 확인하십시오"
    assert np.all(np.isfinite(m))
    # 요금제 코드가 어휘에 살아 있는가 (Stage 4 코드조회의 전제)
    joined = " ".join(v.vocab)
    assert "5g" in joined or "5G-STD-69".lower() in joined, (
        "요금제 코드의 흔적이 어휘에 없습니다. Stage 4 코드조회가 불가능해집니다"
    )


def test_재현되는가(documents):
    """⚠ 두 번 돌려 같은 행렬이 나와야 한다 (§13-4)."""
    from raglab.embedding import TfidfVectorizer

    texts = [d.text for d in documents]
    a = TfidfVectorizer().fit_transform(texts)
    b = TfidfVectorizer().fit_transform(texts)
    assert np.allclose(a, b), "같은 입력에 다른 벡터가 나왔습니다"
