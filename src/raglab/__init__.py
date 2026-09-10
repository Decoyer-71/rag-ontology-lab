"""raglab — ⭐ **사용자가 직접 채우는 패키지.**

⚠⚠ CLAUDE.md §5-T — Claude 는 이 패키지의 알고리즘 본체를 쓰지 않는다.
   `guard_handson.ps1` 훅이 `raise NotImplementedError` 가 줄어드는 편집을 기계적으로 차단한다.

이 저장소의 목적은 「돌아가는 RAG」가 아니라 「이해」다.
코드가 다 채워졌는데 왜 그런지 설명하지 못하면 실패한 것이다.

  chunking  (Stage 1) : 문서를 검색 단위로 자른다
  embedding (Stage 2) : 의미를 숫자 배열로 바꾼다 — TF-IDF 직접 구현
  retrieval (Stage 3·4): 가까운 것을 찾는다 — 코사인 · BM25 · RRF
  evaluate  (Stage 5) : 얼마나 맞히는지 잰다 — Recall@k · MRR · A/B/C 분해

  Stage 6 이후(ontology · graph · pipeline)는 **백지**다.
  파일 구조부터 직접 설계한다 → docs/stages/ 의 명세와 tests/ 를 보라.
"""

__all__ = ["chunking", "embedding", "retrieval", "evaluate"]
