---
name: suspect-goldenset-contamination
description: 검색 성능이 이상하게 좋으면 축하가 아니라 골든셋 오염을 먼저 의심한다
metadata:
  type: feedback
---

**Recall@5 가 0.95 이상이면 경보다.** 골든셋으로 튜닝하고 같은 골든셋으로 평가했는지 먼저 확인한다.

**Why:** 지도학습의 데이터 누수와 같은 병이다. 튜닝에 쓴 평가셋의 수치는 낙관 편향돼 있고, 그 상태로 "검색이 잘 된다"고 적으면 다음 판단이 전부 그 위에 쌓인다. oil_DA 의 [[suspect-leakage-first]] 와 같은 실패 모드다.

**How to apply:** 골든셋을 **dev / holdout 으로 나눠** 두고 보류분은 단계가 닫힐 때만 연다. 이상하게 좋은 수치를 만나면 ① 질의가 문서 원문을 그대로 포함하지 않는지 ② 정답 청크가 후보 집합에 미리 들어가 있지 않은지 ③ 합성 코퍼스 생성기가 심어 둔 패턴을 그대로 재발견한 것은 아닌지 순서로 본다. 관련: [[measure-with-baseline]]
