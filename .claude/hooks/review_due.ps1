# -*- coding: utf-8 -*-
<#
  SessionStart 훅 — **이번 세션의 복습 계획을 세우고 게이트를 정한다.** (CLAUDE.md §14)

  ⚠⚠ 왜 세션 시작에 계산하는가
  ─────────────────────────────────────────────────────────────────────────────
  §14-5 — 새 학습을 시작하기 전에 **공백기간을 반영한 복습 계획**이 먼저 있어야 한다.
  계획이 없으면 「밀린 복습」이라는 개념 자체가 성립하지 않고, guard_review 는
  막을 근거를 잃는다.

  하는 일은 둘뿐이다:
    ① `labkit/review.py session` 을 불러 `.claude/state/review_session.json` 을 쓴다
       (만기 카드 · 공백일수 · 게이트 open/blocked)
    ② 사람이 읽을 배너를 찍는다

  ⚠ 계산 자체는 파이썬이 한다. 훅은 **부르고 보여주기만** 한다 —
    같은 규칙이 두 언어로 두 번 쓰이면 반드시 갈라진다.

  ⚠⚠ fail-open — 파이썬이 없거나 죽어도 세션은 진행된다.
     단, 그 경우 게이트 파일이 낡은 채로 남지 않도록 **지운다**.
     낡은 blocked 가 남아 영원히 막는 것이 가장 나쁜 실패다.
#>

$ErrorActionPreference = 'Continue'

try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8NoBom
    $OutputEncoding = $utf8NoBom
} catch { }

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
if (-not $root) { exit 0 }

$py       = Join-Path $root '.venv\Scripts\python.exe'
$cli      = Join-Path $root 'src\labkit\review.py'
$sessPath = Join-Path $root '.claude\state\review_session.json'

if (-not (Test-Path -LiteralPath $py) -or -not (Test-Path -LiteralPath $cli)) {
    # ⚠⚠ 계산할 수 없으면 낡은 게이트를 남기지 않는다
    Remove-Item -LiteralPath $sessPath -Force -ErrorAction SilentlyContinue
    Write-Output "[review] ⚠ 복습 스케줄러를 부르지 못했습니다 (파이썬 또는 CLI 없음). 게이트를 엽니다."
    exit 0
}

try {
    $null = & $py $cli session 2>&1
} catch {
    Remove-Item -LiteralPath $sessPath -Force -ErrorAction SilentlyContinue
    Write-Output "[review] ⚠ 복습 계획 계산이 실패했습니다. 게이트를 엽니다."
    exit 0
}

if (-not (Test-Path -LiteralPath $sessPath)) { exit 0 }

$sess = $null
try {
    $sess = Get-Content -LiteralPath $sessPath -Raw -Encoding UTF8 | ConvertFrom-Json
} catch { exit 0 }
if (-not $sess) { exit 0 }

# ── 배너 ────────────────────────────────────────────────────────────────────
$due   = [int]$sess.due_total
$gapKo = if ($null -eq $sess.gap_days) { '학습 기록 없음' } else { "$($sess.gap_days)일" }

if ($due -le 0) {
    Write-Output "[review] 만기 복습 없음 · 마지막 학습 이후 $gapKo"
    exit 0
}

$take = @($sess.cards).Count
$defer = [int]$sess.deferred

Write-Output "=== 복습 (CLAUDE.md §14) ==="
Write-Output "  만기 $due 장 · 이번 세션 $take 장 · 이월 $defer 장 · 마지막 학습 이후 $gapKo"

if ($sess.skipping) {
    Write-Output "  ⚠ $($sess.skip_until) 까지 사용자가 건너뛰기를 요청한 상태입니다 — 게이트를 엽니다"
}

if ($null -ne $sess.revisit_stage) {
    Write-Output "  ⚠⚠ 공백이 깁니다. 카드 몇 장이 아니라 **Stage $($sess.revisit_stage) 재방문**이 맞습니다 (§14-5)"
}

if ($sess.gate -eq 'blocked') {
    Write-Output "  ⛔ 게이트 blocked — 복습을 돌기 전에는 **새 단계를 열 수 없습니다** (guard_review)"
    Write-Output "     review 스킬로 시작하십시오. ⚠ 다시 읽기가 아니라 **인출**입니다"
} else {
    Write-Output "  게이트 open"
}

exit 0
