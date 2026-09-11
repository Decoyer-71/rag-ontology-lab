# -*- coding: utf-8 -*-
<#
  PreToolUse 훅 — ⭐ **원격과 어긋난 채로 새 단계를 열지 않는다.** (CLAUDE.md §15)

  ⚠⚠ 왜 막아야 하는가 (경고로는 부족한 이유)
  ─────────────────────────────────────────────────────────────────────────────
  이 저장소는 **학습 상태 자체를 커밋한다.** 원격이 앞서 있는 상태에서 새 단계를
  시작하면 progress.json·review.json·docs/PROGRESS.md 가 양쪽에서 갈라지고,
  그 충돌은 「어느 쪽이 맞는가」를 사람이 판단해야 하는 종류다.
  **되돌리는 비용이 pull 한 번보다 훨씬 크다.** 그래서 사후 경고가 아니라 사전 차단이다.

  ⚠ 막는 범위 — guard_review 와 같다. **새 단계를 여는 행위**만이다.
      · next-step 스킬 · docs/stages/ · tests/test_stage* · src/raglab 새 파일 · progress.json
    사용자가 편집기에서 코드 짜는 것은 훅으로 막히지도 않고 막아서도 안 된다.

  ⚠ 막지 **않는** 경우
      · state = clean  : 원격과 같다
      · state = ahead  : 푸시만 안 됐다. 이건 **떠나기 전에** 할 일이지 지금 막을 일이 아니다
      · 판정 파일 없음 : 오프라인이거나 sync_check 가 못 돌았다 → fail-open

  즉 막는 것은 **behind · diverged 둘뿐**이다.

  ⚠⚠ fail-open — 훅 자체의 오류로는 아무것도 막지 않는다.
#>

$ErrorActionPreference = 'Stop'

try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8NoBom
    $OutputEncoding = $utf8NoBom
} catch { }

function Pass { exit 0 }

function Deny([string]$Message) {
    [Console]::Error.Write($Message)
    exit 2
}

$startDir = $PSScriptRoot
if (-not $startDir) { try { $startDir = Split-Path -Parent $MyInvocation.MyCommand.Path } catch {} }

$root = $null
try {
    . (Join-Path $startDir '_common.ps1')
    $rr = Resolve-RepoRoot -StartDir $startDir -Markers @('.claude\hooks')
    $root = $rr.Root
} catch {
    try {
        $cand = Split-Path -Parent (Split-Path -Parent $startDir)
        if ($cand -and (Test-Path -LiteralPath (Join-Path $cand '.claude\hooks'))) { $root = $cand }
    } catch { }
}
if (-not $root) { Pass }

# ── 판정 읽기 ───────────────────────────────────────────────────────────────
$statePath = Join-Path $root '.claude\state\sync_session.json'
if (-not (Test-Path -LiteralPath $statePath)) { Pass }

