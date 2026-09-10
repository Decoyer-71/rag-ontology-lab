---
name: repo-publish
description: GitHub 원격 저장소를 연결하고 다른 PC에서 이어받을 수 있게 만드는 절차. gh CLI가 없는 환경 기준이며, 커밋 전 점검·푸시 확인·다른 PC 이관 체크리스트가 들어 있다. "깃허브에 올려줘", "원격 설정해줘", "다른 PC에서 작업할 수 있게 해줘", 또는 Stage 11에서 쓴다.
---

# GitHub 원격 연결과 다른 PC 이관

`../../CLAUDE.md` §2 · §13. **이 PC 에는 `gh` CLI 가 없다.** 웹에서 저장소를 만들고 수동으로 remote 를 거는 경로다.

## ⚠⚠ Claude 가 할 수 없는 것 — 먼저 명확히

| 항목 | 누가 |
|---|---|
| GitHub 계정 로그인·인증 | **사용자만.** Claude 는 자격증명을 입력하지 않는다 |
| 저장소 생성 (웹 UI) | **사용자만** |
| Personal Access Token 발급·입력 | **사용자만** |
| `git remote add` · 커밋 · 브랜치 | Claude 가 한다 |
| **`git push`** | ⚠⚠ **사용자 확인을 받고** 한다 — 외부로 내보내는 되돌리기 어려운 동작이다 |

⚠ 승인은 **한 번에 하나**다. 첫 푸시를 승인받았다고 이후 푸시까지 승인된 것이 아니다.

---

## A. 최초 원격 연결

### A-1. ⚠⚠ 커밋 전 점검 — 나가면 안 되는 것

푸시는 **되돌리기 어렵다.** 한 번 나간 것은 커밋 이력에 남는다. 푸시 전에 반드시 확인한다:

```bash
git status --short
git ls-files | head -60
```

**절대 나가면 안 되는 것:**

| 대상 | 이유 |
|---|---|
| `data/external/**` | ⚠⚠ **KorQuAD 는 CC BY-ND 2.0 KR — 재배포 금지.** 라이선스 위반이다(§6 지뢰 7) |
| `.venv/` | 수백 MB. 다른 PC 에서 어차피 못 쓴다 |
| `.env` · `*.key` · 토큰 | ⚠⚠ **API 키가 나가면 즉시 폐기·재발급이다** |
| `models/` · `*.safetensors` | Stage 9 이후. 수백 MB~GB |
| 개인 경로가 박힌 파일 | `C:\Users\<이름>\...` 이 문서에 들어 있으면 지운다 |

`.gitignore` 가 다 잡고 있지만 **믿지 말고 `git ls-files` 로 실제 추적 목록을 눈으로 본다.**

```bash
git ls-files | grep -E "external|\.venv|\.env|\.key|safetensors" || echo "OK — 금지 대상 없음"
```

### A-2. 사용자가 GitHub 에서 저장소를 만든다

사용자에게 안내할 것 (⚠ Claude 가 대신 하지 않는다):

1. github.com → New repository
2. 이름 제안: **`rag-ontology-lab`**
3. **공개 / 비공개** — 포트폴리오로 제출한다면 공개여야 링크를 낼 수 있다. ⚠ 다만 **아직 결과가 비어 있으므로** 학습이 어느 정도 진행된 뒤 공개로 바꾸는 것도 방법이다. **사용자에게 물어라**
4. ⚠⚠ **README·.gitignore·LICENSE 를 GitHub 쪽에서 만들지 마라** — 이미 로컬에 있다. 만들면 첫 푸시에서 이력이 갈라진다
5. 만들고 나온 URL 을 Claude 에게 알려준다

### A-3. remote 연결

```bash
git remote add origin https://github.com/<사용자>/rag-ontology-lab.git
git remote -v
```

⚠ 이미 origin 이 있으면 `git remote set-url origin <새 URL>`.

### A-4. 브랜치 이름 확인

```bash
git branch --show-current
```

`master` 면 `main` 으로 바꾼다(GitHub 기본값과 맞춘다):

```bash
git branch -M main
```

### A-5. ⚠⚠ 첫 푸시 — **사용자 확인을 받고**

