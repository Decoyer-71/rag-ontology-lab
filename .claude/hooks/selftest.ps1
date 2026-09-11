# -*- coding: utf-8 -*-
<#
  자가 시험 — **감시자도 감시받는다.** (oil_DA CLAUDE.md §5-J 에서 이식)

  ⚠⚠ 왜 이 파일이 있는가
  ─────────────────────────────────────────────────────────────────────────────
  훅은 **조용히 죽는다.** 경로가 바뀌거나 JSON 스키마가 달라지거나 인코딩이 깨지면
  차단해야 할 것을 통과시키면서 아무 말도 안 한다.
  그 상태로 몇 세션이 지나면 "방어선이 있다"고 믿는 채로 방어선이 없다.

  이 저장소에서 그 대가는 크다 — `guard_handson` 이 죽으면 **대필이 그냥 통과한다.**
  그러면 이 프로젝트의 목적 자체가 사라진다 (§5-T).

  ⚠ 시험 방법 — 가짜 도구 호출 JSON 을 만들어 훅에 먹이고 종료코드를 본다
      exit 0 = 통과시킴 / exit 2 = 차단함

  사용:
      .claude\hooks\selftest.ps1          전체 (임시 git 저장소로 관문·자동 푸시·자동 받기까지 — 수십 초)
      .claude\hooks\selftest.ps1 -Quick   핵심만 (SessionStart 에서 자동 호출)
#>

param([switch]$Quick)

$ErrorActionPreference = 'Continue'

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
$root = Split-Path -Parent (Split-Path -Parent $startDir)

$pass = 0
$fail = 0
$failMsgs = New-Object System.Collections.Generic.List[string]

function Invoke-Hook {
    <# 훅에 JSON 을 먹이고 종료코드를 돌려준다 #>
    param([string]$HookName, [hashtable]$Payload)

    $hookPath = Join-Path $startDir $HookName
    if (-not (Test-Path -LiteralPath $hookPath)) { return 999 }

    $json = $Payload | ConvertTo-Json -Depth 8 -Compress
    $tmp = [System.IO.Path]::GetTempFileName()
    try {
        [System.IO.File]::WriteAllText($tmp, $json, (New-Object System.Text.UTF8Encoding($false)))

        # ⚠⚠ 2026-09-10 에 실제로 틀렸던 부분이다.
        #   처음엔 `powershell -Command "... | & '$hookPath'"` 로 불렀는데,
        #   그러면 훅 안의 `exit 2` 는 **호출된 스크립트만** 끝내고
        #   바깥 powershell.exe 는 0 을 돌려준다.
        #   → 자가 시험이 "전부 통과"라고 보고했고, **차단 훅 5개가 죽은 줄 몰랐다.**
        #   반드시 `-File` 로 부르고 stdin 을 파이프로 넣어 프로세스 종료코드를 받는다.
        $null = Get-Content -LiteralPath $tmp -Raw |
                & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $hookPath 2>&1
        return $LASTEXITCODE
    } catch {
        return 998
    } finally {
        Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
    }
}

function Check {
    param([string]$Name, [int]$Actual, [int]$Expected)
    if ($Actual -eq $Expected) {
        $script:pass++
    } else {
        $script:fail++
        $verdictA = if ($Actual -eq 2) { '차단' } elseif ($Actual -eq 0) { '통과' } else { "오류($Actual)" }
        $verdictE = if ($Expected -eq 2) { '차단' } else { '통과' }
        $script:failMsgs.Add("  ⛔ $Name — 기대: $verdictE / 실제: $verdictA")
    }
}

# ═══════════════════════════════════════════════════════════════════════════
#  guard_handson — 이 저장소의 제1 방어선 (§5-T)
# ═══════════════════════════════════════════════════════════════════════════

# ① TODO 를 채우는 Edit → 차단해야 한다
Check "handson: TODO 채우는 Edit" (Invoke-Hook 'guard_handson.ps1' @{
    tool_name  = 'Edit'
    tool_input = @{
        file_path  = "$root\src\raglab\retrieval.py"
        old_string = "    raise NotImplementedError('Stage 3')"
        new_string = "    norms = np.linalg.norm(mat, axis=1)`n    return mat @ q / norms"
    }
}) 2

