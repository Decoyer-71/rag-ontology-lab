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

  ⚠ 하는 일은 넷이다:
    ① `git fetch` 로 원격을 확인한다
    ② ⭐ **안전할 때만 받는다** — behind 이고, 내 쪽에 새 커밋이 없고, 추적 파일 변경이 0 일 때만
       `git merge --ff-only`. 병합이 일어날 수 없는 조건이라 잃는 데이터가 없다 (2026-09-11 추가)
    ③ behind/ahead/미커밋 수를 `.claude/state/sync_session.json` 에 쓴다
    ④ 사람이 읽을 배너를 찍는다

  ⚠⚠ 왜 ②를 여기서 하는가 — 복습 계획(review_due)이 **받은 뒤의** review.json 을 봐야 한다.
     그래서 session_start.ps1 이 이 스크립트를 **맨 먼저** 부른다 (CLAUDE.md §15-3).
     갈라진 이력(diverged)은 자동으로 합치지 않는다 — 그건 사람이 판단한다.

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

    # ── 추적 파일의 미커밋 변경 수 — 자동 받기의 전제이자, 두고 가는 작업의 신호 ──
    # ⚠ --no-optional-locks : 사용자가 동시에 git 을 써도 index.lock 충돌을 만들지 않는다
    $dirty = 0
    try {
        $dirty = @(& git --no-optional-locks status --porcelain --untracked-files=no 2>$null | Where-Object { $_ }).Count
    } catch { }

    # ── ⭐ 자동 받기 — fast-forward 만 ─────────────────────────────────────────
    # ⚠⚠ 조건 셋이 모두 참일 때만 한다:
    #   · behind > 0  — 받을 것이 있다
    #   · ahead = 0   — 내 쪽에 새 커밋이 없다 = 병합이 일어날 수 없다
    #   · dirty = 0   — 덮어쓸 작업이 없다 (추적 안 되는 파일은 git 이 스스로 지킨다)
    # 이 조건에서 --ff-only 는 「브랜치 포인터를 앞으로 당기기」만 한다. fetch 가 실패해도
    # 마지막으로 받아 둔 원격 기준으로 당기는 것이라 안전하다.
    $pulled = 0
    if ($behind -gt 0 -and $ahead -eq 0 -and $dirty -eq 0) {
        $null = & git merge --ff-only --quiet $upstream 2>&1
        if ($LASTEXITCODE -eq 0) {
            $pulled = $behind
            $behind = 0
        }
    }

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
        dirty       = $dirty
        pulled      = $pulled
        fetch_ok    = $fetchOk
        # ⚠⚠ guard_sync.ps1 이 읽는 값이다. 이름을 바꾸면 훅도 같이 고쳐라.
        state       = $state
    })

    # ── 배너 ────────────────────────────────────────────────────────────────
    if (-not $fetchOk) {
        Write-Output "[sync] ⚠ 원격 확인 실패(오프라인?). **마지막으로 알던 값**으로 판단합니다 — behind $behind · ahead $ahead"
    }

    if ($pulled -gt 0) {
        Write-Output "[sync] ⬇ 다른 PC 작업 $pulled 커밋을 받았습니다 (fast-forward — 병합 없음)"
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
            if ($dirty -gt 0) {
                Write-Output "       미커밋 변경 $dirty 파일 때문에 자동으로 받지 못했습니다 → 커밋한 뒤 git pull --rebase"
            } else {
                Write-Output "       자동 받기(fast-forward)가 실패했습니다 → git pull --rebase"
            }
            Write-Output "       지금 진행하면 진도·복습 이력이 충돌합니다"
        }
        'diverged' {
            Write-Output "[sync] ⛔⛔ 이력이 갈라졌습니다 — 로컬 $ahead 개 / 원격 $behind 개"
            Write-Output "       git pull --rebase 로 합치십시오. ⚠ progress.json·review.json 충돌은"
            Write-Output "       더 진행된 쪽을 택하고 completed_stages 는 합집합으로 만듭니다 (docs/SETUP.md §8)"
            if ($dirty -gt 0) {
                Write-Output "       ⚠ 미커밋 변경 $dirty 파일이 있으면 pull --rebase 가 거부됩니다 — 먼저 커밋하십시오"
            }
        }
    }

    if ($dirty -gt 0 -and @('clean', 'ahead') -contains $state) {
        Write-Output "[sync] ⚠ 커밋 안 된 변경 $dirty 파일이 남아 있습니다 — 다른 PC 로 옮기기 전에 커밋하십시오"
    }
} finally {
    try { Pop-Location } catch { }
}

exit 0
