---
name: venv-full-path
description: 파이썬은 .venv 전체 경로로 부른다 — 시스템 python 은 MS Store 스텁이다
metadata: 
  node_type: memory
  type: project
  originSessionId: 1ba4b8fe-1a57-4687-bbeb-30c37efd9e72
  modified: 2026-09-10T12:42:32.177Z
---

이 PC 에서 파이썬은 반드시 **`.venv/Scripts/python.exe`** 로 부른다. `uv` 도 PATH 에 없어 전체 경로가 필요하다:
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe`

⚠ **`rag-ontology-lab` 의 작업 루트는 `D:\projects\rag-ontology-lab` 이다.** (2026-09-10 재실측.
옛 판은 `C:\projects\...` 이고 「D 드라이브 없음」이었는데 둘 다 틀렸다 — 프로젝트가 D 로 옮겨졌다.)

**Why:** 시스템 `python` 은 **Microsoft Store 스텁**이라 부르면 죽는다. 그 venv 는 Python **3.12.13** 이고
설치된 것은 numpy 2.5.3 · pyyaml 6.0.3 · pytest 9.1.1 **셋뿐**이다 — torch·sklearn·pandas·matplotlib 은 **없다**.

**How to apply:** 있다고 가정하고 코드를 쓰지 말고, 필요하면
`uv pip install --python .venv/Scripts/python.exe <패키지>` 로 조달한다.
⚠ 디스크는 D 여유 324GB · C 여유 66GB 라 **2~3GB 조달은 더 이상 용량 제약이 아니다.**
다만 조달 자체는 여전히 사용자 확인 사항이다. 관련: [[windows-encoding-traps]]