# ② NotImplementedError 없이 로직 대량 유입 → 차단해야 한다
Check "handson: 로직 대량 삽입" (Invoke-Hook 'guard_handson.ps1' @{
    tool_name  = 'Edit'
    tool_input = @{
        file_path  = "$root\src\raglab\retrieval.py"
        old_string = "# placeholder"
        new_string = "a = 1`nb = 2`nc = a + b`nd = c * 2`ne = d - 1`nf = e / 2`ng = f + 1"
    }
}) 2

# ③ 뼈대 생성(시그니처 + 독스트링 + TODO) → 통과해야 한다
Check "handson: 뼈대 생성 허용" (Invoke-Hook 'guard_handson.ps1' @{
    tool_name  = 'Write'
    tool_input = @{
        file_path = "$root\src\raglab\__probe_selftest.py"
        content   = "def f(x: int) -> int:`n    `"`"`"왜 이렇게 하는가.`"`"`"`n    raise NotImplementedError('Stage 9')"
    }
}) 0

# ④ 보호 대상 밖(labkit) → 통과해야 한다
Check "handson: labkit 은 대상 아님" (Invoke-Hook 'guard_handson.ps1' @{
    tool_name  = 'Edit'
    tool_input = @{
        file_path  = "$root\src\labkit\corpus.py"
        old_string = "x"
        new_string = "a = 1`nb = 2`nc = 3`nd = 4`ne = 5`nf = 6`ng = 7`nh = 8"
    }
}) 0

# ⑤ 테스트 파일 → 통과해야 한다 (명세를 주는 것은 대필이 아니다)
Check "handson: tests 는 대상 아님" (Invoke-Hook 'guard_handson.ps1' @{
    tool_name  = 'Write'
    tool_input = @{
        file_path = "$root\tests\test_probe.py"
        content   = "def test_x():`n    assert 1 == 1`n    assert 2 == 2`n    assert 3 == 3`n    assert 4 == 4`n    assert 5 == 5`n    assert 6 == 6`n    assert 7 == 7"
    }
}) 0

if ($Quick) {
    # ═══ 빠른 시험은 제1 방어선만 본다 ═══
    $head = "[selftest] guard_handson $pass/$($pass + $fail) 통과"
    if ($fail -gt 0) {
        Write-Output ($head + "  ⛔ 방어선에 구멍이 있습니다")
        Write-Output ($failMsgs -join "`n")
        Write-Output "  ⚠⚠ 이 상태에서는 대필이 그냥 통과합니다. 고치기 전에 학습을 진행하지 마십시오 (§5-T)."
    } else {
        Write-Output $head
    }
    exit 0
}

# ═══════════════════════════════════════════════════════════════════════════
#  guard_spoiler — 아직 안 푼 단계의 정답 열람 (§3)
# ═══════════════════════════════════════════════════════════════════════════

Check "spoiler: 미완료 단계 정답 읽기" (Invoke-Hook 'guard_spoiler.ps1' @{
    tool_name  = 'Read'
    tool_input = @{ file_path = "$root\solutions\stage03_retrieval.py" }
}) 2

Check "spoiler: Bash 로 우회 열람" (Invoke-Hook 'guard_spoiler.ps1' @{
    tool_name  = 'Bash'
    tool_input = @{ command = "cat solutions/stage04_hybrid.py" }
}) 2

Check "spoiler: 무관한 파일" (Invoke-Hook 'guard_spoiler.ps1' @{
    tool_name  = 'Read'
    tool_input = @{ file_path = "$root\tests\test_stage03_retrieval.py" }
}) 0

# ═══════════════════════════════════════════════════════════════════════════
#  guard_claim — 규격 미달 산출물 (§3-S · §8)
# ═══════════════════════════════════════════════════════════════════════════

$probeHtml = Join-Path $root 'outputs\__probe_selftest.html'
try {
    Set-Content -LiteralPath $probeHtml -Value "<html><body>Recall 0.9</body></html>" -Encoding UTF8
    Check "claim: 합성·한계 표기 없는 산출물" (Invoke-Hook 'guard_claim.ps1' @{
        tool_name  = 'SendUserFile'
        tool_input = @{ files = @($probeHtml) }
    }) 2

    Set-Content -LiteralPath $probeHtml -Value "<html><body>합성 데이터입니다. <h2>한계</h2></body></html>" -Encoding UTF8
    Check "claim: 표기 갖춘 산출물" (Invoke-Hook 'guard_claim.ps1' @{
        tool_name  = 'SendUserFile'
        tool_input = @{ files = @($probeHtml) }
    }) 0
} finally {
    Remove-Item -LiteralPath $probeHtml -Force -ErrorAction SilentlyContinue
}

