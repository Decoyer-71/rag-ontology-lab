---
name: learner-writes-code
description: 이 저장소에서 src/raglab 의 알고리즘 본체는 Claude 가 아니라 사용자가 쓴다
metadata:
  type: feedback
---

`rag-ontology-lab` 에서 **`src/raglab/` 의 알고리즘 본체는 사용자가 직접 쓴다.** Claude 는 시그니처·독스트링·`TODO`·테스트·힌트까지다.

**Why:** 사용자 요구사항 원문 — *"단순 클로드가 코드를 짜주는게 아닌 사용자가 직접 코드를 작성하고 작동 알고리즘을 이해하도록 구성"*. 이 저장소의 목적은 돌아가는 RAG 가 아니라 이해다. 코드가 다 채워졌는데 왜 그런지 설명 못 하면 실패한 것이고, 기업 지원 포트폴리오로 나가므로 면접 한 질문에 드러난다.

**How to apply:** 막힌 사용자에게는 [[hint-not-answer]] 대로 단계적 힌트를 준다. `guard_handson.ps1` 훅이 `TODO`(=`raise NotImplementedError`) 개수가 줄어드는 편집을 기계적으로 차단한다. 사용자가 **명시적으로** 대필을 요청한 경우에만 `.claude/state/handson_override.json` 에 등재하고 `docs/PROGRESS.md` 에 기록한 뒤 진행한다. 관련: [[honorific-tone]]
