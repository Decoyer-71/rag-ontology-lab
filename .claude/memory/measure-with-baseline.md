---
name: measure-with-baseline
description: 개선을 주장할 때는 기준선 수치를 같은 표에 놓는다
metadata:
  type: feedback
---

RAG 기법을 하나 추가했으면 **넣기 전 수치와 넣은 후 수치를 같은 표에** 놓는다. **아무것도 없는 기준선**(무작위 k건 / 앞에서 k건)을 항상 포함한다. 그걸 못 이기는 검색기는 실패한 검색기다.

**Why:** 교본이 RAG 실패 1순위로 꼽은 것이 *골든셋 없이 튜닝한다* 이다. 체감으로 판단하면 튜닝이 미신이 된다. 포트폴리오 관점에서도 「돌아간다」는 변별력이 0이고 「측정했다」가 차별점이다.

**How to apply:** 측정 결과는 `outputs/metrics/stageNN.json` 에 남긴다 — 이게 쌓인 것이 README 결과 표가 된다. **바뀐 지표 전부**를 본다(Recall 만 올리고 다른 게 떨어진 것을 감추지 않는다). 모든 수치에 **분모**를 붙인다: "0.72" 가 아니라 "0.72 (골든셋 25문항 중 18)". 관련: [[suspect-goldenset-contamination]] · [[label-synthetic-data]]