# ═══════════════════════════════════════════════════════════════════════════
#  guard_review — 밀린 복습이 있으면 새 단계를 막는가 (§14)
# ═══════════════════════════════════════════════════════════════════════════

# ⚠⚠ 카드가 0장이면 게이트는 늘 열려 있다. 그 상태로는 이 훅이 한 번도 안 돌고,
#    그러면 「방어선이 있다」고 믿는 채로 방어선이 없다.
#    그래서 **가짜 세션 파일을 주입해** blocked 상태를 만들어 시험한다.

$sessPath = Join-Path $root '.claude\state\review_session.json'
$sessBak  = $null
if (Test-Path -LiteralPath $sessPath) {
    $sessBak = Get-Content -LiteralPath $sessPath -Raw -Encoding UTF8
}

function Set-Gate([string]$Gate) {
    $obj = [ordered]@{
        computed_at   = (Get-Date).ToString('s')
        gap_days      = 3
        due_total     = 2
        cards         = @('s99-probe_a', 's99-probe_b')
        deferred      = 0
        revisit_stage = $null
        skipping      = $false
        skip_until    = $null
        gate          = $Gate
        reviewed      = @()
    }
    $json = $obj | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText($sessPath, $json, (New-Object System.Text.UTF8Encoding($false)))
}

try {
    Set-Gate 'blocked'

    # ① 새 단계를 여는 정문 → 차단
    Check "review: 밀린 복습 중 next-step" (Invoke-Hook 'guard_review.ps1' @{
        tool_name  = 'Skill'
        tool_input = @{ skill = 'next-step' }
    }) 2

    # ② 새 단계 강의 집필 → 차단
    Check "review: 밀린 복습 중 새 단계 강의" (Invoke-Hook 'guard_review.ps1' @{
        tool_name  = 'Write'
        tool_input = @{ file_path = "$root\docs\stages\07-graph.md"; content = 'x' }
    }) 2

    # ③ 새 단계 테스트 작성 → 차단
    Check "review: 밀린 복습 중 새 단계 테스트" (Invoke-Hook 'guard_review.ps1' @{
        tool_name  = 'Write'
        tool_input = @{ file_path = "$root\tests\test_stage07_graph.py"; content = 'x' }
    }) 2

    # ④ 진도 전진 → 차단
    Check "review: 밀린 복습 중 진도 전진" (Invoke-Hook 'guard_review.ps1' @{
        tool_name  = 'Edit'
        tool_input = @{ file_path = "$root\.claude\state\progress.json"; old_string = 'a'; new_string = 'b' }
    }) 2

    # ⑤ ⚠⚠ 데드락 방지 — 복습 자체로 가는 길은 열려 있어야 한다
    Check "review: 복습 스킬은 통과" (Invoke-Hook 'guard_review.ps1' @{
        tool_name  = 'Skill'
        tool_input = @{ skill = 'review' }
    }) 0

    Check "review: 복습 상태 파일은 통과" (Invoke-Hook 'guard_review.ps1' @{
        tool_name  = 'Write'
        tool_input = @{ file_path = "$root\.claude\state\review.json"; content = 'x' }
    }) 0

    Check "review: PROGRESS.md 기록은 통과" (Invoke-Hook 'guard_review.ps1' @{
        tool_name  = 'Write'
        tool_input = @{ file_path = "$root\docs\PROGRESS.md"; content = 'x' }
    }) 0

    Check "review: 무관한 파일은 통과" (Invoke-Hook 'guard_review.ps1' @{
        tool_name  = 'Write'
        tool_input = @{ file_path = "$root\README.md"; content = 'x' }
    }) 0

    # ⑤-2 ⚠⚠ 데드락 방지 — 복습의 코드 카드는 src/raglab/ 의 **기존 파일**을 되돌린다.
    #      그걸 막으면 게이트가 자기를 여는 유일한 길을 막는 것이 된다.
    Check "review: raglab 기존 파일은 통과 (코드 카드)" (Invoke-Hook 'guard_review.ps1' @{
        tool_name  = 'Edit'
        tool_input = @{
            file_path  = "$root\src\raglab\chunking.py"
            old_string = 'a'
            new_string = 'b'
        }
    }) 0

    # ⑤-3 단, 아직 없는 파일을 만드는 것은 새 단계 작업대다 → 차단
    Check "review: raglab 새 파일은 차단 (새 단계)" (Invoke-Hook 'guard_review.ps1' @{
        tool_name  = 'Write'
        tool_input = @{ file_path = "$root\src\raglab\graph.py"; content = 'x' }
    }) 2

    # ⑥ 게이트가 열리면 전부 통과해야 한다 — 오탐으로 영원히 막는 것이 최악이다
    Set-Gate 'open'

    Check "review: 게이트 열리면 next-step 통과" (Invoke-Hook 'guard_review.ps1' @{
        tool_name  = 'Skill'
        tool_input = @{ skill = 'next-step' }
    }) 0

    Check "review: 게이트 열리면 강의 집필 통과" (Invoke-Hook 'guard_review.ps1' @{
        tool_name  = 'Write'
        tool_input = @{ file_path = "$root\docs\stages\07-graph.md"; content = 'x' }
    }) 0
}
finally {
    if ($null -ne $sessBak) {
        [System.IO.File]::WriteAllText($sessPath, $sessBak, (New-Object System.Text.UTF8Encoding($false)))
    } else {
        Remove-Item -LiteralPath $sessPath -Force -ErrorAction SilentlyContinue
    }
}

