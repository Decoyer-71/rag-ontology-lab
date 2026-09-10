---
name: windows-encoding-traps
description: "이 PC 의 인코딩·이스케이프 지뢰 다섯 — ps1 BOM, 파이썬 stdout, Bash heredoc, sed 백슬래시, 환경변수 접두사"
metadata: 
  node_type: memory
  type: project
  originSessionId: 1ba4b8fe-1a57-4687-bbeb-30c37efd9e72
  modified: 2026-09-10T12:42:49.406Z
---

Windows 에서 한글·경로를 다룰 때 2026-09-10 에 **실제로 밟은** 것 다섯:

1. **`.ps1` 은 UTF-8 BOM 으로 저장한다.** Windows PowerShell 5.1 은 BOM 없는 UTF-8 을 cp949 로 읽어 한글이 깨진다. 훅의 차단 사유가 깨지면 Claude 가 왜 막혔는지 못 읽어 **훅이 반쯤 무력화된다.** 훅 안에서 `[Console]::OutputEncoding` 도 UTF-8 로 고정한다
2. **파이썬 stdout 이 cp949 다.** 한글·특수문자(`—`, `✅`)를 출력하면 `UnicodeEncodeError`. 스크립트 첫머리에서 `sys.stdout.reconfigure(encoding="utf-8")`. pytest 한글 테스트명도 같은 이유로 깨지는데 그건 `PYTHONIOENCODING=utf-8` 로 푼다
3. **⚠⚠ 한글이 든 긴 문서를 Bash heredoc 으로 쓰지 마라.** `unexpected EOF` 로 깨졌다. **`Write` 도구를 쓴다**
4. **⚠⚠ `sed` 로 윈도우 경로를 치환하지 마라.** 백슬래시가 이스케이프로 먹혀 `D:\projects\rag-ontology-lab` 이 `D:projectsag-ontology-lab` 이 됐다(`\r` 이 CR 로 해석됨). **백슬래시가 든 치환은 파이썬 스크립트로** 한다 — 3번과 같은 뿌리다
5. **⚠ `PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe ...` 처럼 환경변수를 앞에 붙이면 권한이 거부된다.** `.claude/settings.json` 의 허용 규칙 `Bash(.venv/Scripts/python.exe *)` 에 안 걸리기 때문이다. **인코딩은 스크립트 안에서 세우고, 명령은 허용 규칙 모양 그대로** 부른다

**Why:** 전부 **조용히** 깨지거나 엉뚱한 곳에서 터진다. 1번은 방어선이 죽은 줄 모르게 만들고, 4번은 파일을 망가뜨린 채 성공한 것처럼 보인다.

**How to apply:** 파일을 읽고 쓸 때 `open(..., encoding="utf-8")` 을 명시한다 — Windows 기본은 cp949 다. BOM 이 있는 파일은 읽을 때 `utf-8-sig`, 쓸 때도 `utf-8-sig` 로 왕복시킨다(안 그러면 BOM 이 두 번 붙는다). 관련: [[venv-full-path]]
