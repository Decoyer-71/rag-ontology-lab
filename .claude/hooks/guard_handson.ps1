# -*- coding: utf-8 -*-
<#
  PreToolUse 훅 — ⭐ **이 프로젝트의 제1 방어선.** (CLAUDE.md §5-T)

  Claude 가 `src/raglab/` 의 알고리즘 본체를 **대신 짜는 것**을 기계적으로 막는다.

  ⚠⚠ 왜 이 훅이 있는가
  ─────────────────────────────────────────────────────────────────────────────
  사용자 요구사항 원문:
      "단순 클로드가 코드를 짜주는게 아닌 사용자가 직접 코드를 작성하고
       작동 알고리즘을 이해하도록 구성"

  대필은 **진행이 빨라 보이기 때문에** 매력적이다. 그래서 규약만으로는 막히지 않는다.
  코드가 다 채워진 상태는 이 프로젝트에서 성공이 아니라 **아무것도 아닌 상태**일 수 있다.
  포트폴리오 관점에서는 더 무겁다 — 대필된 코드는 면접에서 한 질문에 드러난다 (§13).

  ⚠ 판정 기준 — 「TODO 를 채웠는가」를 본다
  ─────────────────────────────────────────────────────────────────────────────
  뼈대에는 함수마다 `raise NotImplementedError` 가 하나씩 들어 있다.
  **그 개수가 줄어들면 누군가 구현을 채운 것이다.** 이것이 가장 오탐이 적은 신호다.

    · Edit : old_string 에 NotImplementedError 가 있고 new_string 에 없다  → 차단
    · Write: 디스크의 기존 파일보다 NotImplementedError 가 줄었다          → 차단
    · 부수 : NotImplementedError 없이 로직 6줄 이상이 새로 들어온다        → 차단

  ⚠ 탈출구 — 사용자가 **명시적으로** 대필을 요청한 경우 (§5-T 예외)
  ─────────────────────────────────────────────────────────────────────────────
  `.claude/state/handson_override.json` 에 파일을 등재하면 통과한다.
  등재 자체가 기록이므로 나중에 "여기는 내가 안 짰다"를 추적할 수 있다.

      { "files": ["src/raglab/chunking.py"],
        "reason": "사용자가 2026-09-11 에 명시적으로 요청",
        "granted": "2026-09-11" }

  ⚠⚠ fail-open — 훅 자체의 오류로는 아무것도 막지 않는다.
     단, 그 경우 stderr 에 경고를 남긴다. 조용히 죽는 방어선을 만들지 않기 위해서다.
#>

$ErrorActionPreference = 'Stop'

# ⚠⚠ 출력 인코딩을 UTF-8 로 고정한다.
#   Windows PowerShell 5.1 기본값은 OEM 코드페이지(cp949)라,
#   차단 사유의 한글이 깨진 채 Claude 에게 전달된다 → 훅이 반쯤 무력화된다.
try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8NoBom
    $OutputEncoding = $utf8NoBom
} catch { }


# ── 임계값 ──────────────────────────────────────────────────────────────────
# 뼈대(시그니처+독스트링+TODO)는 로직 줄이 0~2 다. 6 이면 명백한 구현이다.
# ⚠ 넉넉히 잡는다 — 오탐으로 작업을 막는 것이 더 나쁘다 (_common.ps1 Count-LogicLines)
$LOGIC_LINE_LIMIT = 6

# ── 보호 대상 ───────────────────────────────────────────────────────────────
$PROTECTED = 'src/raglab/'

# ── 보호 대상 안이지만 예외인 파일 (배관이지 학습 대상이 아니다) ─────────────
$EXEMPT_LEAF = @('__init__.py')

function Pass { exit 0 }

function Deny([string]$Message) {
    [Console]::Error.Write($Message)
    exit 2
}

# ── 루트 찾기 (자체 폴백 포함) ───────────────────────────────────────────────
$startDir = $PSScriptRoot
if (-not $startDir) { try { $startDir = Split-Path -Parent $MyInvocation.MyCommand.Path } catch {} }

$root = $null
try {
    . (Join-Path $startDir '_common.ps1')
    $rr = Resolve-RepoRoot -StartDir $startDir -Markers @('.claude\hooks')
    $root = $rr.Root
} catch {
    # 폴백 — 훅은 <루트>\.claude\hooks 에 있으므로 두 단계 위.
    # ⚠ 확인 없이 두 단계 위를 루트로 삼으면 새 fail-open 을 만드는 것이다. marker 를 본다.
    try {
        $cand = Split-Path -Parent (Split-Path -Parent $startDir)
        if ($cand -and (Test-Path -LiteralPath (Join-Path $cand '.claude\hooks'))) { $root = $cand }
    } catch { }
}

# ── 입력 파싱 ───────────────────────────────────────────────────────────────
try {
    $raw = [Console]::In.ReadToEnd()
    if ($raw.Length -gt 0 -and $raw[0] -eq [char]0xFEFF) { $raw = $raw.Substring(1) }
    $payload = $raw | ConvertFrom-Json
} catch { Pass }

if (-not $payload) { Pass }