$sync = $null
try {
    $sync = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch { Pass }
if (-not $sync) { Pass }

$state = [string]$sync.state
if (@('behind', 'diverged') -notcontains $state) { Pass }

# ── 입력 파싱 ───────────────────────────────────────────────────────────────
try {
    $raw = [Console]::In.ReadToEnd()
    if ($raw.Length -gt 0 -and $raw[0] -eq [char]0xFEFF) { $raw = $raw.Substring(1) }
    $payload = $raw | ConvertFrom-Json
} catch { Pass }
if (-not $payload) { Pass }

$tool = [string]$payload.tool_name
$ti = $payload.tool_input
if (-not $ti) { Pass }

$what = ''

if ($tool -eq 'Skill') {
    $skill = ''
    try { $skill = [string]$ti.skill } catch { }
    if ($skill -eq 'next-step') { $what = 'next-step 스킬(새 단계 시작)' }
}
elseif (@('Write', 'Edit', 'NotebookEdit') -contains $tool) {
    $path = ''
    try { $path = [string]$ti.file_path } catch { }
    if (-not $path) { Pass }
    $norm = $path.Replace('\', '/')

    # ── 언제나 통과 — 동기화 자체와 기록으로 가는 길 ────────────────────────
    if ($norm -match '\.claude/state/(review|sync)') { Pass }
    if ($norm -match 'outputs/metrics/review_log')   { Pass }
    if ($norm -match 'docs/PROGRESS\.md$')           { Pass }

    $isNewRaglabFile = $false
    if ($norm -match 'src/raglab/') {
        try { $isNewRaglabFile = -not (Test-Path -LiteralPath $path) } catch { $isNewRaglabFile = $false }
    }

    if     ($norm -match 'docs/stages/')                  { $what = '새 단계 강의(docs/stages/)' }
    elseif ($norm -match 'tests/test_stage')              { $what = '새 단계 테스트(tests/test_stage*)' }
    elseif ($isNewRaglabFile)                             { $what = '새 단계 뼈대(src/raglab/ 새 파일)' }
    elseif ($norm -match '\.claude/state/progress\.json') { $what = '진도 전진(progress.json)' }
}

if (-not $what) { Pass }

# ── 차단 ────────────────────────────────────────────────────────────────────
$behind = [int]$sync.behind
$ahead  = [int]$sync.ahead
$dirty  = 0
try { $dirty = [int]$sync.dirty } catch { }

# ⚠ 미커밋 변경이 있으면 sync_check 가 자동으로 못 받았고, pull --rebase 도 거부된다
$todo = if ($dirty -gt 0) {
    @"
     미커밋 변경 $dirty 파일이 있어 자동으로 받지 못했습니다. 커밋한 뒤:
     git pull --rebase
     (커밋하기 싫으면: git stash → git pull --rebase → git stash pop)
"@
} else {
    "     git pull --rebase"
}

$diag = if ($state -eq 'diverged') {
    "이력이 갈라졌습니다 — 로컬만 있는 커밋 $ahead 개 / 원격만 있는 커밋 $behind 개"
} else {
    "원격이 $behind 커밋 앞서 있습니다 — 다른 PC 에서 한 작업이 아직 안 받아져 있습니다"
}

$extra = if ($state -eq 'diverged') {
    @"

■ 충돌이 나면 (거의 확실히 납니다)
  · progress.json      → 더 진행된 쪽. completed_stages 는 **합집합**
  · review.json        → ⚠⚠ 카드의 due·interval_days·history 는 **합칠 수 없습니다.**
                          더 최근에 복습한 쪽을 택하십시오. 애매하면 그 카드만 만기로 되돌립니다
                          (틀리게 합치느니 한 번 더 인출하는 편이 쌉니다)
  · review_log.json    → entries 는 **양쪽을 다 남깁니다.** 인출 기록은 지우면 안 됩니다
  · outputs/metrics/*  → ⚠ 임의로 합치지 말고 **다시 측정**하십시오 (§4)
"@
} else { '' }

$msg = @"
⛔ CLAUDE.md §15 — 원격과 어긋난 채로 새 단계를 열지 않는다

  막은 동작 : $what
  상태      : $diag
  브랜치    : $($sync.branch) → $($sync.upstream)

이 저장소는 **학습 상태 자체를 커밋합니다** — 진도(progress.json), 복습 카드와 간격·이력
(review.json), 인출 기록(review_log.json), 막힌 지점(docs/PROGRESS.md).
지금 진행하면 그것들이 양쪽에서 갈라지고, **되돌리는 비용이 pull 한 번보다 훨씬 큽니다.**

■ 지금 해야 할 것
$todo
  그다음 이 세션을 다시 시작하거나, 아래 명령으로 판정과 복습 계획을 다시 세우십시오:
     powershell -NoProfile -ExecutionPolicy Bypass -File .claude\hooks\session_start.ps1
$extra
■ 막지 않는 것
  복습(review 스킬)·힌트·기록은 그대로 됩니다. 막은 것은 **새 단계를 여는 행위**뿐입니다.
"@

Deny $msg