# ═══════════════════════════════════════════════════════════════════════════
#  guard_sync — 원격과 어긋났을 때 새 단계를 막는가 (§15)
# ═══════════════════════════════════════════════════════════════════════════

# ⚠⚠ 실제로 behind 상태를 만들려면 원격을 건드려야 한다. 그건 시험이 아니라 사고다.
#    그래서 **가짜 판정 파일을 주입해** 상태만 흉내 낸다 (guard_review 와 같은 방식).

$syncPath = Join-Path $root '.claude\state\sync_session.json'
$syncBak  = $null
if (Test-Path -LiteralPath $syncPath) {
    $syncBak = Get-Content -LiteralPath $syncPath -Raw -Encoding UTF8
}

function Set-Sync([string]$State, [int]$Behind, [int]$Ahead) {
    $obj = [ordered]@{
        computed_at = (Get-Date).ToString('s')
        branch      = 'main'
        upstream    = 'origin/main'
        behind      = $Behind
        ahead       = $Ahead
        fetch_ok    = $true
        state       = $State
    }
    $json = $obj | ConvertTo-Json -Depth 6
    [System.IO.File]::WriteAllText($syncPath, $json, (New-Object System.Text.UTF8Encoding($false)))
}

try {
    # ── behind: 다른 PC 작업을 아직 안 받았다 → 새 단계 차단 ────────────────
    Set-Sync 'behind' 3 0

    Check "sync: behind 상태에서 next-step" (Invoke-Hook 'guard_sync.ps1' @{
        tool_name  = 'Skill'
        tool_input = @{ skill = 'next-step' }
    }) 2

    Check "sync: behind 상태에서 진도 전진" (Invoke-Hook 'guard_sync.ps1' @{
        tool_name  = 'Edit'
        tool_input = @{ file_path = "$root\.claude\state\progress.json"; old_string = 'a'; new_string = 'b' }
    }) 2

    # ⚠⚠ 데드락 방지 — 복습과 기록은 막히면 안 된다
    Check "sync: behind 여도 복습 스킬은 통과" (Invoke-Hook 'guard_sync.ps1' @{
        tool_name  = 'Skill'
        tool_input = @{ skill = 'review' }
    }) 0

    Check "sync: behind 여도 PROGRESS.md 는 통과" (Invoke-Hook 'guard_sync.ps1' @{
        tool_name  = 'Write'
        tool_input = @{ file_path = "$root\docs\PROGRESS.md"; content = 'x' }
    }) 0

    # ── diverged: 이력이 갈라졌다 → 차단 ────────────────────────────────────
    Set-Sync 'diverged' 2 1

    Check "sync: diverged 상태에서 새 단계 강의" (Invoke-Hook 'guard_sync.ps1' @{
        tool_name  = 'Write'
        tool_input = @{ file_path = "$root\docs\stages\07-graph.md"; content = 'x' }
    }) 2

    # ── ahead: 푸시만 안 됐다 → **막지 않는다** ─────────────────────────────
    # 떠나기 전에 할 일이지 지금 막을 일이 아니다. 여기서 막으면 작업 자체가 안 된다.
    Set-Sync 'ahead' 0 4

    Check "sync: ahead 는 막지 않는다" (Invoke-Hook 'guard_sync.ps1' @{
        tool_name  = 'Skill'
        tool_input = @{ skill = 'next-step' }
    }) 0

    # ── clean: 통과 ─────────────────────────────────────────────────────────
    Set-Sync 'clean' 0 0

    Check "sync: clean 은 통과" (Invoke-Hook 'guard_sync.ps1' @{
        tool_name  = 'Write'
        tool_input = @{ file_path = "$root\docs\stages\07-graph.md"; content = 'x' }
    }) 0
}
finally {
    if ($null -ne $syncBak) {
        [System.IO.File]::WriteAllText($syncPath, $syncBak, (New-Object System.Text.UTF8Encoding($false)))
    } else {
        Remove-Item -LiteralPath $syncPath -Force -ErrorAction SilentlyContinue
    }
}

