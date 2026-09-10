# -*- coding: utf-8 -*-
<#
  SessionStart 훅 — **지금 어디까지 왔는지**를 세션 첫머리에 박아 둔다. (CLAUDE.md §7-0)

  ⚠ 왜 필요한가
  ─────────────────────────────────────────────────────────────────────────────
  이 프로젝트는 **여러 세션에 걸쳐** 진행된다. 진도를 안 읽고 시작하면
  이미 끝난 단계를 다시 설명하거나, 아직 안 배운 개념을 전제로 말하게 된다.
  컨텍스트는 요약되면 사라지지만 `progress.json` 은 남는다.

  ⚠ 출력은 stdout 으로 나가고 세션 컨텍스트에 들어간다. **짧게 유지한다.**
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
    Write-Output "[rag-ontology-lab] ⚠ 저장소 루트를 못 찾았습니다. 훅이 제 기능을 못 합니다."
    exit 0
}

$prog = $null
try { $prog = Get-Progress -Root $root } catch { }

$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("=== rag-ontology-lab · RAG·온톨로지 실습실 ===")

if (-not $prog) {
    $lines.Add("⚠ .claude/state/progress.json 을 못 읽었습니다. 진도 확인 불가.")
} else {
    $cur = 0
    try { $cur = [int]$prog.current_stage } catch { }
    $title = ''
    try { $title = [string]$prog.current_title } catch { }
    $done = @()
    try { $done = @($prog.completed_stages) } catch { }
    $total = 12
    try { if ($prog.total_stages) { $total = [int]$prog.total_stages } } catch { }

    $lines.Add("진도  : Stage $cur / $($total - 1)  ($($done.Count)개 완료)")
    if ($title) { $lines.Add("현재  : $title") }

    $assume = $false
    try { $assume = [bool]$prog.assumptions_unconfirmed } catch { }
    if ($assume) {
        $lines.Add("")
        $lines.Add("⚠⚠ CLAUDE.md §0-2 미확정 가정 3건이 아직 확인되지 않았습니다.")
        $lines.Add("   새 세션 첫 턴 과업 — 코퍼스 도메인 / 실습 강도 / Stage 9 조달 시점.")
        $lines.Add("   확인 전까지 이 가정들을 「사용자가 정한 것」처럼 말하지 마십시오.")
    }
}

$lines.Add("")
$lines.Add("규율 요약 — 전문은 CLAUDE.md")
$lines.Add("  §5-T  src/raglab/ 의 알고리즘 본체는 **사용자가 직접 씁니다.** Claude 는 뼈대·테스트·힌트까지")
$lines.Add("  §3    테스트 통과 ≠ 이해. checkpoint 로 「왜」를 확인해야 단계가 닫힙니다")
$lines.Add("  §5-D' 개선은 기준선 수치와 **나란히** 보고합니다")
$lines.Add("  §3-S  data/synthetic/ 은 전부 합성입니다. 산출물에 배너로 표기")
$lines.Add("  §7-8  사용자 응답은 존댓말")
$lines.Add("")
$lines.Add("파이썬 : .venv/Scripts/python.exe  (⚠ 시스템 python 은 MS Store 스텁)")

Write-Output ($lines -join "`n")
exit 0
