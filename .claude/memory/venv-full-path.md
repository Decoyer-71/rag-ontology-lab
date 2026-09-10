---
name: venv-full-path
description: 파이썬은 .venv 전체 경로로 부른다 — 시스템 python 은 MS Store 스텁이다
metadata:
  type: project
---

이 PC 에서 파이썬은 반드시 **`.venv/Scripts/python.exe`** 로 부른다. `uv` 도 PATH 에 없어 전체 경로가 필요하다:
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe`

**Why:** 시스템 `python` 은 **Microsoft Store 스텁**이라 부르면 죽는다. 2026-09-10 실측. `rag-ontology-lab` 의 venv 는 Python 3.12.14 이고 설치된 것은 numpy 2.5.3 · pyyaml 6.0.3 · pytest 9.1.1 **셋뿐**이다 — torch·sklearn·pandas·matplotlib 은 **없다**.

**How to apply:** 있다고 가정하고 코드를 쓰지 말고, 필요하면 `uv pip install --python .venv/Scripts/python.exe <패키지>` 로 조달한다. ⚠ 2GB 넘는 조달(torch 등)은 사용자 확인을 받는다 — C 여유 19GB. 관련: [[windows-encoding-traps]]
