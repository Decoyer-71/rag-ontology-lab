# SETUP — 새 PC 에서 이어받기

⚠⚠ **클론만으로는 안 돕니다.** 커밋으로 따라오지 않는 것이 다섯 있고, 그중 둘(메모리 정션 · git 훅)은 **명령 한 줄**이면 됩니다.

이 저장소는 **PC 두 대(집 데스크탑 · 노트북)를 오가며** 작업하는 것을 전제로 만들어졌습니다(사용자 요구, 2026-09-10).
PC 마다 다른 값(저장소 루트 · 디스크 · 버전)은 `CLAUDE.md` §2 의 **PC 별 열**에 있습니다.

---

## 0. 무엇이 안 따라오는가

| 대상 | 왜 커밋 안 하나 | 어떻게 복구 |
|---|---|---|
| `.venv/` | 수백 MB, PC 마다 경로가 다르다 | §2 — `uv` 로 재생성 |
| Claude 메모리 폴더 (저장소 밖) | Claude 가 읽는 곳은 저장소 밖이다 | §5 — `link_memory.ps1` **한 번** (정션으로 저장소에 잇는다) |
| git 훅 켜기 (`core.hooksPath`) | git 설정은 커밋으로 안 따라온다 | §5-2 — **한 줄** |
| `data/external/` | ⚠⚠ **KorQuAD 는 CC BY-ND — 재배포 금지** | §4 — 직접 다운로드 |
| `outputs/cache/`·`models/` | 재생성 가능 / 너무 크다 | 필요할 때 다시 만든다 |

**코퍼스는 커밋돼 있습니다.** `data/synthetic/` 은 그대로 따라옵니다.

---

## 1. 클론

```bash
git clone https://github.com/Decoyer-71/rag-ontology-lab.git
cd rag-ontology-lab
```

⚠ 경로에 **공백을 넣지 마십시오.** 짧고 공백 없는 곳에 둡니다 — 데스크탑은 `D:\projects\rag-ontology-lab`,
노트북은 `C:\projects\rag-ontology-lab`. PC 마다 달라도 됩니다. 훅은 저장소 기준 상대경로로 돕니다.

---

## 2. 가상환경

이 프로젝트는 `uv` 로 파이썬을 관리합니다.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
```

### ⚠ `uv` 가 PATH 에 없을 때 (두 PC 모두 이 상태)

winget 으로 설치하면 PATH 에 안 잡힙니다. **전체 경로로** 부릅니다:

```
%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe
```

`uv` 자체가 없으면:

```powershell
winget install astral-sh.uv
```

### ⚠⚠ 시스템 `python` 을 쓰지 마십시오

Windows 의 `python` 은 **Microsoft Store 스텁**인 경우가 많아 부르면 그냥 죽습니다.
**항상 `.venv/Scripts/python.exe` 전체 경로**를 씁니다.

```bash
.venv/Scripts/python.exe --version   # Python 3.12.x 가 나와야 합니다 (패치 버전은 PC 마다 다를 수 있습니다)
```

---

## 3. 동작 확인

```bash
# 코퍼스가 제대로 따라왔는지
.venv/Scripts/python.exe -m labkit.corpus     # ⚠ src/ 가 경로에 있어야 합니다
# 또는
.venv/Scripts/python.exe -c "import sys;sys.path.insert(0,'src');from labkit.corpus import corpus_summary;print(corpus_summary())"

