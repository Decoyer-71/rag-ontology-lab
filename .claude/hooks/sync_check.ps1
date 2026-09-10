# -*- coding: utf-8 -*-
<#
  SessionStart 훅 — **PC 두 대를 오갈 때 원격과 어긋난 상태를 세션 시작에 잡는다.** (CLAUDE.md §15)

  ⚠⚠ 왜 필요한가
  ─────────────────────────────────────────────────────────────────────────────
  이 저장소는 **학습 상태 자체를 커밋한다** — progress.json(진도),
  review.json(복습 카드·간격·이력), review_log.json(인출 기록), docs/PROGRESS.md.
  그래서 두 PC 를 오가면 그 파일들이 **양쪽에서 동시에 바뀐다.**

  가장 흔한 사고는 이것이다:
      PC A 에서 작업 → 푸시를 잊음 → PC B 에서 그대로 시작 → 이력이 갈라짐
      → progress.json·review.json 이 충돌 → 진도와 복습 이력이 뒤섞인다

  복습 카드의 `due`·`interval_days`·`history` 는 카드마다 바뀌므로 **거의 확실히 충돌한다.**
  그리고 그건 「어느 쪽이 맞는가」를 사람이 판단해야 하는 종류의 충돌이다.

  ⚠ 하는 일은 셋뿐이다:
    ① `git fetch` 로 원격을 확인한다 (읽기 전용. 아무것도 바꾸지 않는다)
    ② behind/ahead 를 세어 `.claude/state/sync_session.json` 에 쓴다
    ③ 사람이 읽을 배너를 찍는다

  ⚠⚠ fail-open — 오프라인이거나 fetch 가 실패하면 **아무것도 막지 않는다.**
     그래서 판정 파일을 **맨 먼저 지우고** 시작한다. 훅이 중간에 죽어도
     낡은 판정이 남아 영원히 막는 일이 없도록.
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

$statePath = Join-Path $root '.claude\state\sync_session.json'

# ⚠⚠ 낡은 판정을 먼저 지운다. 이 훅이 죽으면 「판정 없음」이 되고, 그러면 guard_sync 는 통과시킨다.
Remove-Item -LiteralPath $statePath -Force -ErrorAction SilentlyContinue

function Write-State($obj) {
    try {
        $json = $obj | ConvertTo-Json -Depth 6
        [System.IO.File]::WriteAllText($statePath, $json, (New-Object System.Text.UTF8Encoding($false)))
    } catch { }
}

Push-Location -LiteralPath $root
try {
    $branch = (& git rev-parse --abbrev-ref HEAD 2>$null | Out-String).Trim()
    $upstream = (& git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null | Out-String).Trim()

    if (-not $upstream) {
        Write-Output "[sync] ⚠ upstream 이 없습니다 (브랜치 $branch). 다른 PC 와 동기화되지 않습니다."
        Write-Output "       git push -u origin $branch 로 연결하십시오."
        exit 0
    }

    # ── 원격 확인. 읽기 전용이고, 실패하면 그냥 넘어간다 ────────────────────
    # ⚠⚠ GIT_TERMINAL_PROMPT=0 을 반드시 세운다.
    #   이 훅은 -NonInteractive 로 돌아 입력을 받을 수 없는데, git 이 자격증명을 물으면
    #   **세션 시작이 통째로 멈춘다.** 0 이면 묻는 대신 즉시 실패하고 우리는 fail-open 한다.
    $fetchOk = $true
    $prevPrompt = $env:GIT_TERMINAL_PROMPT
    try {
        $env:GIT_TERMINAL_PROMPT = '0'
        $null = & git fetch --quiet 2>&1
        if ($LASTEXITCODE -ne 0) { $fetchOk = $false }
    } catch {
        $fetchOk = $false
    } finally {
        $env:GIT_TERMINAL_PROMPT = $prevPrompt
    }

    $behind = 0
    $ahead = 0
    try {
        $counts = (& git rev-list --left-right --count "$upstream...HEAD" 2>$null | Out-String).Trim()
        $parts = $counts -split '\s+'
        if ($parts.Count -ge 2) {
            $behind = [int]$parts[0]
            $ahead = [int]$parts[1]
        }
    } catch { }

    $state = 'clean'
    if     ($behind -gt 0 -and $ahead -gt 0) { $state = 'diverged' }
    elseif ($behind -gt 0)                   { $state = 'behind' }
    elseif ($ahead  -gt 0)                   { $state = 'ahead' }

    Write-State ([ordered]@{
        computed_at = (Get-Date).ToString('s')
        branch      = $branch
        upstream    = $upstream
        behind      = $behind
        ahead       = $ahead
        fetch_ok    = $fetchOk
        # ⚠⚠ guard_sync.ps1 이 읽는 값이다. 이름을 바꾸면 훅도 같이 고쳐라.
        state       = $state
    })

    # ── 배너 ────────────────────────────────────────────────────────────────
    if (-not $fetchOk) {
        Write-Output "[sync] ⚠ 원격 확인 실패(오프라인?). **마지막으로 알던 값**으로 판단합니다 — behind $behind · ahead $ahead"
    }

    switch ($state) {
        'clean' {
            Write-Output "[sync] ✅ 원격과 같음 ($upstream)"
        }
        'ahead' {
            Write-Output "[sync] ⚠ 푸시 안 된 커밋 $ahead 개 ($upstream 보다 앞섬)"
            Write-Output "       ⚠⚠ **다른 PC 로 옮기기 전에 반드시 푸시하십시오.** 안 하면 저쪽에서 이력이 갈라집니다"
        }
        'behind' {
            Write-Output "[sync] ⛔ 원격이 $behind 커밋 앞서 있습니다 — **다른 PC 에서 한 작업이 안 받아져 있습니다**"
            Write-Output "       git pull --rebase 를 먼저 하십시오. 지금 진행하면 진도·복습 이력이 충돌합니다"
        }
        'diverged' {
            Write-Output "[sync] ⛔⛔ 이력이 갈라졌습니다 — 로컬 $ahead 개 / 원격 $behind 개"
            Write-Output "       git pull --rebase 로 합치십시오. ⚠ progress.json·review.json 충돌은"
            Write-Output "       더 진행된 쪽을 택하고 completed_stages 는 합집합으로 만듭니다 (docs/SETUP.md §8)"
        }
    }
} finally {
    try { Pop-Location } catch { }
}

exit 0
