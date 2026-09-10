# -*- coding: utf-8 -*-
<#
  SessionStart 훅 — **학습 커밋을 따라잡는다.** (CLAUDE.md §14)

  ⚠⚠ 왜 PostToolUse 가 아니라 SessionStart 인가
  ─────────────────────────────────────────────────────────────────────────────
  커밋은 **사용자가 터미널에서 직접** 할 수도 있다. Claude 의 도구 호출을 지켜보는
  PostToolUse 훅으로 잡으면 그때마다 놓친다.
  그래서 「지켜보기」가 아니라 **「따라잡기」** 로 만든다 — 세션이 시작될 때
  git 을 직접 읽어 마지막 학습 커밋을 확인한다. 훅이 한 번 죽어도 다음 세션에 복구된다.

  ⚠ 학습 커밋의 정의 (§14-1)
  ─────────────────────────────────────────────────────────────────────────────
  `src/raglab/` 를 건드린 커밋만 학습 커밋이다.
  `docs/`·`.claude/` 만 고친 커밋은 학습이 아니다 — 그걸 세면 "오늘 공부했다"가
  문서 정리만으로 성립해 버린다.

  ⚠⚠ fail-open — 훅 오류로는 아무것도 막지 않는다. 단, 조용히 죽지는 않는다.
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

$py = Join-Path $root '.venv\Scripts\python.exe'
$cli = Join-Path $root 'src\labkit\review.py'
if (-not (Test-Path -LiteralPath $py) -or -not (Test-Path -LiteralPath $cli)) { exit 0 }

# ── 마지막 학습 커밋 찾기 ────────────────────────────────────────────────────
# ⚠ `-- src/raglab` 로 경로를 한정한다. 이것이 「학습 커밋」의 기계적 정의다.
$sha = $null
$at  = $null
try {
    Push-Location -LiteralPath $root
    $line = & git log -1 --format='%H|%cI' -- 'src/raglab' 2>$null
    Pop-Location
    if ($line) {
        $parts = ([string]$line).Trim() -split '\|'
        if ($parts.Count -ge 2) { $sha = $parts[0]; $at = $parts[1] }
    }
} catch {
    try { Pop-Location } catch { }
}

if (-not $sha) { exit 0 }

# ── 이미 아는 커밋이면 아무것도 하지 않는다 ──────────────────────────────────
$statePath = Join-Path $root '.claude\state\review.json'
$known = $null
if (Test-Path -LiteralPath $statePath) {
    try {
        $st = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $known = [string]$st.last_learning_commit
    } catch { }
}
if ($known -eq $sha) { exit 0 }

try {
    $null = & $py $cli touch --commit $sha --at $at 2>&1
} catch { }

exit 0
