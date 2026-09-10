"""코퍼스 로더 — 학습 대상이 아닌 배관이다.

⚠ 왜 이게 `raglab` 이 아니라 `labkit` 에 있는가
    파일을 읽고 YAML front matter 를 떼는 것은 RAG 의 메커니즘이 아니다.
    사용자가 손으로 짜야 하는 것은 **청킹부터**다 (CLAUDE.md §5-T).
    여기서 시간을 쓰면 정작 배울 것에 쓸 시간이 준다.

⚠⚠ 여기서 나오는 모든 문서는 **합성**이다 (CLAUDE.md §3-S).
"""
from __future__ import annotations

import csv
import json
import pathlib
from dataclasses import dataclass, field
from typing import Any

import yaml

# 저장소 루트 — 이 파일 기준 세 단계 위 (src/labkit/corpus.py → 루트)
ROOT = pathlib.Path(__file__).resolve().parents[2]
SYNTHETIC = ROOT / "data" / "synthetic"


@dataclass(frozen=True)
class Document:
    """문서 하나. 본문과 메타데이터를 함께 들고 다닌다.

    ⚠ 메타데이터를 본문과 분리해 두면 나중에 못 넣는다 — 교본 §1-2 「메타데이터는 RAG 의 숨은 절반」.
      유효일자·권한등급으로 **검색 단계에서** 거르려면 인덱스에 같이 실려 있어야 한다.
    """

    doc_id: str
    title: str
    doc_type: str
    text: str
    path: pathlib.Path
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def effective_from(self) -> str:
        return str(self.meta.get("effective_from", ""))

    @property
    def is_superseded(self) -> bool:
        """구버전인가. 신버전이 있으면 검색에서 걸러야 한다 (교본 §1-6 함정 03)."""
        return bool(self.meta.get("superseded_by"))

    @property
    def acl(self) -> str:
        return str(self.meta.get("acl", "PUBLIC"))


def _split_front_matter(raw: str) -> tuple[dict[str, Any], str]:
    """`---` 로 감싼 YAML front matter 를 본문에서 떼어 낸다.

    Returns:
        (메타데이터 dict, 본문 문자열)

    ⚠ front matter 가 없으면 빈 dict 와 원문 전체를 돌려준다 — 예외를 던지지 않는다.
      외부 문서를 붙일 때 메타 없이 들어오는 경우가 있다.
    """
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        return {}, raw
    return meta, parts[2].lstrip("\n")


def load_documents(docs_dir: pathlib.Path | None = None) -> list[Document]:
    """합성 코퍼스의 문서를 전부 읽는다.

    ⚠ 파일명 순으로 정렬해 돌려준다 — 순서가 실행마다 바뀌면 측정이 재현되지 않는다
      (CLAUDE.md §13-4 재현성).
    """
    d = docs_dir or (SYNTHETIC / "docs")
    out: list[Document] = []
    for p in sorted(d.glob("*.md")):
        meta, body = _split_front_matter(p.read_text(encoding="utf-8"))
        out.append(
            Document(
                doc_id=str(meta.get("doc_id", p.stem)),
                title=str(meta.get("title", p.stem)),
                doc_type=str(meta.get("doc_type", "")),
                text=body,
                path=p,
                meta=meta,
            )
        )
    return out


def load_triples(path: pathlib.Path | None = None) -> list[tuple[str, str, str]]:
    """지식그래프 트리플 (주어, 술어, 목적어).

    ⚠ 수치 비교(「더 싼 요금제」)는 이걸로 못 한다 — 목적어가 문자열이다.
      `load_plan_attrs()` 를 함께 쓴다 (Stage 7).
    """
    p = path or (SYNTHETIC / "triples.csv")
    with p.open(encoding="utf-8", newline="") as f:
        return [(r["subject"], r["predicate"], r["object"]) for r in csv.DictReader(f)]


def load_plan_attrs(path: pathlib.Path | None = None) -> dict[str, dict[str, Any]]:
    """요금제 속성 (월요금·데이터·망). 수치 비교용."""
    p = path or (SYNTHETIC / "plan_attrs.json")
    return json.loads(p.read_text(encoding="utf-8"))


def load_concepts(path: pathlib.Path | None = None) -> dict[str, Any]:
    """개념사전. `{"concepts": [...], "rules": [...]}` 형태.

    ⚠ 「3망 해지」·「W코드」는 **어느 문서에도 정의가 없다.** 그래서 이 파일이 필요하다 (Stage 6).
    """
    p = path or (SYNTHETIC / "concepts.yaml")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def load_golden_set(
    path: pathlib.Path | None = None, split: str | None = None
) -> list[dict[str, Any]]:
    """골든셋(RAG 채점표)을 읽는다.

    Args:
        split: "dev" | "holdout" | None(전체)

    ⚠⚠ **기본값이 전체가 아니라는 점을 기억하라.**
      튜닝 중에는 `split="dev"` 만 쓴다. holdout 으로 튜닝하면 그 수치는 낙관 편향이다
      (CLAUDE.md §5-E' 골든셋 오염 금지).
    """
    p = path or (SYNTHETIC / "golden_set.yaml")
    qs = yaml.safe_load(p.read_text(encoding="utf-8"))["questions"]
    if split is None:
        return qs
    return [q for q in qs if q.get("split") == split]


def load_competency_questions(path: pathlib.Path | None = None) -> list[dict[str, Any]]:
    """역량질문(온톨로지 채점표). 교본 온톨로지 STEP 1."""
    p = path or (SYNTHETIC / "competency_questions.yaml")
    return yaml.safe_load(p.read_text(encoding="utf-8"))["questions"]


def corpus_summary() -> str:
    """지금 코퍼스가 어떤 상태인지 한눈에. 세션 시작이나 디버깅 때 쓴다."""
    docs = load_documents()
    tri = load_triples()
    con = load_concepts()
    gold = load_golden_set()
    dev = [q for q in gold if q.get("split") == "dev"]
    hold = [q for q in gold if q.get("split") == "holdout"]
    types: dict[str, int] = {}
    for q in gold:
        types[q["type"]] = types.get(q["type"], 0) + 1

    lines = [
        "⚠ 합성 코퍼스입니다 (한빛텔레콤은 가상 회사입니다)",
        f"  문서     : {len(docs)}건  (구버전 {sum(d.is_superseded for d in docs)}건 포함)",
        f"  트리플   : {len(tri)}건",
        f"  개념     : {len(con['concepts'])}건 · 규칙 {len(con['rules'])}건",
        f"  골든셋   : dev {len(dev)} / holdout {len(hold)}  — {types}",
        f"  역량질문 : {len(load_competency_questions())}건",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print(corpus_summary())