확인 문구 예시:

> `<사용자>/rag-ontology-lab` 으로 커밋 N개를 푸시합니다. 공개 저장소이므로 내용이 인터넷에 공개됩니다. 진행할까요?

승인 후:

```bash
git push -u origin main
```

⚠ 인증을 물으면 **사용자가 직접 입력한다.** Claude 는 토큰·비밀번호를 입력하지 않는다.

---

## B. 다른 PC 에서 이어받기

⚠⚠ **이 저장소는 클론만으로는 안 돈다.** 커밋되지 않은 것이 넷 있다.

`docs/SETUP.md` 에 같은 내용이 있다. 여기선 순서만.

```bash
# 1. 클론
git clone https://github.com/<사용자>/rag-ontology-lab.git
cd rag-ontology-lab

# 2. venv — 커밋 안 됨. uv 로 다시 만든다
#    ⚠ uv 경로는 PC 마다 다르다. winget 설치 위치를 확인한다
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt

# 3. 코퍼스 — 커밋돼 있으므로 재생성 불필요. 확인만
.venv/Scripts/python.exe -m pytest tests/ -q   # 미구현 단계는 실패가 정상

# 4. 외부 데이터 — 커밋 안 됨 (ND 라이선스). Stage 10 에서 필요
.venv/Scripts/python.exe data/fetch_korquad.py
```

### ⚠⚠ 5. 메모리는 자동으로 안 따라온다

`.claude/memory/` 는 **이동용 사본**이다. Claude 가 실제로 읽는 곳은 저장소 밖이다:

```
%USERPROFILE%\.claude\projects\<프로젝트 해시>\memory\
```

새 PC 에서 **직접 복사해 넣어야** 한다. 안 하면 그 PC 의 세션은 이 프로젝트의 규율 기억 없이 시작한다.

### 6. 첫 세션에서 확인할 것

`preflight` 훅이 자동으로 진단한다. 붉은 줄이 있으면 **고치기 전에 코드를 돌리지 마라.**

- venv · 의존성 · 훅 4종 · `progress.json` · 코퍼스 · git 원격

그리고 `selftest.ps1` 이 **대필 차단 훅이 실제로 도는지** 시험한다.
⚠⚠ 여기서 실패가 나면 §5-T 방어선이 죽은 상태다. **학습을 진행하기 전에 고친다.**

---

## C. 평소 동기화 (PC 두 대를 오갈 때)

```bash
# 작업 시작 전 — 항상
git pull --rebase

# 작업 끝 — 단계별로 쪼개서
git add -A
git commit -m "Stage N: <능력 목표 한 줄>"
git push        # ⚠ 사용자 확인
```

⚠ **`progress.json` 이 충돌하기 쉽다.** 두 PC 에서 같은 단계를 진행하면 그렇다.
충돌하면 **더 진행된 쪽**을 택하고, `completed_stages` 는 **합집합**으로 만든다.

---

## D. Stage 11 — 포트폴리오로 내보낼 때 추가 점검

`docs/PORTFOLIO.md` 체크리스트를 따른다. 여기선 저장소 표면만.

- [ ] README 첫 화면에 **결과 표 + 아키텍처 그림**이 스크롤 없이 보이는가(§13-1)
- [ ] 결과 표의 빈칸이 **추정치로 메워지지 않았는가**(§13-5)
- [ ] 「배운 것」이 `docs/PROGRESS.md` 의 **막힌 지점**에서 나왔는가(§13-3)
- [ ] 「한계」 절이 있는가
- [ ] 기술 스택에 **실제로 안 쓴 것**이 적혀 있지 않은가 — 면접에서 물어본다
- [ ] 합성 데이터임이 README·리포트·DATA_CARD 세 곳에 표기됐는가(§3-S)
- [ ] 커밋 이력이 단계별로 쪼개져 있는가(§13-4)
- [ ] `LICENSE` 파일이 있는가
- [ ] ⚠ 저장소 About 에 한 줄 설명과 토픽(`rag`, `ontology`, `knowledge-graph`, `information-retrieval`)이 붙었는가 — 사용자가 웹에서 한다
