# SETUP — 새 PC 에서 이어받기

⚠⚠ **클론만으로는 안 돕니다.** 커밋되지 않은 것이 넷 있습니다.

이 저장소는 **여러 PC 를 오가며** 작업하는 것을 전제로 만들어졌습니다(사용자 요구, 2026-09-10).

---

## 0. 무엇이 안 따라오는가

| 대상 | 왜 커밋 안 하나 | 어떻게 복구 |
|---|---|---|
| `.venv/` | 수백 MB, PC 마다 경로가 다르다 | §2 — `uv` 로 재생성 |
| `data/external/` | ⚠⚠ **KorQuAD 는 CC BY-ND — 재배포 금지** | §4 — 직접 다운로드 |
| `.claude/memory/` 의 **실제 위치** | Claude 가 읽는 곳은 저장소 밖이다 | §5 — ⚠ **수동 복사 필요** |
| `outputs/cache/`·`models/` | 재생성 가능 / 너무 크다 | 필요할 때 다시 만든다 |

**코퍼스는 커밋돼 있습니다.** `data/synthetic/` 은 그대로 따라옵니다.

---

## 1. 클론

```bash
git clone https://github.com/Decoyer-71/rag-ontology-lab.git
cd rag-ontology-lab
```

⚠ 경로에 **공백을 넣지 마십시오.** `D:\projects\rag-ontology-lab` 처럼 짧고 공백 없는 곳에 둡니다.

---

## 2. 가상환경

이 프로젝트는 `uv` 로 파이썬을 관리합니다.

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
```

### ⚠ `uv` 가 PATH 에 없을 때 (이 PC 의 상태)

winget 으로 설치하면 PATH 에 안 잡힙니다. **전체 경로로** 부릅니다:

```
C:\Users\<사용자>\AppData\Local\Microsoft\WinGet\Packages\astral-sh.uv_Microsoft.Winget.Source_8wekyb3d8bbwe\uv.exe
```

`uv` 자체가 없으면:

```powershell
winget install astral-sh.uv
```

### ⚠⚠ 시스템 `python` 을 쓰지 마십시오

Windows 의 `python` 은 **Microsoft Store 스텁**인 경우가 많아 부르면 그냥 죽습니다.
**항상 `.venv/Scripts/python.exe` 전체 경로**를 씁니다.

```bash
.venv/Scripts/python.exe --version   # Python 3.12.x 가 나와야 합니다
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

## 5. ⚠⚠ 메모리 — 이게 가장 자주 빠집니다

`.claude/memory/` 는 **이동용 사본**입니다. Claude 가 실제로 읽는 곳은 저장소 밖입니다:

```
%USERPROFILE%\.claude\projects\<세션 작업 디렉터리를 인코딩한 폴더>\memory\
```

⚠ **폴더 이름은 세션을 어느 디렉터리에서 열었는지에 따라 달라집니다.**
`C:\` 에서 열면 `C--`, `D:\projects\rag-ontology-lab` 에서 열면 그 경로를 인코딩한 이름이 됩니다.
그래서 **경로를 외우지 말고 찾으십시오.**

```powershell
# ① 이 프로젝트 폴더에서 Claude Code 세션을 한 번 엽니다 (폴더가 그때 생깁니다)
# ② 최근 수정 순으로 후보를 확인
Get-ChildItem "$env:USERPROFILE\.claude\projects" | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name

# ③ 그 폴더 아래에 memory\ 를 만들고 저장소 사본을 복사
$dest = "$env:USERPROFILE\.claude\projects\<②에서 확인한 폴더>\memory"
New-Item -ItemType Directory -Force $dest | Out-Null
Copy-Item -Recurse -Force .claude\memory\* $dest
```

안 하면 그 PC 의 세션은 「사용자가 코드를 쓴다」·「기준선과 나란히 측정한다」 같은
**이 프로젝트의 규율 기억 없이** 시작합니다.

⚠ `CLAUDE.md` 와 `.claude/` 의 훅·스킬·에이전트는 **저장소에 있으므로 자동으로 따라옵니다.**
수동이 필요한 것은 `memory/` 하나뿐입니다.

### ⚠⚠ 5-1. git 신원도 PC 마다 지정해야 합니다

이 프로젝트를 만든 PC 에는 이제 git 전역 신원이 있습니다 (2026-09-10 재실측). ⚠ **새 PC 에는 없을 수 있습니다.** 없으면
`fatal: unable to auto-detect email address` 로 **커밋이 아예 실패합니다.**

```powershell
git config --local user.name  "<커밋 저자명>"
git config --local user.email "<GitHub 계정에 등록된 이메일>"
```

⚠ **GitHub 계정에 등록된 이메일**을 쓰십시오. 다른 이메일로 커밋하면
프로필 기여도(contribution graph)에 안 잡힙니다 — 포트폴리오에서는 이게 눈에 띕니다.

⚠ 값을 모르면 이 저장소의 기존 커밋에서 확인할 수 있습니다:

```bash
git log -1 --format="%an <%ae>"
```

---

## 6. 첫 세션에서 확인할 것

세션을 시작하면 훅이 자동으로 진단합니다.

### `preflight` — 환경 자가진단

venv · 의존성 · 훅 4종 · `progress.json` · 코퍼스 · git 원격을 확인합니다.
**붉은 줄(⛔)이 있으면 고치기 전에 코드를 돌리지 마십시오.**

### `selftest -Quick` — ⚠⚠ 대필 차단 훅이 실제로 도는지

```
[selftest] guard_handson 5/5 통과
```

이렇게 나와야 합니다. 실패하면 **§5-T 방어선이 죽은 상태**입니다 —
그 상태에서는 Claude 가 `src/raglab/` 을 대신 채워도 아무도 막지 않습니다.
**학습을 진행하기 전에 고칩니다.**

전체 시험:

```powershell
.claude\hooks\selftest.ps1
```

기대: `[selftest] 10/10 통과`

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
# 시작 전 — 항상
git pull --rebase

# 끝 — 단계별로 쪼개서
git add -A
git commit -m "Stage N: <능력 목표 한 줄>"
git push
```

⚠ **`progress.json` 이 충돌하기 쉽습니다.** 두 PC 에서 같은 단계를 진행하면 그렇습니다.
충돌하면 **더 진행된 쪽**을 택하고 `completed_stages` 는 **합집합**으로 만듭니다.

⚠ `outputs/metrics/*.json` 도 충돌할 수 있습니다. 이건 **측정값**이므로
임의로 합치지 말고 **다시 측정**하십시오(§4 — 파생값을 측정값으로 두지 않는다).

---

## 9. 문제가 생기면

| 증상 | 원인 | 조치 |
|---|---|---|
| `python` 이 아무것도 안 하고 끝남 | MS Store 스텁 | `.venv/Scripts/python.exe` 전체 경로 |
| `uv: command not found` | PATH 에 없음 | §2 의 전체 경로 |
| `ModuleNotFoundError: labkit` | `src/` 가 경로에 없음 | pytest 는 `conftest.py` 가 처리. 직접 실행 시 `sys.path` 추가 |
| `UnicodeEncodeError` (파이썬) | stdout 이 cp949 | `PYTHONIOENCODING=utf-8` 을 앞에 붙인다 |
| 훅 메시지가 깨져 나옴 | `.ps1` BOM 없음 | §6 참고 |
| Stage 0 테스트 실패 | 코퍼스 손상 | `data/make_corpus.py` 재실행 |
| `guard_spoiler` 가 모든 걸 막음 | `progress.json` 없음 | 저장소에서 복구 |
