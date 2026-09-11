---
name: two-pc-sync-gate
description: PC 두 대를 번갈아 쓴다 — 받을 땐 자동 ff, 올릴 땐 개인정보 관문을 거친 자동 푸시, 어긋나면 새 단계를 막는다
metadata:
  type: project
---

사용자는 **PC 두 대를 번갈아** 학습을 진행한다(2026-09-10 확정). 이건 배포 편의가 아니라
**데이터 무결성 문제**다 — 이 저장소는 코드만이 아니라 **학습 상태 자체를 커밋**하기 때문이다:
`progress.json`(진도) · `review.json`(복습 카드·간격·이력) · `review_log.json`(인출 기록) ·
`docs/PROGRESS.md`(막힌 지점).

- **받는 쪽** — `session_start.ps1`(SessionStart)이 `sync_check → 배너 → commit_watch → review_due` **순서로** 부른다.
  같은 이벤트의 훅은 병렬로 돌기 때문에 한 스크립트로 묶었다. `sync_check` 는 behind · 내 커밋 없음 · 미커밋 0 이면
  `merge --ff-only` 로 **자동으로 받는다** — 그래야 복습 계획이 받은 뒤의 `review.json` 을 본다
- **막는 것** — `guard_sync.ps1` 이 `behind`(자동으로 못 받은 경우) · `diverged` 에서 새 단계를 막는다.
  범위는 §14 복습 게이트와 같다. `ahead` 는 경고만. 판정 없음(오프라인)은 통과
- **떠나는 쪽** — `leave_check.ps1`(Stop)이 미커밋 · 안 올라간 커밋을 화면에 알린다(같은 상태면 20분에 한 번).
  `.githooks/post-commit` 이 **커밋하자마자 푸시**한다 — 그 전에 개인정보 관문(pre-commit · commit-msg · pre-push)을 거친다
- **메모리** — 실제 메모리 폴더는 `link_memory.ps1` 로 저장소 `.claude/memory/` 에 정션 연결 → git 으로 따라온다
- ⚠⚠ **`review.json` 충돌은 합칠 수 없다.** 더 최근에 복습한 쪽을 택하고, 애매하면 그 카드만 만기로 되돌린다

**Why:** 가장 흔한 사고는 「PC A 에서 푸시를 잊고 PC B 를 켜는 것」인데, B 의 게이트는 원격만 보므로
**A 에 두고 온 것을 못 본다.** 그래서 떠나는 쪽(자동 푸시 · Stop 알림)과 받는 쪽(자동 ff · 게이트)을 둘 다 지킨다.

**How to apply:** 세션 시작 `[sync]` 줄과 응답 끝 `[떠나기 전 점검]` 줄을 본다. PC 마다 한 번씩 필요한 것 —
venv · `link_memory.ps1` · `git config core.hooksPath .githooks` · `data/external/`(Stage 10).
⚠ 관문을 켠 PC 에서는 **커밋 = 공개**다 — Claude 가 커밋할 때는 사용자 확인.
관련: [[review-gate-system]] · [[memory-is-public]] · [[git-identity-yoon71]]
