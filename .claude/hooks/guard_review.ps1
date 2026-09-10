# -*- coding: utf-8 -*-
<#
  PreToolUse 훅 — ⭐ **복습 게이트.** (CLAUDE.md §14)

  밀린 복습이 있으면 **새 단계를 여는 동작**을 막는다.

  ⚠⚠ 왜 「사용자가 코드 쓰는 것」을 막지 않는가
  ─────────────────────────────────────────────────────────────────────────────
  PreToolUse 훅은 **Claude 의 도구 호출**에만 걸린다. 사용자가 편집기에서 직접 짜는
  것은 훅으로 막을 수 없고, 막아서도 안 된다 — 그건 학습 자체를 막는 것이다.

  그래서 이 훅이 막는 것은 **Claude 가 새 단계를 여는 행위**다:
    · next-step 스킬 호출            ← 새 단계를 시작하는 정문
    · docs/stages/NN-*.md 집필        ← 새 단계 강의
    · tests/test_stageNN_*.py 작성    ← 새 단계 명세
    · src/raglab/ 새 뼈대 생성        ← 새 단계 작업대
    · .claude/state/progress.json 갱신 ← 진도 전진

  즉 「복습 안 하고 진도만 나가는 것」을 막는다. §14-4 가 그것이다.

  ⚠ 막지 않는 것 — 복습 자체와 기록
  ─────────────────────────────────────────────────────────────────────────────
  review/hint/checkpoint 스킬, 복습 상태 파일, docs/PROGRESS.md 는 언제나 통과한다.
  게이트가 자기 자신을 여는 길까지 막으면 그건 데드락이다.

  ⚠ 탈출구 — 건너뛰기는 **기록으로 남는다** (§14-6)
  ─────────────────────────────────────────────────────────────────────────────
      .venv\Scripts\python.exe src\labkit\review.py skip --days 1 --reason "사유"
  건너뛴 횟수도 데이터다. 몇 번 건너뛰었는지가 review.json 의 skip_log 에 쌓인다.

  ⚠⚠ fail-open — 훅 자체의 오류로는 아무것도 막지 않는다.
     세션 파일이 없으면(=계획을 못 세웠으면) 통과시킨다.
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

# ── 루트 ────────────────────────────────────────────────────────────────────
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

# ── 게이트 상태 ─────────────────────────────────────────────────────────────
$sessPath = Join-Path $root '.claude\state\review_session.json'
if (-not (Test-Path -LiteralPath $sessPath)) { Pass }

$sess = $null
try {
    $sess = Get-Content -LiteralPath $sessPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch { Pass }
if (-not $sess) { Pass }
if ([string]$sess.gate -ne 'blocked') { Pass }

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

    # ── 언제나 통과 — 복습 자체와 기록으로 가는 길 ──────────────────────────
    if ($norm -match '\.claude/state/review')       { Pass }
    if ($norm -match 'outputs/metrics/review_log')  { Pass }
    if ($norm -match 'docs/PROGRESS\.md$')          { Pass }

    # ── ⚠⚠ 데드락 방지 — src/raglab/ 의 **기존 파일**은 막지 않는다 ─────────
    #   복습의 코드 카드는 「이미 통과한 함수를 빈칸으로 되돌리는」 동작이고,
    #   그건 정확히 src/raglab/ 의 기존 파일을 고치는 일이다.
    #   그걸 막으면 게이트가 자기를 여는 유일한 길을 막는 것이 된다.
    #   ⚠ 여기를 열어도 대필은 못 한다 — guard_handson 이 따로 막는다 (§5-T).
    #   막아야 하는 것은 **새 단계의 새 작업대**, 즉 아직 없는 파일을 만드는 경우다.
    $isNewRaglabFile = $false
    if ($norm -match 'src/raglab/') {
        try { $isNewRaglabFile = -not (Test-Path -LiteralPath $path) } catch { $isNewRaglabFile = $false }
    }

    # ── 새 단계를 여는 동작 ─────────────────────────────────────────────────
    if     ($norm -match 'docs/stages/')                 { $what = '새 단계 강의(docs/stages/)' }
    elseif ($norm -match 'tests/test_stage')             { $what = '새 단계 테스트(tests/test_stage*)' }
    elseif ($isNewRaglabFile)                            { $what = '새 단계 뼈대(src/raglab/ 새 파일)' }
    elseif ($norm -match '\.claude/state/progress\.json') { $what = '진도 전진(progress.json)' }
}

if (-not $what) { Pass }

# ── 차단 ────────────────────────────────────────────────────────────────────
$due   = [int]$sess.due_total
$take  = @($sess.cards).Count
$left  = @($sess.cards | Where-Object { @($sess.reviewed) -notcontains $_ }).Count
$gapKo = if ($null -eq $sess.gap_days) { '학습 기록 없음' } else { "$($sess.gap_days)일" }

$revisitLine = ''
if ($null -ne $sess.revisit_stage) {
    $revisitLine = "`n  ⚠⚠ 공백이 깁니다. 카드 몇 장이 아니라 「Stage $($sess.revisit_stage) 재방문」이 맞습니다 (§14-5)"
}

$msg = @"
⛔ CLAUDE.md §14 — 복습을 건너뛰고 진도만 나가지 않는다

  막은 동작 : $what
  밀린 복습 : 만기 $due 장 (이번 세션 배정 $take 장 · 아직 $left 장 남음)
  공백기간   : 마지막 학습 이후 $gapKo$revisitLine

이 저장소에서 「단계를 통과했다」는 그날 이해했다는 뜻이지 한 달 뒤에도 안다는 뜻이
아닙니다. 면접은 마지막 커밋 3개월 뒤에 옵니다 (§13).

■ 지금 해야 할 것
  1. review 스킬을 도십시오. ⚠⚠ **다시 읽기가 아니라 인출입니다** —
     근거상 다시 읽기는 최저 등급 기법이고 스스로 인출하기가 최고 등급입니다 (§14-2)
  2. 코드 카드는 사용자가 이미 통과시킨 함수를 빈칸으로 되돌리고 다시 짜게 합니다.
     정답 키는 git history 에, 채점표는 tests/ 에 이미 있습니다
  3. 카드를 다 돌면 게이트가 저절로 열립니다

■ 정말 건너뛰어야 하면 (기록이 남습니다)
     .venv\Scripts\python.exe src\labkit\review.py skip --days 1 --reason "사유"
  ⚠ 건너뛴 횟수도 데이터입니다. review.json 의 skip_log 에 쌓입니다

■ 하면 안 되는 우회
  · review_session.json 을 손으로 고쳐 게이트를 여는 것 → 그건 측정을 조작하는 것입니다
  · 복습 없이 "이번만" 진도를 나가고 나중에 몰아서 하기 → 몰아서 하면 간격 효과가 사라집니다
"@

Deny $msg
