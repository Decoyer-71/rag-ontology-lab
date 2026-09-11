---
name: git-identity-yoon71
description: 커밋 신원은 PC 마다 설정 위치가 다르다 — 커밋 이메일 공개는 사용자가 허용했다 (noreply 로 바꾸자고 다시 제안하지 않는다)
metadata:
  type: project
---

커밋 저자명은 `YOON71` 이다. **신원 설정 위치는 PC 마다 다르다** — 한 PC 는 전역(global), 다른 PC 는 이 저장소 local 에만 있다(`CLAUDE.md` §2).
두 PC 는 **같은 커밋 이메일**을 쓴다.

⭐ **사용자 결정(2026-09-11): 커밋 이메일 공개는 허용한다.** 이미 공개 이력 전부에 있고, 계좌·휴대전화·비밀번호가 노출되는 것과는
다르다고 판단했다. **noreply 로 바꾸자고 다시 제안하지 않는다.** `.githooks/` 개인정보 관문도 내 커밋 이메일은 막지 않는다 —
관문이 막는 것은 계좌·카드·전화·주민번호·비밀번호·키·남의 이메일이다.

⚠ 그래도 **실제 이메일 값을 문서·메모리에 옮겨 적을 이유는 없다.**

**Why:** 신원이 없으면 `fatal: unable to auto-detect email address` 로 커밋이 실패한다.
공개 저장소의 커밋 저자는 남에게 보이므로 **임의로 지어내면 안 된다** — 사용자가 정한 값을 따른다.

**How to apply:** 새 PC 는 `docs/SETUP.md` §5-1. `gh` 는 `C:\Program Files\GitHub CLI\gh.exe` 로 부른다(PATH 에 없을 수 있다).
⚠ 인증·계정·토큰 입력은 **사용자만** 한다. 관련: [[rag-ontology-lab-project]] · [[memory-is-public]]