# 테스트 — ⚠ 미구현 단계가 실패하는 것이 정상입니다
.venv/Scripts/python.exe -m pytest tests/ -q
```

**기대 결과**(2026-09-10 환경 구축 시점 기준):

```
70 failed, 8 passed
```

- 통과 8건 = Stage 0(채점표 규격). 코퍼스·로더·설정이 정상이라는 뜻입니다
- 실패 70건 = 아직 사용자가 구현하지 않은 Stage 1~5. **정상입니다**

⚠ Stage 0 가 실패하면 코퍼스가 깨진 것입니다:

```bash
.venv/Scripts/python.exe data/make_corpus.py
```

---

## 4. 외부 데이터 (Stage 10 에서 필요)

```bash
.venv/Scripts/python.exe data/fetch_korquad.py
```

⚠⚠ **CC BY-ND 2.0 KR — 재배포 금지.**
`.gitignore` 의 `data/external/` 줄을 **지우지 마십시오.** 커밋하면 라이선스 위반입니다.

Stage 9 이전에는 필요 없습니다.

---

## 5. ⚠⚠ 메모리 — 정션으로 저장소에 잇습니다

Claude 가 실제로 읽고 쓰는 메모리는 저장소 밖에 있습니다:

```
%USERPROFILE%\.claude\projects\<세션을 연 경로를 인코딩한 폴더>\memory\
```

이 폴더를 저장소 `.claude/memory/` 를 가리키는 **디렉터리 정션**으로 바꾸면, 그다음부터 메모리도 **git 으로 따라옵니다.**
관리자 권한은 필요 없습니다.

```powershell
# ① 이 프로젝트 폴더에서 Claude Code 세션을 한 번 엽니다
# ② 저장소 루트에서
.claude\hooks\link_memory.ps1
#    → [memory] ✅ 연결했습니다 — 메모리 폴더가 이제 저장소 .claude\memory 를 봅니다
```

- 폴더 이름은 경로에서 영숫자가 아닌 글자를 `-` 로 바꾼 것입니다
  (`C:\projects\rag-ontology-lab` → `C--projects-rag-ontology-lab`). 스크립트가 계산합니다
- 그 폴더에 이미 파일이 있으면 저장소에 없는 것만 옮기고, **내용이 다른 파일이 있으면 멈춥니다** —
  어느 쪽이 맞는지는 사람이 정합니다. 옛 폴더는 지우지 않고 `memory.bak-<시각>` 으로 남깁니다
- 확인만: `.claude\hooks\link_memory.ps1 -Check`. `preflight` 도 매 세션 봅니다

안 하면 그 PC 의 세션은 「사용자가 코드를 쓴다」·「기준선과 나란히 측정한다」 같은
**이 프로젝트의 규율 기억 없이** 시작합니다. (2026-09-11 노트북에서 실제로 메모리 0개로 돌고 있었습니다)

⚠⚠ **대가 — 메모리가 공개 저장소에 커밋됩니다.** 메모리에 개인정보를 적지 마십시오. 커밋 전에 개인정보 관문(§5-2)이 한 번 더 봅니다.

⚠ `CLAUDE.md` 와 `.claude/` 의 훅·스킬·에이전트는 **저장소에 있으므로 자동으로 따라옵니다.**

### ⚠ 5-1. git 신원 — PC 마다

신원 설정 위치는 PC 마다 다릅니다(`CLAUDE.md` §2 — 한 PC 는 전역, 다른 PC 는 이 저장소 local).
없으면 `fatal: unable to auto-detect email address` 로 **커밋이 아예 실패합니다.** `preflight` 가 비어 있으면 알립니다.

```powershell
git config --local user.name  "<커밋 저자명>"
git config --local user.email "<이미 쓰고 있는 커밋 이메일>"
```

- 두 PC 가 **같은 이메일**을 씁니다. 값은 기존 커밋에서 확인합니다: `git log -1 --format="%an <%ae>"`
- 커밋 이메일은 커밋에 박혀 공개 이력에 남습니다. 이 저장소는 **사용자 결정으로 그대로 공개합니다**(2026-09-11) —
  개인정보 관문도 내 커밋 이메일은 막지 않습니다. 막는 것은 계좌·카드·전화·주민번호·비밀번호·키 같은 값입니다
- ⚠ GitHub 의 「Block command line pushes that expose my email」 설정은 **켜지 마십시오** — 켜면 이 이메일로 한 푸시가 전부 거부됩니다

### ⭐ 5-2. 개인정보 관문 + 자동 푸시 — PC 마다 한 번

```powershell
git config core.hooksPath .githooks
```

- 커밋 전·푸시 전에 개인정보·비밀값을 검사하고, 통과한 커밋은 **곧바로 원격에 올립니다** (`CLAUDE.md` §15-5)
- ⚠ 그래서 **커밋 = 공개**입니다. 되돌릴 틈이 없으니 커밋 전에 한 번 봅니다
- 잠시 끄기: `git config lab.autopush false` — 검사는 계속됩니다
- PC 고유 금지어(실명·전화번호 등)는 `.git/info/privacy-denylist` 에 한 줄씩 — 커밋되지 않습니다
- 오탐이면 그 문자열을 `.githooks/privacy-allow.txt` 에 — 커밋되므로 무엇을 풀었는지 리뷰에 보입니다
- 전체 감사: `.venv/Scripts/python.exe .githooks/privacy_scan.py tree` (`--all` 이면 아직 커밋 안 한 새 파일까지)
- ⛔ `--no-verify` 우회는 **사용자만** 판단합니다

---

## 6. 첫 세션에서 확인할 것

세션을 시작하면 훅이 자동으로 진단합니다.

### `preflight` — 환경 자가진단

venv · 의존성 · 훅 · `progress.json` · 코퍼스 · git 원격 · **메모리 정션 · 개인정보 관문 · 커밋 신원**을 확인합니다.
**붉은 줄(⛔)이 있으면 고치기 전에 코드를 돌리지 마십시오.** 노란 줄(⚠)은 두 PC 운영의 구멍입니다 — §5 에서 한 줄씩 고칩니다.

### `selftest -Quick` — ⚠⚠ 대필 차단 훅이 실제로 도는지

```
[selftest] guard_handson 5/5 통과
```

이렇게 나와야 합니다. 실패하면 **§5-T 방어선이 죽은 상태**입니다 —
그 상태에서는 Claude 가 `src/raglab/` 을 대신 채워도 아무도 막지 않습니다.
**학습을 진행하기 전에 고칩니다.**

전체 시험 (약 1분 — 임시 git 저장소를 만들어 개인정보 관문·자동 푸시·자동 받기·떠나기 전 점검까지 실제로 돌립니다):

```powershell
.claude\hooks\selftest.ps1
```

기대: **`통과` 앞뒤 숫자가 같을 것** — 2026-09-11 기준 `[selftest] 54/54 통과`.
⚠ 케이스가 늘면 숫자도 늘어납니다. **외운 숫자와 비교하지 말고 「N/N 인가」를 보십시오.**
하나라도 어긋나면 방어선에 구멍이 있는 것이고, 그 상태로 학습을 진행하면 안 됩니다.

### ⚠ 훅이 한글을 깨뜨린다면

`.ps1` 파일이 **UTF-8 BOM** 으로 저장돼 있어야 합니다.
Windows PowerShell 5.1 은 BOM 없는 UTF-8 을 cp949 로 읽습니다.
차단 사유가 깨져 나가면 Claude 가 왜 막혔는지 못 읽어 **훅이 반쯤 무력화됩니다.**

```bash
.venv/Scripts/python.exe -c "print(open(r'.claude/hooks/guard_handson.ps1','rb').read(3))"
# b'\xef\xbb\xbf' 가 나와야 합니다
```

---

## 7. 진도 확인

```bash
cat .claude/state/progress.json
```

`session_banner` 훅이 세션 시작 때 자동으로 보여 줍니다.

✅ `assumptions_unconfirmed` 는 **2026-09-10 에 `false` 가 됐습니다** — `CLAUDE.md` §0-2 의
세 가지가 확정됐고 `decisions` 키에 들어 있습니다.

⚠ 이 값이 다시 `true` 로 보이면 진도 파일이 옛 판이라는 뜻입니다. **먼저 `git pull` 하십시오.**

---

## 8. 두 PC 를 오갈 때

```bash
# 시작 — 세션을 열면 훅이 알아서 받습니다 (내 쪽 새 커밋이 없고 미커밋 변경이 없을 때만)
# 끝 — 커밋하면 자동으로 올라갑니다 (§5-2 를 켠 PC)
git add -A
git commit -m "Stage N: <능력 목표 한 줄>"
```

⚠ 관문을 **안 켠** PC 라면 예전처럼 `git pull --rebase`(시작) · `git push`(끝)를 손으로 합니다.

### ⭐ 잊어도 훅이 잡아 줍니다

- **받는 쪽** — `session_start` 훅이 원격을 확인하고, 안전하면 fast-forward 로 받은 **다음에** 복습 계획을 세웁니다.
  못 받았으면 `guard_sync` 가 새 단계를 여는 것을 막습니다 (`CLAUDE.md` §15-3)
- **떠나는 쪽** — Claude 응답이 끝날 때마다 `[떠나기 전 점검]` 줄이 미커밋·안 올라간 커밋을 알립니다 (§15-6).
  ⚠ 받는 쪽은 원격만 보므로 **다른 PC 에 두고 온 작업을 못 봅니다** — 그래서 떠나는 쪽에서 알립니다

| 상태 | 게이트 |
|---|---|
| 원격과 같음 | 통과 |
| 푸시 안 됨(ahead) | ⚠ 경고만 — 자동 푸시가 실패한 것입니다. 원인을 보고 `git push` |
| 원격이 앞섬(behind) | ⭐ 깨끗하면 **자동으로 받습니다.** 미커밋 변경이 있으면 ⛔ 차단 — 커밋한 뒤 `git pull --rebase` |
| 갈라짐(diverged) | ⛔ **차단.** `git pull --rebase` (미커밋 변경이 있으면 먼저 커밋) |

⚠ 복습·힌트·기록은 막히지 않습니다. 막는 것은 새 단계를 여는 행위뿐입니다.

### ⚠⚠ 충돌하면 — 파일마다 규칙이 다릅니다

| 파일 | 규칙 |
|---|---|
| `.claude/state/progress.json` | 더 진행된 쪽. `completed_stages` 는 **합집합** |
| `.claude/state/review.json` | ⚠⚠ **합칠 수 없습니다.** 더 최근에 복습한 쪽을 택하고, 애매하면 그 카드만 **만기로 되돌립니다** — 틀리게 합치느니 한 번 더 인출하는 편이 쌉니다 |
| `outputs/metrics/review_log.json` | `entries` 는 **양쪽을 다 남깁니다.** 인출 기록을 지우면 복습 주기를 데이터로 고칠 근거가 사라집니다 |
| `outputs/metrics/stageNN.json` | ⚠ 임의로 합치지 말고 **다시 측정**하십시오(§4 — 파생값을 측정값으로 두지 않는다) |
| `docs/PROGRESS.md` | 양쪽을 다 남깁니다. **막힌 지점이 §13-3 의 재료입니다** |

⚠ `*_session.json`(복습·동기화·떠나기 전 알림 판정)은 커밋되지 않습니다. 세션마다 다시 계산되므로 신경 쓸 필요가 없습니다.

---

## 9. 문제가 생기면

| 증상 | 원인 | 조치 |
|---|---|---|
| `python` 이 아무것도 안 하고 끝남 | MS Store 스텁 | `.venv/Scripts/python.exe` 전체 경로 |
| `uv: command not found` | PATH 에 없음 | §2 의 전체 경로 |
| `ModuleNotFoundError: labkit` | `src/` 가 경로에 없음 | pytest 는 `conftest.py` 가 처리. 직접 실행 시 `sys.path` 추가 |
| `UnicodeEncodeError` (파이썬) | stdout 이 cp949 | 스크립트 안에서 `sys.stdout.reconfigure(encoding="utf-8")` |
| 훅 메시지가 깨져 나옴 | `.ps1` BOM 없음 | §6 참고 |
| Stage 0 테스트 실패 | 코퍼스 손상 | `data/make_corpus.py` 재실행 |
| `guard_spoiler` 가 모든 걸 막음 | `progress.json` 없음 | 저장소에서 복구 |
| `guard_sync` 가 계속 막음 | 원격이 앞서 있는데 미커밋 변경이 있거나, 이력이 갈라짐 | 커밋 → `git pull --rebase` → `.claude\hooks\session_start.ps1` 재실행 (판정과 복습 계획을 다시 세웁니다) |
| `guard_review` 가 계속 막음 | 밀린 복습 카드 | `review` 스킬로 도십시오. 정말 못 하면 `review.py skip` (기록 남음) |
| `[privacy] ⛔ … 커밋을 막았습니다` | 계좌·카드·전화·주민번호·비밀번호·키, 남의 이메일 | 값을 지우거나 자리표시자로 · 오탐은 `privacy-allow.txt` |
| `[privacy] ⛔ .venv 파이썬을 못 찾아…` | venv 없음 — 관문은 fail-closed | §2 로 venv 를 만듭니다 |
| `[auto-push] ⚠ 올리지 못했습니다` | 오프라인 · 개인정보 관문 · 원격이 앞섬 | 원인을 해결한 뒤 `git push` |
| `[memory] ⛔ 연결돼 있지 않습니다` | 이 PC 에서 정션을 안 만듦 | `.claude\hooks\link_memory.ps1` |
| 세션 시작이 몇 초 걸림 | `session_start` 의 `git fetch` · `selftest -Quick` | 정상입니다. 오프라인이면 fetch 가 즉시 실패하고 게이트를 엽니다 |