$tool = [string]$payload.tool_name
if (@('Write', 'Edit', 'NotebookEdit') -notcontains $tool) { Pass }

$ti = $payload.tool_input
if (-not $ti) { Pass }

$path = ''
try { $path = [string]$ti.file_path } catch { }
if (-not $path) { Pass }

$norm = $path.Replace('\', '/')
if ($norm -notmatch [regex]::Escape($PROTECTED)) { Pass }

$leaf = Split-Path $path -Leaf
if ($EXEMPT_LEAF -contains $leaf) { Pass }

# ── 탈출구: 사용자 승인 등재 확인 ────────────────────────────────────────────
if ($root) {
    $ovPath = Join-Path $root '.claude\state\handson_override.json'
    if (Test-Path -LiteralPath $ovPath) {
        try {
            $ov = Get-Content -LiteralPath $ovPath -Raw -Encoding UTF8 | ConvertFrom-Json
            foreach ($f in @($ov.files)) {
                if (-not $f) { continue }
                $fn = ([string]$f).Replace('\', '/')
                if ($norm.EndsWith($fn) -or $fn.EndsWith($norm)) { Pass }
            }
        } catch { }
    }
}

# ── 판정용 값 뽑기 ──────────────────────────────────────────────────────────
$nieOld = 0
$nieNew = 0
$codePayload = ''
$verdict = ''

if ($tool -eq 'Write') {
    try { $codePayload = [string]$ti.content } catch { $codePayload = '' }

    # 디스크의 기존 파일과 대조한다. 없으면 신규 뼈대 생성이므로 old = 0.
    $existing = ''
    try {
        if (Test-Path -LiteralPath $path) {
            $existing = Get-Content -LiteralPath $path -Raw -Encoding UTF8
        }
    } catch { $existing = '' }

    $nieOld = ([regex]::Matches($existing, 'NotImplementedError')).Count
    $nieNew = ([regex]::Matches($codePayload, 'NotImplementedError')).Count

    if ($nieNew -lt $nieOld) { $verdict = 'todo-filled' }
}
else {
    $os = ''
    $ns = ''
    try { $os = [string]$ti.old_string } catch { }
    try { $ns = [string]$ti.new_string } catch { }
    $codePayload = $ns

    $nieOld = ([regex]::Matches($os, 'NotImplementedError')).Count
    $nieNew = ([regex]::Matches($ns, 'NotImplementedError')).Count

    if (($nieOld -gt 0) -and ($nieNew -lt $nieOld)) { $verdict = 'todo-filled' }
}

# ── 부수 신호: NotImplementedError 없이 로직이 대량 유입 ──────────────────────
$logic = 0
try { $logic = Count-LogicLines -Code $codePayload } catch { $logic = 0 }

if (-not $verdict) {
    if (($logic -ge $LOGIC_LINE_LIMIT) -and ($nieNew -eq 0)) { $verdict = 'bulk-logic' }
}

if (-not $verdict) { Pass }

# ── 차단 ────────────────────────────────────────────────────────────────────
$why = if ($verdict -eq 'todo-filled') {
    "TODO 자리(``raise NotImplementedError``)가 $nieOld 개에서 $nieNew 개로 줄었습니다. 구현을 채워 넣는 동작입니다."
} else {
    "``NotImplementedError`` 없이 로직 $logic 줄이 새로 들어옵니다 (한도 $LOGIC_LINE_LIMIT 줄). 새 구현을 삽입하는 동작입니다."
}

$msg = @"
⛔ CLAUDE.md §5-T — 손을 대신 움직이지 않는다 (이 프로젝트의 제1규율)

  대상 : $norm
  사유 : $why

이 저장소의 목적은 「돌아가는 RAG」가 아니라 「사용자의 이해」입니다.
`src/raglab/` 의 알고리즘 본체는 **사용자가 직접 씁니다.**

■ 지금 대신 해야 할 것
  1. `hint` 스킬로 **단계적 힌트**를 주십시오. 정답 코드가 아니라 방향입니다
  2. 사용자가 이미 쓴 코드가 있으면 `code-coach` 에 위임해 **어디가 왜 틀렸는지만** 짚으십시오
  3. 개념이 안 잡힌 것 같으면 `concept-explainer` 로 설명을 다시 설계하십시오

■ 하면 안 되는 우회
  · 채팅에 정답 코드 블록을 띄우고 "복사해 넣으세요" → **파일에 안 썼을 뿐 대필입니다**
  · `solutions/` 를 열어 그 내용을 설명으로 흘리기 → `guard_spoiler` 가 따로 막습니다

■ 사용자가 **명시적으로** 대필을 요청한 경우에만 (§5-T 예외)
  `.claude/state/handson_override.json` 의 files 배열에 이 경로를 등재하고 다시 시도하십시오.
  등재는 기록으로 남고, `docs/PROGRESS.md` 에도 "이 파일은 대필" 이라고 적어야 합니다.
  ⚠ 사용자가 단지 막혀서 답답해하는 것과 명시적 요청은 다릅니다. **먼저 힌트를 시도하십시오.**
"@

Deny $msg
