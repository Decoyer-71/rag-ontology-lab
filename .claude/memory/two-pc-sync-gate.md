---
name: two-pc-sync-gate
description: PC 두 대를 번갈아 쓴다 — 학습 상태가 커밋되므로 원격과 어긋나면 새 단계를 훅이 막는다
metadata: 
  node_type: memory
  type: project
  originSessionId: 1ba4b8fe-1a57-4687-bbeb-30c37efd9e72
  modified: 2026-09-10T13:06:19.024Z
---

사용자는 **PC 두 대를 번갈아** 학습을 진행한다(2026-09-10 확정). 이건 배포 편의가 아니라
**데이터 무결성 문제**다 — 이 저장소는 코드만이 아니라 **학습 상태 자체를 커밋**하기 때문이다:
`progress.json`(진도) · `review.json`(복습 카드·간격·이력) · `review_log.json`(인출 기록) ·
`docs/PROGRESS.md`(막힌 지점).

- **강제 지점**: `sync_check.ps1`(SessionStart, `git fetch`) 이 상태를 재고
  `guard_sync.ps1`(PreToolUse) 이 막는다. 막는 범위는 §14 복습 게이트와 **같다** —
  `next-step` · `docs/stages/` · `tests/test_stage*` · `src/raglab` 새 파일 · `progress.json`
- **`behind`·`diverged` 만 차단한다.** `ahead`(푸시 안 됨)는 **경고만** — 떠나기 전에 할 일이지
  지금 막을 일이 아니다. 여기서 막으면 작업 자체가 안 된다
- 판정 파일이 없으면(오프라인·훅 미실행) **통과**시킨다. fail-open 이 원칙이다
- ⚠⚠ **`review.json` 충돌은 합칠 수 없다.** 더 최근에 복습한 쪽을 택하고, 애매하면 그 카드만
  만기로 되돌린다 — 틀리게 합치느니 한 번 더 인출하는 편이 싸다

**Why:** 가장 흔한 사고는 「PC A 에서 푸시를 잊고 PC B 를 켜는 것」이다. `pull` 한 번이 5초인데
갈라진 `review.json` 을 손으로 합치는 것은 사람이 판단해야 하는 일이다. 비용 차이가 크다.

**How to apply:** 세션 시작 배너의 `[sync]` 줄을 먼저 본다. `ahead` 가 뜨면 **자리를 뜨기 전에 푸시**한다.
커밋으로 안 따라오는 것 넷은 `docs/SETUP.md` — venv · 저장소 밖 memory 폴더 · `data/external/` ·
`*_session.json`. 관련: [[review-gate-system]] · [[rag-ontology-lab-project]]
