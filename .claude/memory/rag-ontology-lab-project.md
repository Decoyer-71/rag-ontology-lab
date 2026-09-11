---
name: rag-ontology-lab-project
description: rag-ontology-lab 는 RAG·온톨로지를 손으로 짜서 배우는 학습 실습실이자 기업 지원 포트폴리오다 — PC 두 대를 오간다
metadata:
  type: project
---

`rag-ontology-lab` — RAG·온톨로지 **학습 실습실**. 2026-09-10 환경 구축 완료, 학습은 미착수.
⚠ **PC 두 대(집 데스크탑 · 노트북)를 번갈아 쓴다** — 저장소 루트가 PC 마다 다르다(`CLAUDE.md` §2).

원격: https://github.com/Decoyer-71/rag-ontology-lab (**공개**, `main`).
GitHub 계정 `Decoyer-71` · LICENSE 저작자 `DECOYER71` · 커밋 저자 `YOON71`.

목적은 둘이다 — ① 메커니즘을 **손으로 짜서** 이해 ② 그 결과를 **기업 지원 포트폴리오**로 GitHub 등재.
①이 본체다. 코드가 다 채워졌는데 왜 그런지 설명 못 하면 실패한 것이고, 면접 한 질문에 드러난다.

교재는 사용자가 받은 「RAG와 온톨로지 구축 교본」(한빛텔레콤 가상사례)이고, 코퍼스는 그 사례를 그대로 구현한 합성 데이터다.
커리큘럼 12단계 — 채점표 → 청킹 → TF-IDF → 코사인 → BM25/RRF → A·B·C 분해 → 개념 정규화 → 3홉 그래프 → 규칙·통합 → 신경망 임베딩 → KorQuAD 실데이터 이식 → 패키징.

**Why:** 학습자는 **트랜스포머 개념까지는 알고 RAG 내부는 표면적으로만** 안다. 이 두 줄이 모든 설명의 기준선이다. 비유는 트랜스포머 쪽에 걸고, IR 용어(BM25·MRR·재순위)는 첫 등장 시 풀이를 붙인다.

**How to apply:** 규율 전문은 저장소의 `CLAUDE.md` 에 있고 세션마다 자동으로 읽힌다. ✅ `CLAUDE.md` §0-2 는 2026-09-10 에 확정됐다 — **코퍼스는 한빛텔레콤 가상사례**, 실습 강도는 Stage 1~5 빈칸 → 6~11 백지, Stage 9 신경망 임베딩은 Stage 8 이후 판단(측정 순서가 이유이고, 어느 PC 에서 할지도 그때 정한다). ⚠ 골든셋이 이미 있어 **Stage 0 은 「만들기」가 아니라 「검수하고 문항을 추가하기」**다. 관련: [[learner-writes-code]] · [[measure-with-baseline]] · [[review-gate-system]] · [[two-pc-sync-gate]] · [[git-identity-yoon71]]
