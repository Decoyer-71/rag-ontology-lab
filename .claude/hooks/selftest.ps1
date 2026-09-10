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
      .claude\hooks\selftest.ps1          전체
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

$total = $pass + $fail
Write-Output "[selftest] $pass/$total 통과"
if ($fail -gt 0) {
    Write-Output ($failMsgs -join "`n")
    Write-Output ""
    Write-Output "⚠⚠ 침묵하는 방어선은 없는 방어선보다 나쁩니다. 고치기 전에 학습을 진행하지 마십시오."
    exit 1
}
exit 0
