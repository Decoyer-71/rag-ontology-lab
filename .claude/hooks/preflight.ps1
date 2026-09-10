# -*- coding: utf-8 -*-
<#
  SessionStart 훅 — **환경 자가진단.** (CLAUDE.md §2)

  ⚠ 왜 필요한가
  ─────────────────────────────────────────────────────────────────────────────
  이 저장소는 **다른 PC 로 옮겨 다닌다**(사용자 요구, 2026-09-10).
  옮겨간 곳에서 `.venv` 는 커밋되지 않았고, `uv` 경로가 다르고,
  `.claude/memory` 는 사본일 뿐이다. **그걸 모른 채 시작하면 첫 명령부터 깨진다.**

  §2 의 실측표가 「그 PC 에서도 참인지」를 세션 시작 때 한 번 확인한다.

  ⚠ 진단이지 수리가 아니다. 고치는 것은 사용자와 함께 한다 → docs/SETUP.md
#>

$ErrorActionPreference = 'SilentlyContinue'

# ⚠⚠ 출력 인코딩을 UTF-8 로 고정한다.
#   Windows PowerShell 5.1 기본값은 OEM 코드페이지(cp949)라,
#   차단 사유의 한글이 깨진 채 Claude 에게 전달된다 → 훅이 반쯤 무력화된다.
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

if (-not $root) {
    Write-Output "[preflight] ⛔ 저장소 루트를 못 찾았습니다. 훅 전체가 무력화된 상태입니다."
    exit 0
}

$bad = New-Object System.Collections.Generic.List[string]
$ok = New-Object System.Collections.Generic.List[string]

# ── ① 파이썬 ────────────────────────────────────────────────────────────────
$py = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $py) {
    $ver = ''
    try { $ver = (& $py --version 2>&1 | Out-String).Trim() } catch { }
    if ($ver) { $ok.Add("파이썬 $ver") } else { $bad.Add(".venv 는 있으나 python.exe 가 안 돕니다") }
} else {
    $bad.Add(".venv 가 없습니다 → docs/SETUP.md 대로 uv 로 만드십시오 (커밋 대상이 아닙니다)")
}

# ── ② 핵심 패키지 ───────────────────────────────────────────────────────────
if (Test-Path -LiteralPath $py) {
    $probe = ''
    try {
        $probe = (& $py -c "import numpy,yaml,pytest;print('pkg-ok')" 2>&1 | Out-String)
    } catch { }
    if ($probe -match 'pkg-ok') {
        $ok.Add("numpy·pyyaml·pytest")
    } else {
        $bad.Add("의존성 미설치 → uv pip install --python .venv/Scripts/python.exe -r requirements.txt")
    }
}

# ── ③ 훅 배선 ───────────────────────────────────────────────────────────────
foreach ($h in @('guard_handson.ps1', 'guard_spoiler.ps1', 'guard_claim.ps1', '_common.ps1')) {
    $hp = Join-Path $root ".claude\hooks\$h"
    if (-not (Test-Path -LiteralPath $hp)) { $bad.Add("훅 누락: $h") }
}

# ── ④ 진도 파일 ─────────────────────────────────────────────────────────────
$pp = Join-Path $root '.claude\state\progress.json'
if (-not (Test-Path -LiteralPath $pp)) {
    $bad.Add("progress.json 이 없습니다 — guard_spoiler 가 모든 solutions/ 를 막습니다")
}

# ── ⑤ 코퍼스 ────────────────────────────────────────────────────────────────
$corpus = Join-Path $root 'data\synthetic\docs'
if (Test-Path -LiteralPath $corpus) {
    $n = @(Get-ChildItem -LiteralPath $corpus -Filter *.md -ErrorAction SilentlyContinue).Count
    if ($n -gt 0) { $ok.Add("합성 코퍼스 문서 $n 건") }
    else { $bad.Add("코퍼스가 비었습니다 → .venv/Scripts/python.exe data/make_corpus.py") }
} else {
    $bad.Add("data/synthetic/docs 가 없습니다 → .venv/Scripts/python.exe data/make_corpus.py")
}

# ── ⑥ git 원격 (다른 PC 이관용) ──────────────────────────────────────────────
$remote = ''
try {
    Push-Location $root
    $remote = (& git remote -v 2>&1 | Out-String).Trim()
    Pop-Location
} catch { }
if (-not $remote) {
    $bad.Add("git 원격이 없습니다 — 다른 PC 에서 이어받으려면 필요합니다 (repo-publish 스킬)")
} else {
    $ok.Add("git 원격 설정됨")
}

# ── 출력 ────────────────────────────────────────────────────────────────────
$out = New-Object System.Collections.Generic.List[string]
$out.Add("[preflight] 환경 자가진단")
if ($ok.Count -gt 0) { $out.Add("  ✅ " + ($ok -join ' · ')) }
if ($bad.Count -gt 0) {
    foreach ($b in $bad) { $out.Add("  ⛔ $b") }
    $out.Add("  → 조치는 docs/SETUP.md 에 있습니다. ⚠ 고치기 전에 코드를 돌리지 마십시오.")
}

Write-Output ($out -join "`n")
exit 0
