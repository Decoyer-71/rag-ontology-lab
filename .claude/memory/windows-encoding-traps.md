---
name: windows-encoding-traps
description: 이 PC 의 한글 인코딩 지뢰 셋 — PowerShell BOM, 파이썬 stdout, Bash heredoc
metadata:
  type: project
---

Windows 에서 한글을 다룰 때 2026-09-10 에 **실제로 밟은** 것 셋:

1. **`.ps1` 은 UTF-8 BOM 으로 저장한다.** Windows PowerShell 5.1 은 BOM 없는 UTF-8 을 cp949 로 읽어 한글이 깨진다. 훅의 차단 사유가 깨지면 Claude 가 왜 막혔는지 못 읽어 **훅이 반쯤 무력화된다.** 훅 안에서 `[Console]::OutputEncoding` 도 UTF-8 로 고정한다
2. **파이썬 stdout 이 cp949 다.** 한글·특수문자(`—` 등)를 출력하면 `UnicodeEncodeError`. `PYTHONIOENCODING=utf-8` 을 붙인다
3. **⚠⚠ 한글이 든 긴 문서를 Bash heredoc 으로 쓰지 마라.** `unexpected EOF` 로 깨졌다. **`Write` 도구를 쓴다**

**Why:** 셋 다 **조용히** 깨지거나 엉뚱한 곳에서 터진다. 특히 1번은 방어선이 죽은 줄 모르게 만든다.

**How to apply:** 파일을 읽고 쓸 때 `open(..., encoding="utf-8")` 을 명시한다 — Windows 기본은 cp949 다. 관련: [[venv-full-path]]
