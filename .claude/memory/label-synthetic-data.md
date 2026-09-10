---
name: label-synthetic-data
description: 한빛텔레콤 코퍼스는 전부 합성이며 모든 산출물에 표기한다
metadata:
  type: feedback
---

`data/synthetic/` 은 **전부 합성이다.** 한빛텔레콤·요금제·고객·수치 전부 교육용 가상 설정이며 실재하지 않는다. **산출물 최상단에 배너로 표기한다.**

**Why:** 합성에서 나온 Recall 수치가 「RAG 는 이 정도 성능이다」로 읽히는 순간 그 산출물은 틀린 것보다 나쁘다 — 틀린 줄 모르고 인용되기 때문이다. 포트폴리오라면 더더욱. 그리고 **내가 심은 구조만 발견된다**: 코퍼스 생성기가 넣어 둔 패턴을 「발견」이라고 부르면 안 된다.

**How to apply:** `labkit.report` 의 `synthetic=True` 를 쓴다. `guard_claim.ps1` 훅이 `outputs/*.html` 에 「합성」과 「한계」가 있는지 기계적으로 확인한다. 합성의 한계를 재는 유일한 장치는 Stage 10 의 KorQuAD 실데이터 이식이다. 관련: [[measure-with-baseline]]