# ⚠ 판정 파일이 아예 없을 때는 fail-open 이어야 한다 (오프라인·훅 미실행)
$syncSaved = $null
if (Test-Path -LiteralPath $syncPath) {
    $syncSaved = Get-Content -LiteralPath $syncPath -Raw -Encoding UTF8
    Remove-Item -LiteralPath $syncPath -Force -ErrorAction SilentlyContinue
}
try {
    Check "sync: 판정 없으면 통과 (fail-open)" (Invoke-Hook 'guard_sync.ps1' @{
        tool_name  = 'Skill'
        tool_input = @{ skill = 'next-step' }
    }) 0
}
finally {
    if ($null -ne $syncSaved) {
        [System.IO.File]::WriteAllText($syncPath, $syncSaved, (New-Object System.Text.UTF8Encoding($false)))
    }
}

# ═══════════════════════════════════════════════════════════════════════════

#  샌드박스 — 임시 git 저장소로 **실제 동작**을 본다 (2026-09-11 추가, §15-3 · §15-5 · §15-6)
# ═══════════════════════════════════════════════════════════════════════════
#
# ⚠⚠ 원격을 건드리는 시험을 실제 저장소에서 하면 그건 시험이 아니라 사고다.
#    임시 폴더에 bare 원격 + 클론을 만들어 거기서만 하고, 끝나면 통째로 지운다.
# ⚠⚠ 훅을 부를 때 CLAUDE_PROJECT_DIR 을 반드시 샌드박스로 바꾼다 — 안 그러면 훅이
#    **실제 저장소**를 루트로 잡고, sync_check 의 자동 받기가 실제 저장소에서 돈다.
# ⚠ 가짜 개인정보는 전부 **조립**한다. 글자 그대로 적으면 이 파일을 커밋할 때 관문에 걸린다.
# ⚠ git 인자는 배열로 넘긴다 — PowerShell 이 `-d`·`--hard` 를 함수 매개변수로 오인하지 않게.

function CheckBool {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    if ($Ok) {
        $script:pass++
    } else {
        $script:fail++
        $d = ''
        if ($Detail) { $d = ' — ' + (($Detail -split "`n" | Where-Object { $_.Trim() } | Select-Object -First 3) -join ' / ') }
        $script:failMsgs.Add("  ⛔ $Name$d")
    }
}

