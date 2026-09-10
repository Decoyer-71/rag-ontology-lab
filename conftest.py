"""pytest 공용 설정 — `src/` 를 import 경로에 넣는다.

⚠ 왜 패키지 설치(`pip install -e .`) 대신 이 방식인가
    이 저장소는 학습용이고, 빌드 도구(setuptools·hatchling)를 의존성에 더하고 싶지 않다.
    `conftest.py` 는 pytest 가 **자동으로** 먼저 읽으므로 추가 설정이 필요 없다.
    (CLAUDE.md §9 — 가장 단순한 방법으로 되면 거기서 멈춘다)
"""
from __future__ import annotations

import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(scope="session")
def documents():
    """합성 코퍼스 문서 15건. ⚠ 전부 가상 데이터다 (CLAUDE.md §3-S)."""
    from labkit.corpus import load_documents

    return load_documents()


@pytest.fixture(scope="session")
def golden_dev():
    """골든셋 dev 분할. ⚠ holdout 은 단계가 닫힐 때만 연다 (§5-E')."""
    from labkit.corpus import load_golden_set

    return load_golden_set(split="dev")


@pytest.fixture(scope="session")
def triples():
    """지식그래프 트리플 49건."""
    from labkit.corpus import load_triples

    return load_triples()


@pytest.fixture(scope="session")
def concepts():
    """개념사전. `{"concepts": [...], "rules": [...]}`."""
    from labkit.corpus import load_concepts

    return load_concepts()


@pytest.fixture
def plans_doc(documents):
    """요금안내 2026 — ⚠ 표가 들어 있어 청킹 테스트의 핵심 재료다."""
    for d in documents:
        if d.doc_id == "PLANS-2026":
            return d
    pytest.fail("PLANS-2026 문서가 없습니다. data/make_corpus.py 를 실행하십시오")


@pytest.fixture
def terms_doc(documents):
    """이용약관 2026 — 조(條) 구조가 있어 구조 청킹 테스트에 쓴다."""
    for d in documents:
        if d.doc_id == "TERMS-2026":
            return d
    pytest.fail("TERMS-2026 문서가 없습니다. data/make_corpus.py 를 실행하십시오")
