---
name: venv-full-path
description: 파이썬은 .venv 상대경로로 부른다 — 시스템 python 은 MS Store 스텁이고, 저장소 루트는 PC 마다 다르다
metadata:
  type: project
---

파이썬은 반드시 **`.venv/Scripts/python.exe`**(저장소 루트 기준 상대경로)로 부른다. `uv` 도 PATH 에 없어 전체 경로가 필요하다:
`%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe`

⚠⚠ **저장소 루트·파이썬 패치 버전·디스크 여유는 PC 마다 다르다.** 값은 `CLAUDE.md` §2 의 **PC 별 열**에 있고,
여기엔 적지 않는다 — 한 PC 값을 공용 사실로 적었다가 다른 PC 에서 「틀렸다」로 덮어쓰는 사고가
2026-09-10 에 실제로 있었다(§6 지뢰 11).

**Why:** 시스템 `python` 은 **Microsoft Store 스텁**이라 부르면 죽는다. venv 에 설치된 것은
numpy 2.5.3 · pyyaml 6.0.3 · pytest 9.1.1 **셋뿐**이다(두 PC 공통, `requirements.txt` 고정) — torch·sklearn·pandas·matplotlib 은 **없다**.

**How to apply:** 있다고 가정하고 코드를 쓰지 말고, 필요하면
`uv pip install --python .venv/Scripts/python.exe <패키지>` 로 조달한다. 조달은 사용자 확인 사항이고,
⚠ 디스크 여유가 PC 마다 크게 다르므로(§2) **어느 PC 에서 할지도 같이 묻는다.** 관련: [[windows-encoding-traps]] · [[two-pc-sync-gate]]
