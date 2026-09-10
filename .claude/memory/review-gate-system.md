---
name: review-gate-system
description: 복습을 안 하면 새 단계를 못 열게 훅으로 강제한다 — 복습은 다시 읽기가 아니라 인출이다
metadata: 
  node_type: memory
  type: project
  originSessionId: 1ba4b8fe-1a57-4687-bbeb-30c37efd9e72
  modified: 2026-09-10T12:43:07.152Z
---

2026-09-10 사용자 요구로 만든 **복습 게이트**(`CLAUDE.md` §14). 사용자가 못박은 조건은
*"단순 md파일로 남기는데 그치지말고 강제적인 로직으로 적용"* 이었다.

- **강제 지점**: `guard_review.ps1` (PreToolUse `Write|Edit|NotebookEdit|Skill`). 밀린 카드가 있으면
  **Claude 가 새 단계를 여는 행위**를 막는다 — `next-step` 스킬 · `docs/stages/` · `tests/test_stage*` ·
  `src/raglab/` **새 파일** · `progress.json`
- ⚠⚠ **막지 않는 것**: `review`·`hint`·`checkpoint` 스킬, `review*.json`, `docs/PROGRESS.md`,
  그리고 **`src/raglab/` 의 기존 파일**. 마지막 것을 막았다가 데드락을 만들었다 —
  복습의 코드 카드가 바로 그 파일을 빈칸으로 되돌리는 동작이기 때문이다
- **복습 = 인출**. 개념 카드는 `checkpoint` 가 던졌던 「왜」 질문을 다시 묻고, 코드 카드는
  **이미 통과시킨 함수를 빈칸으로 되돌려 다시 짜게** 한다. 정답 키는 git history, 채점표는 `tests/` 다
- **카드는 `checkpoint` 스킬 7절에서만 만들어진다.** 거기서 안 만들면 그 단계는 영영 복습되지 않는다
- 건너뛰기는 `review.py skip` 으로만 하고 **횟수가 `skip_log` 에 남는다**

**Why:** 단계를 통과했다는 건 그날 이해했다는 뜻이지 한 달 뒤에도 안다는 뜻이 아니다.
그리고 면접은 마지막 커밋 몇 달 뒤에 온다. §5-T 를 훅으로 막은 것과 같은 이유로 이것도 훅으로 막는다 —
md 로만 적힌 규율은 지켜지지 않는다.

**How to apply:** 세션 시작 배너에 「게이트 blocked」가 뜨면 `review` 스킬을 먼저 돈다.
⛔ `review_session.json` 을 손으로 고쳐 여는 것은 측정 조작이다. 그럴 거면 `skip` 으로 정직하게 연다.
관련: [[no-optimal-review-interval]] · [[learner-writes-code]] · [[rag-ontology-lab-project]]