$sandbox   = Join-Path ([System.IO.Path]::GetTempPath()) ('lab-selftest-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
$remote    = Join-Path $sandbox 'remote.git'
$realHooks = (Join-Path $root '.githooks').Replace('\', '/')
$realPy    = Join-Path $root '.venv\Scripts\python.exe'
$at        = '@'
$fakeMail  = 'some.one' + $at + 'gmail' + '.com'
$okMail    = 'selftest' + $at + 'example.invalid'
$savedProjectDir = $env:CLAUDE_PROJECT_DIR
$savedLabPy      = $env:LAB_PYTHON
$script:gitOut   = ''

function G([string]$Dir, [string[]]$A) {
    $script:gitOut = (& git -C $Dir @A 2>&1 | Out-String)
    return $LASTEXITCODE
}
function GOut([string]$Dir, [string[]]$A) {
    return ((& git -C $Dir @A 2>$null | Out-String).Trim())
}
function New-Clone([string]$Name) {
    $d = Join-Path $sandbox $Name
    $null = & git clone --quiet $remote $d 2>&1
    $null = G $d @('config', 'user.name', 'selftest')
    $null = G $d @('config', 'user.email', $okMail)
    return $d
}
function Add-Commit([string]$Dir, [string]$File, [string]$Content, [string]$Msg) {
    [System.IO.File]::WriteAllText((Join-Path $Dir $File), $Content, (New-Object System.Text.UTF8Encoding($false)))
    $null = G $Dir @('add', '--', $File)
    return (G $Dir @('commit', '--quiet', '-m', $Msg))
}
function CommitCount([string]$Dir) { return [int](GOut $Dir @('rev-list', '--count', 'HEAD')) }
function HeadOf([string]$Dir) { return (GOut $Dir @('rev-parse', 'HEAD')) }
function RemoteHead { return (GOut $remote @('rev-parse', 'main')) }
function Invoke-Ps([string]$Script, [string]$StdIn = '') {
    if ($StdIn) {
        return ($StdIn | & powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $Script 2>&1 | Out-String)
    }
    return (& powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $Script 2>&1 | Out-String)
}

try {
    New-Item -ItemType Directory -Path $sandbox -Force | Out-Null
    $null = & git init --quiet --bare --initial-branch=main $remote 2>&1
    $a = New-Clone 'a'
    $null = Add-Commit $a 'README.md' "seed`n" 'seed'
    $null = G $a @('push', '--quiet', '-u', 'origin', 'main')

    # ── 개인정보 관문 — 규칙 단위 ─────────────────────────────────────────────
    $unit = (& $realPy (Join-Path $root '.githooks\privacy_scan.py') selftest 2>&1 | Out-String)
    CheckBool "privacy: 규칙 단위 시험 (privacy_scan.py selftest)" ($LASTEXITCODE -eq 0) $unit

    # ── 개인정보 관문 + 자동 푸시 — 실제 git 훅으로 ──────────────────────────
    $null = G $a @('config', 'core.hooksPath', $realHooks)

    $n0 = CommitCount $a
    $null = Add-Commit $a 'ok.md' "한빛텔레콤 LTE-S-33 요금제`n" 'docs: clean'
    CheckBool "privacy: 깨끗한 커밋은 통과" ((CommitCount $a) -eq ($n0 + 1)) $script:gitOut
    CheckBool "auto-push: 커밋하자마자 원격에 올라감" ((RemoteHead) -eq (HeadOf $a)) $script:gitOut

    $leaks = @(
        @{ n = '이메일';          v = ('연락 ' + $fakeMail) },
        @{ n = 'GitHub 토큰';     v = ('token=ghp_' + ('A1b2' * 9)) },
        @{ n = '이 PC 계정 경로'; v = ('C:' + '\Users\' + $env:USERNAME + '\AppData') },
        @{ n = '계좌번호';        v = ('입금 110' + '-123-' + '456789') },
        @{ n = '비밀번호 대입';   v = ('password=' + 'hunter22') }
    )
    foreach ($lk in $leaks) {
        $n0 = CommitCount $a
        $null = Add-Commit $a 'leak.md' ($lk.v + "`n") 'docs: leak'
        CheckBool "privacy: $($lk.n) 든 커밋은 차단" ((CommitCount $a) -eq $n0) $script:gitOut
        $null = G $a @('reset', '--quiet', '--hard', 'HEAD')
    }

    $n0 = CommitCount $a
    $null = Add-Commit $a 'ok2.md' "x`n" ('docs: 문의 ' + $fakeMail)
    CheckBool "privacy: 커밋 메시지의 이메일은 차단 (commit-msg)" ((CommitCount $a) -eq $n0) $script:gitOut
    $null = G $a @('reset', '--quiet', '--hard', 'HEAD')

    # ⭐ 내 커밋 이메일은 막지 않는다 — 신원으로도, 본문에 있어도 (사용자 결정 2026-09-11)
    #    남의 이메일은 여전히 막는다
    $null = G $a @('config', 'user.email', $fakeMail)
    $n0 = CommitCount $a
    $null = Add-Commit $a 'me.md' ('연락처 ' + $fakeMail + "`n") 'docs: my contact'
    CheckBool "privacy: 내 커밋 이메일은 신원·본문 모두 통과 (사용자 결정)" ((CommitCount $a) -eq ($n0 + 1)) $script:gitOut
    $n0 = CommitCount $a
    $null = Add-Commit $a 'other.md' ('연락처 other.person' + $at + 'gmail' + '.com' + "`n") 'docs: other contact'
    CheckBool "privacy: 남의 이메일은 여전히 차단" ((CommitCount $a) -eq $n0) $script:gitOut
    $null = G $a @('reset', '--quiet', '--hard', 'HEAD')
    $null = G $a @('config', 'user.email', $okMail)

    # ⚠⚠ 두 번째 방어선 — 훅을 켜기 전에 만든 커밋도 푸시에서 걸려야 한다
    $null = G $a @('config', '--unset', 'core.hooksPath')
    $null = Add-Commit $a 'old.md' ('token=ghp_' + ('Z9y8' * 9) + "`n") 'docs: before hooks'
    $null = G $a @('config', 'core.hooksPath', $realHooks)
    $before = RemoteHead
    $rc = G $a @('push', '--quiet')
    CheckBool "privacy: 훅 켜기 전 커밋도 pre-push 가 차단" (($rc -ne 0) -and ((RemoteHead) -eq $before)) $script:gitOut
    $null = G $a @('reset', '--quiet', '--hard', '@{u}')

    # 자동 푸시 끄기 스위치 — 검사는 하되 올리지 않는다
    $null = G $a @('config', 'lab.autopush', 'false')
    $before = RemoteHead
    $null = Add-Commit $a 'ok4.md' "x`n" 'docs: autopush off'
    CheckBool "auto-push: lab.autopush=false 면 올리지 않음" (((RemoteHead) -eq $before) -and ((HeadOf $a) -ne $before)) $script:gitOut
    $null = G $a @('config', '--unset', 'lab.autopush')
    $null = G $a @('push', '--quiet')

    # 실제 사용 형태 — 상대경로 hooksPath(.githooks). 훅 폴더를 복사해 $0 해석을 본다
    Copy-Item -LiteralPath (Join-Path $root '.githooks') -Destination (Join-Path $a '.githooks') -Recurse
    $null = G $a @('config', 'core.hooksPath', '.githooks')
    $env:LAB_PYTHON = $realPy.Replace('\', '/')
    $n0 = CommitCount $a
    $null = Add-Commit $a 'leak2.md' ('연락 ' + $fakeMail + "`n") 'docs: leak rel'
    CheckBool "privacy: 상대경로 hooksPath 에서도 차단" ((CommitCount $a) -eq $n0) $script:gitOut
    $null = G $a @('reset', '--quiet', '--hard', 'HEAD')
    $n0 = CommitCount $a
    $null = Add-Commit $a 'ok5.md' "x`n" 'docs: clean rel'
    CheckBool "privacy: 상대경로 hooksPath 에서 깨끗한 커밋 통과" ((CommitCount $a) -eq ($n0 + 1)) $script:gitOut
    $env:LAB_PYTHON = $savedLabPy
    $null = G $a @('config', 'core.hooksPath', $realHooks)

    # ── sync_check 자동 받기 (§15-3) ────────────────────────────────────────
    $b = New-Clone 'b'
    $bHooks = Join-Path $b '.claude\hooks'
    New-Item -ItemType Directory -Path $bHooks -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $b '.claude\state') -Force | Out-Null
    Copy-Item -Path (Join-Path $startDir '*.ps1') -Destination $bHooks
    $bSync  = Join-Path $bHooks 'sync_check.ps1'
    $bState = Join-Path $b '.claude\state\sync_session.json'
    $env:CLAUDE_PROJECT_DIR = $b

    $null = Add-Commit $a 'from-a.md' "x`n" 'docs: from a'
    $out = Invoke-Ps $bSync
    $st = Get-Content -LiteralPath $bState -Raw -Encoding UTF8 | ConvertFrom-Json
    CheckBool "sync: behind·깨끗하면 자동으로 받는다 (ff-only)" (((HeadOf $b) -eq (RemoteHead)) -and ($st.state -eq 'clean') -and ([int]$st.pulled -ge 1)) $out

    $null = Add-Commit $a 'from-a2.md' "x`n" 'docs: from a 2'
    Add-Content -LiteralPath (Join-Path $b 'README.md') -Value 'local edit'
    $headB = HeadOf $b
    $out = Invoke-Ps $bSync
    $st = Get-Content -LiteralPath $bState -Raw -Encoding UTF8 | ConvertFrom-Json
    CheckBool "sync: 미커밋 변경이 있으면 받지 않는다" (((HeadOf $b) -eq $headB) -and ($st.state -eq 'behind') -and ([int]$st.dirty -ge 1)) $out
    $null = G $b @('checkout', '--', 'README.md')

    $null = Add-Commit $b 'from-b.md' "x`n" 'docs: from b'
    $headB = HeadOf $b
    $out = Invoke-Ps $bSync
    $st = Get-Content -LiteralPath $bState -Raw -Encoding UTF8 | ConvertFrom-Json
    CheckBool "sync: 갈라지면 자동으로 합치지 않는다" (((HeadOf $b) -eq $headB) -and ($st.state -eq 'diverged')) $out

    # ── 떠나기 전 점검 (§15-6) ──────────────────────────────────────────────
    $bLeave      = Join-Path $bHooks 'leave_check.ps1'
    $bLeaveState = Join-Path $b '.claude\state\leave_session.json'
    $null = G $b @('fetch', '--quiet')
    $null = G $b @('reset', '--quiet', '--hard', '@{u}')
    Remove-Item -LiteralPath $bLeaveState -Force -ErrorAction SilentlyContinue

    $out = Invoke-Ps $bLeave '{}'
    CheckBool "leave: 깨끗하면 조용하다" (-not ($out -match 'systemMessage')) $out
    Add-Content -LiteralPath (Join-Path $b 'README.md') -Value 'wip'
    $out = Invoke-Ps $bLeave '{}'
    CheckBool "leave: 미커밋이 있으면 알린다" ($out -match 'systemMessage') $out
    $out = Invoke-Ps $bLeave '{}'
    CheckBool "leave: 같은 상태면 곧바로 다시 알리지 않는다 (소음 방지)" (-not ($out -match 'systemMessage')) $out
    $null = G $b @('commit', '--quiet', '-am', 'wip')
    $out = Invoke-Ps $bLeave '{}'
    CheckBool "leave: 올라가지 않은 커밋이 생기면 곧바로 알린다" ($out -match 'systemMessage') $out
    Remove-Item -LiteralPath $bLeaveState -Force -ErrorAction SilentlyContinue
    $out = Invoke-Ps $bLeave '{"stop_hook_active":true}'
    CheckBool "leave: stop_hook_active 면 아무것도 안 한다 (반복 방지)" (-not ($out -match 'systemMessage')) $out

    # 관문을 켠 PC 면 「커밋하면 자동으로 올라간다」고 안내해야 한다
    # (2026-09-11: `[string](& git ...)` 이 $null 이라 이 분기가 조용히 죽어 있었다 — §6 지뢰 14)
    $null = G $b @('reset', '--quiet', '--hard', '@{u}')
    $null = G $b @('config', 'core.hooksPath', $realHooks)
    Remove-Item -LiteralPath $bLeaveState -Force -ErrorAction SilentlyContinue
    Add-Content -LiteralPath (Join-Path $b 'README.md') -Value 'wip2'
    $out = Invoke-Ps $bLeave '{}'
    $msg = ''
    try { $msg = [string](($out | ConvertFrom-Json).systemMessage) } catch { }
    CheckBool "leave: 관문을 켠 PC 면 「커밋하면 자동으로 올라간다」고 안내" ($msg -match '자동으로') $out
}
finally {
    $env:CLAUDE_PROJECT_DIR = $savedProjectDir
    $env:LAB_PYTHON = $savedLabPy
    Remove-Item -LiteralPath $sandbox -Recurse -Force -ErrorAction SilentlyContinue
}

# ═══════════════════════════════════════════════════════════════════════════

$total = $pass + $fail
Write-Output "[selftest] $pass/$total 통과"
if ($fail -gt 0) {
    Write-Output ($failMsgs -join "`n")
    Write-Output ""
    Write-Output "⚠⚠ 침묵하는 방어선은 없는 방어선보다 나쁩니다. 고치기 전에 학습을 진행하지 마십시오."
    exit 1
}
exit 0
