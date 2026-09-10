"""Stage 1 — 청킹. 통과 조건이자 명세다.

⚠ 이 파일은 Claude 가 쓴다 (명세를 주는 것은 대필이 아니다 — CLAUDE.md §5-T).
  구현은 `src/raglab/chunking.py` 에서 **사용자가** 한다.

⚠⚠ 「깨지는 조건」 테스트(`@pytest.mark.breaks`)가 섞여 있다.
   잘 되는 예제만 있는 테스트는 가장 해롭다 (§10 원칙 3).
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.stage1


# ══════════════════════════════════════════════════════════════════════════
#  ① 글자수 청킹 — 나쁜 기준선
# ══════════════════════════════════════════════════════════════════════════

def test_글자수_청킹이_길이를_지키는가():
    from raglab.chunking import chunk_by_chars

    text = "가" * 1000
    chunks = chunk_by_chars(text, size=200, overlap=0)
    assert chunks, "청크가 하나도 안 나왔습니다"
    assert all(len(c) <= 200 for c in chunks), "size 를 넘는 청크가 있습니다"
    assert "".join(chunks) == text, "겹침 0일 때는 원문이 그대로 복원돼야 합니다"


def test_글자수_청킹이_겹침을_만드는가():
    """겹침은 경계에 걸친 문장이 양쪽에서 사라지는 것을 줄인다."""
    from raglab.chunking import chunk_by_chars

    text = "".join(str(i % 10) for i in range(300))
    chunks = chunk_by_chars(text, size=100, overlap=20)
    assert len(chunks) >= 3
    # 두 번째 청크의 앞 20자는 첫 청크의 끝 20자와 같아야 한다
    assert chunks[1][:20] == chunks[0][-20:], "겹침이 적용되지 않았습니다"


@pytest.mark.breaks
def test_겹침이_크기_이상이면_거부하는가():
    """⚠⚠ overlap >= size 면 창이 앞으로 못 나가 **무한 루프**가 된다.

    조용히 멈추는 대신 그 자리에서 터뜨려야 한다.
    """
    from raglab.chunking import chunk_by_chars

    with pytest.raises(ValueError):
        chunk_by_chars("아무거나", size=100, overlap=100)


@pytest.mark.breaks
def test_글자수_청킹이_요금표를_깨뜨리는가(plans_doc):
    """⚠⚠ **이 테스트가 Stage 1 의 존재 이유다.**

    글자수로 자르면 마크다운 표의 행 중간이 잘린다.
    잘린 청크를 인용한 답변은 숫자가 전부 틀린다 — 교본 STEP 2 「파싱 쓰레기」.

    여기서는 「깨진다」는 사실 자체를 **테스트로 고정**한다.
    나중에 구조 청킹이 이걸 고치는지 비교할 기준이 된다.
    """
    from raglab.chunking import chunk_by_chars

    chunks = chunk_by_chars(plans_doc.text, size=300, overlap=0)
    # 표 행(`|` 로 시작)이 중간에 잘린 청크가 하나라도 있어야 한다
    broken = [
        c for c in chunks
        if c.rstrip().endswith("|") is False and "|" in c.split("\n")[-1]
    ]
    assert broken, (
        "글자수 청킹인데 표가 하나도 안 깨졌습니다. "
        "size 를 조정하거나 코퍼스가 바뀌었는지 확인하십시오"
    )


# ══════════════════════════════════════════════════════════════════════════
#  ② 구조 청킹
# ══════════════════════════════════════════════════════════════════════════

def test_헤딩으로_쪼개고_경로를_붙이는가(terms_doc):
    from raglab.chunking import split_by_heading

    pairs = split_by_heading(terms_doc.text)
    assert len(pairs) >= 5, f"약관이 {len(pairs)}조각으로만 나뉘었습니다"
    labels = [lab for lab, _ in pairs]
    # 상위 헤딩이 경로에 이어져 있어야 한다 — 조각만 봐도 출처를 알아야 하므로
    assert any(">" in lab for lab in labels), (
        "경로 라벨에 상위 헤딩이 안 붙었습니다. "
        "청크 하나만 LLM 에 건네졌을 때 어느 장의 조항인지 알 수 없습니다"
    )
    assert any("제21조" in lab or "제21조" in body for lab, body in pairs)


def test_첫_헤딩_앞의_본문을_버리지_않는가():
    """⚠ 서문을 버리면 그 내용은 영영 검색되지 않는다."""
    from raglab.chunking import split_by_heading

    text = "서문입니다. 이 문장이 사라지면 안 됩니다.\n\n# 제목\n본문입니다.\n"
    pairs = split_by_heading(text)
    joined = "\n".join(body for _, body in pairs)
    assert "서문입니다" in joined, "첫 헤딩 앞의 본문이 버려졌습니다"


def test_표_줄을_판정하는가():
    from raglab.chunking import is_table_line

    assert is_table_line("| 요금제명 | 월 요금 |")
    assert is_table_line("|---|---|")
    assert is_table_line("  | 여백이 있어도 표 |  ")
    assert not is_table_line("일반 문장입니다")
    assert not is_table_line("")


@pytest.mark.breaks
def test_구조_청킹이_표를_지키는가(plans_doc):
    """⚠⚠ **Stage 1 의 능력 목표가 달성됐는지 재는 테스트다.**

    표 한 개 = 청크 한 개. 표가 여러 청크로 쪼개지면 안 된다.
    """
    from raglab.chunking import chunk_by_structure, is_table_line

    chunks = chunk_by_structure(plans_doc.text, doc_id="PLANS-2026", max_chars=400)
    assert chunks, "청크가 안 나왔습니다"

    for c in chunks:
        lines = [ln for ln in c.text.split("\n") if ln.strip()]
        table_lines = [ln for ln in lines if is_table_line(ln)]
        if not table_lines:
            continue
        # 표가 들어 있다면, 그 표는 헤더+구분선+본문이 온전해야 한다
        assert len(table_lines) >= 3, (
            f"표가 {len(table_lines)}줄로 잘렸습니다 — 표 한 개는 한 청크에 있어야 합니다.\n"
            f"청크 내용: {c.text[:120]}"
        )


def test_청크에_메타데이터가_실리는가(plans_doc):
    """⚠⚠ 교본 §1-2 — 메타데이터는 **나중에 못 넣는다.** 전체 재색인이다.

    유효일자·권한등급으로 검색 단계에서 거르려면 지금 실려 있어야 한다 (Stage 4).
    """
    from raglab.chunking import chunk_by_structure

    chunks = chunk_by_structure(plans_doc.text, doc_id="PLANS-2026", meta=plans_doc.meta)
    assert chunks
    for c in chunks:
        assert c.doc_id == "PLANS-2026"
        assert c.meta.get("effective_from"), "effective_from 이 청크에 안 실렸습니다"
        assert c.path_label, "path_label 이 비었습니다"


def test_max_chars_를_대체로_지키는가(terms_doc):
    """⚠ 표 때문에 넘는 것은 허용한다. 그게 설계 의도다.

    다만 표가 없는데 넘으면 쪼개기가 동작하지 않은 것이다.
    """
    from raglab.chunking import chunk_by_structure, is_table_line

    chunks = chunk_by_structure(terms_doc.text, doc_id="TERMS-2026", max_chars=600)
    for c in chunks:
        if any(is_table_line(ln) for ln in c.text.split("\n")):
            continue
        assert len(c.text) <= 900, (
            f"표가 없는데 {len(c.text)}자입니다 (한도 600, 여유 300). 쪼개기가 안 됩니다"
        )


def test_코퍼스_전체_청킹이_재현되는가(documents):
    """⚠ 두 번 돌려 같은 결과가 나와야 한다. 순서가 흔들리면 측정이 재현되지 않는다 (§13-4)."""
    from raglab.chunking import chunk_documents

    a = chunk_documents(documents)
    b = chunk_documents(documents)
    assert len(a) == len(b) and a and len(a) >= 30, f"청크가 {len(a)}개뿐입니다"
    assert [(c.doc_id, c.chunk_id, c.text) for c in a] == [
        (c.doc_id, c.chunk_id, c.text) for c in b
    ], "같은 입력에 다른 결과가 나왔습니다 — 재현성이 깨집니다"


def test_구버전_문서가_구분되는가(documents):
    """⚠ `plans_2025.md` 는 구버전이다. 청크에 그 사실이 실려야 Stage 4 에서 거를 수 있다."""
    from raglab.chunking import chunk_documents

    chunks = chunk_documents(documents)
    old = [c for c in chunks if c.meta.get("superseded_by")]
    assert old, "구버전 표시(superseded_by)가 실린 청크가 없습니다"
    assert all(c.doc_id == "PLANS-2025" for c in old)
