# -*- coding: utf-8 -*-
<#
  Stop 훅 — **떠나기 전에 두고 가는 것이 없는지** 응답이 끝날 때마다 본다. (CLAUDE.md §15-6)

  ⚠⚠ 왜 필요한가
  ─────────────────────────────────────────────────────────────────────────────
  sync_check 는 **받는 쪽**만 지킨다. 원격만 보기 때문에 PC A 에 두고 온 작업은 PC B 에서
  보이지 않는다 — B 는 원격과 같으니 통과시키고, 나중에 A 가 올리면 이력이 갈라진다.
  그걸 막을 수 있는 곳은 **떠나는 쪽**뿐이다.

    · 커밋 안 된 변경    → 다른 PC 로 안 따라간다
    · 올라가지 않은 커밋 → 자동 푸시가 실패한 것이다 (오프라인 · 개인정보 관문 · 원격이 앞섬)

  ⚠ 막지 않는다 — 알리기만 한다. JSON `systemMessage` 로 사용자 화면에 한 줄 띄운다.
  ⚠ 매 응답마다 띄우면 소음이다. 코드를 짜는 동안은 늘 「미커밋」이라 매번 띄우면 아무도 안 읽는다.
     그래서 **상태가 바뀔 때**, 같은 상태면 **20분에 한 번**만 띄운다 (leave_session.json).
  ⚠ `git --no-optional-locks` — 사용자가 동시에 git 을 쓸 때 index.lock 충돌을 만들지 않는다.
  ⚠⚠ fail-open — 어떤 오류든 조용히 통과한다. 이 훅은 방어선이 아니라 알림이다.
#>

$ErrorActionPreference = 'SilentlyContinue'
$RepeatMinutes = 20

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

# ── 입력 — Stop 훅이 이미 한 번 이어가게 만든 상태면 아무것도 안 한다 (무한 반복 방지) ──
try {
    $raw = [Console]::In.ReadToEnd()
    if ($raw.Length -gt 0 -and $raw[0] -eq [char]0xFEFF) { $raw = $raw.Substring(1) }
    if ($raw) {
        $payload = $raw | ConvertFrom-Json
        if ($payload.stop_hook_active) { exit 0 }
    }
} catch { }

# ── 상태 재기 — 원격에 묻지 않는다. 마지막으로 알던 원격 기준이면 충분하다 ──────────
$lines = @()
try {
    Push-Location -LiteralPath $root
    $lines = @(& git --no-optional-locks status --porcelain=v1 -b --untracked-files=no 2>$null)
    # ⚠ Out-String 을 거친다 — `[string](& git ...)` 은 출력이 없으면 $null 이다 (CLAUDE.md §6 지뢰 14)
    $hooksPath = (& git config core.hooksPath 2>$null | Out-String).Trim()
    $autoPush = (& git config --bool lab.autopush 2>$null | Out-String).Trim()
} catch {
    exit 0
} finally {
    try { Pop-Location } catch { }
}
if ($lines.Count -eq 0) { exit 0 }

$ahead = 0
if ([string]$lines[0] -match '\[ahead (\d+)') { $ahead = [int]$Matches[1] }
$dirty = @($lines | Select-Object -Skip 1 | Where-Object { $_ }).Count

$statePath = Join-Path $root '.claude\state\leave_session.json'

if ($ahead -eq 0 -and $dirty -eq 0) {
    # 깨끗해졌다 — 다음에 다시 더러워지면 곧바로 알리도록 기억을 지운다
    Remove-Item -LiteralPath $statePath -Force -ErrorAction SilentlyContinue
    exit 0
}

# ── 소음 줄이기 — 같은 상태면 20분에 한 번 ──────────────────────────────────────
$sig = '{0}{1}' -f ([int]($ahead -gt 0)), ([int]($dirty -gt 0))
$now = Get-Date
try {
    if (Test-Path -LiteralPath $statePath) {
        $prev = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($prev -and ([string]$prev.sig -eq $sig)) {
            $last = [datetime]::Parse([string]$prev.at)
            if (($now - $last).TotalMinutes -lt $RepeatMinutes) { exit 0 }
        }
    }
} catch { }
try {
    $json = [ordered]@{ sig = $sig; at = $now.ToString('o') } | ConvertTo-Json -Compress
    [System.IO.File]::WriteAllText($statePath, $json, (New-Object System.Text.UTF8Encoding($false)))
} catch { }

# ── 알림 ────────────────────────────────────────────────────────────────────
$auto = ($hooksPath -match '\.githooks[\\/]?$') -and ($autoPush -ne 'false')

$what = New-Object System.Collections.Generic.List[string]
if ($dirty -gt 0) { $what.Add("커밋 안 된 변경 $dirty 파일") }
if ($ahead -gt 0) { $what.Add("올라가지 않은 커밋 $ahead 개") }

if ($ahead -gt 0) {
    $todo = 'git push 로 원인을 확인하십시오 (오프라인 · 개인정보 관문 · 원격이 앞섬)'
} elseif ($auto) {
    $todo = '다른 PC 로 옮기기 전에 커밋하십시오 — 커밋하면 자동으로 올라갑니다 · 이어받기 메모는 docs/PROGRESS.md'
} else {
    $todo = '다른 PC 로 옮기기 전에 커밋·푸시하십시오 · 이어받기 메모는 docs/PROGRESS.md'
}

$msg = "⚠ [떠나기 전 점검] $($what -join ' · ') → $todo (CLAUDE.md §15-6)"
Write-Output (@{ systemMessage = $msg } | ConvertTo-Json -Compress)
exit 0
