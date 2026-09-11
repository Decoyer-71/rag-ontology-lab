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
# ⚠ warn 은 bad 와 다르다 — 코드를 돌리는 데는 지장이 없지만 두 PC 운영에 구멍이 나는 것들
$warn = New-Object System.Collections.Generic.List[string]
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
foreach ($h in @('guard_handson.ps1', 'guard_spoiler.ps1', 'guard_claim.ps1', 'guard_review.ps1', 'guard_sync.ps1',
                 'session_start.ps1', 'leave_check.ps1', '_common.ps1')) {
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

# ── ⑦ 메모리 정션 (§15-4) — 안 돼 있으면 이 PC 의 세션은 규율 기억 없이 돈다 ────────
try {
    $ms = Get-MemoryLinkStatus -Root $root
    switch ($ms.State) {
        'linked'    { $ok.Add("메모리 정션") }
        'elsewhere' { $warn.Add("메모리 폴더가 저장소가 아닌 곳을 가리킵니다 → .claude\hooks\link_memory.ps1 -Check") }
        default     { $warn.Add("메모리가 저장소와 연결돼 있지 않습니다 — 이 PC 의 세션은 규율 기억 없이 돕니다 → .claude\hooks\link_memory.ps1 (PC 마다 한 번)") }
    }
} catch { }

# ── ⑧ 개인정보 관문 · 커밋 신원 존재 (§15-5) ───────────────────────────────────────
# ⚠⚠ `[string](& git ...)` 로 받지 않는다 — PS 5.1 은 출력이 없으면 $null 을 돌려주고, 거기에 .Trim() 을 부르면
#    SilentlyContinue 아래서 if 문 전체가 조용히 건너뛰어진다 (§6 지뢰 14 · 2026-09-11 이 경고가 실제로 사라졌다)
$hooksPath = ''
$email = ''
try {
    $hooksPath = (& git -C $root config core.hooksPath 2>$null | Out-String).Trim()
    $email = (& git -C $root config user.email 2>$null | Out-String).Trim()
} catch { }
if ($hooksPath -match '\.githooks[\\/]?$') {
    $ok.Add("개인정보 관문·자동 푸시")
} else {
    $warn.Add("개인정보 관문·자동 푸시가 꺼져 있습니다 → git config core.hooksPath .githooks (PC 마다 한 번, docs/SETUP.md §5-2)")
}
# ⚠ 이메일이 noreply 인지는 보지 않는다 — 공개는 사용자가 허용했다(2026-09-11). 비어 있으면 커밋이 실패하니 그것만 본다
if (-not $email) {
    $warn.Add("커밋 신원(user.email)이 없습니다 — 커밋이 실패합니다 (docs/SETUP.md §5-1)")
}

# ── 출력 ────────────────────────────────────────────────────────────────────
$out = New-Object System.Collections.Generic.List[string]
$out.Add("[preflight] 환경 자가진단")
if ($ok.Count -gt 0) { $out.Add("  ✅ " + ($ok -join ' · ')) }
foreach ($w in $warn) { $out.Add("  ⚠ $w") }
if ($bad.Count -gt 0) {
    foreach ($b in $bad) { $out.Add("  ⛔ $b") }
    $out.Add("  → 조치는 docs/SETUP.md 에 있습니다. ⚠ 고치기 전에 코드를 돌리지 마십시오.")
}

Write-Output ($out -join "`n")
exit 0
