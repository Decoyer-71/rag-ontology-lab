---
name: git-identity-yoon71
description: 이 PC 에는 git 전역 신원이 설정돼 있다 — 저장소마다 지정할 필요가 없다 (2026-09-10 재실측)
metadata: 
  node_type: memory
  type: project
  originSessionId: 1ba4b8fe-1a57-4687-bbeb-30c37efd9e72
  modified: 2026-09-10T12:42:21.464Z
---

이 PC 에는 **git 전역 신원이 설정돼 있다** (`git config --global user.name` / `user.email` 둘 다 값이 있음).
새 저장소에서 `git config --local` 을 따로 지정하지 않아도 커밋이 된다.

⚠ **옛 판 폐기** — 2026-09-10 이전에는 「전역 설정이 없어 저장소마다 지정해야 한다」고 적혀 있었다.
같은 날 재실측에서 전역 설정이 **있는 것**으로 확인됐다. 옛 지침은 더 이상 유효하지 않다.

⚠ **실제 값은 이 파일에 적지 않는다.** 이 저장소는 공개이고, 공개 저장소의 이메일은 스팸 표적이 된다.
필요하면 `git config --global user.email` 로 직접 확인한다.

**Why:** 신원이 없으면 `fatal: unable to auto-detect email address` 로 커밋이 아예 실패한다.
그리고 공개 저장소의 커밋 저자는 남에게 보이므로 **임의로 지어내면 안 된다** — 사용자가 이미 쓰는 값을 따른다.

**How to apply:** 새 PC 로 옮기면 전역 설정이 다시 없을 수 있으니 `docs/SETUP.md` 의 절차를 따른다.
`gh` CLI 는 설치돼 있다(2.100.0, `C:\Program Files\GitHub CLI\gh.exe`, PATH 에 없어 전체 경로로 부른다).
⚠ 인증·계정·토큰 입력은 **사용자만** 한다. 관련: [[rag-ontology-lab-project]]
