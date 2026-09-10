---
name: git-identity-yoon71
description: 이 사용자의 git 커밋 신원은 YOON71 <cvcv6226@gmail.com> 이고 전역 설정이 없어 저장소마다 지정해야 한다
metadata:
  type: project
---

이 PC 에는 **git 전역 신원 설정이 없다**(`git config --global user.name/email` 둘 다 비어 있음). 새 저장소를 만들 때마다 저장소 로컬로 지정해야 커밋이 된다.

기존 저장소(`C:\projects\oil_DA`)가 쓰는 값과 맞춘다:

```
git config --local user.name  "YOON71"
git config --local user.email "cvcv6226@gmail.com"
```

**Why:** 안 하면 `fatal: unable to auto-detect email address` 로 커밋이 아예 실패한다. 2026-09-10 에 실제로 막혔다. 그리고 공개 저장소의 커밋 저자는 남에게 보이므로 **임의로 지어내면 안 된다** — 사용자가 이미 쓰는 값을 따른다.

**How to apply:** `gh` CLI 는 이 PC 에 **없다.** GitHub 등재는 웹에서 저장소를 만들고 `git remote add` 하는 경로다. ⚠ 인증·계정·토큰 입력은 **사용자만** 한다. 관련: [[rag-ontology-lab-project]]
