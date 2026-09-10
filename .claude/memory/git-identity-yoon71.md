---
name: git-identity-yoon71
description: 이 PC 에는 git 전역 신원 설정이 없어 저장소마다 user.name/user.email 을 지정해야 한다
metadata:
  type: project
---

이 PC 에는 **git 전역 신원 설정이 없다**(`git config --global user.name/email` 둘 다 비어 있음).
새 저장소를 만들 때마다 저장소 로컬로 지정해야 커밋이 된다.

```
git config --local user.name  "<사용자명>"
git config --local user.email "<사용자 이메일>"
```

⚠ **실제 값은 이 파일에 적지 않는다.** 이 저장소는 공개이고, 공개 저장소의 이메일은 스팸 표적이 된다.
실제 값은 로컬 메모리(`%USERPROFILE%\.claude\projects\...\memory\`)에만 있고,
기존 저장소 `C:\projects\oil_DA` 의 `git config --local` 에서도 확인할 수 있다.

**Why:** 안 하면 `fatal: unable to auto-detect email address` 로 커밋이 아예 실패한다.
2026-09-10 에 실제로 막혔다. 그리고 공개 저장소의 커밋 저자는 남에게 보이므로
**임의로 지어내면 안 된다** — 사용자가 이미 쓰는 값을 따른다.

**How to apply:** `gh` CLI 는 2026-09-10 에 설치했다(2.100.0, `C:\Program Files\GitHub CLI\gh.exe`).
⚠ 인증·계정·토큰 입력은 **사용자만** 한다. 관련: [[rag-ontology-lab-project]]
