# -*- coding: utf-8 -*-
<#
  SessionStart 훅 — **순서가 곧 정확성인 세션 시작 작업을 한 줄로 세운다.** (CLAUDE.md §14-5 · §15-3)

  ⚠⚠ 왜 하나로 묶는가
  ─────────────────────────────────────────────────────────────────────────────
  Claude Code 는 같은 이벤트에 걸린 훅을 **병렬로** 돌린다 — settings.json 에 적은 순서는
  실행 순서가 아니다 (공식 hooks 문서 · 2026-09-11 세션 출력 순서가 등록 순서와 달랐던 것으로도 확인).
  그런데 아래 넷은 앞 단계의 결과를 읽는다:

    ① sync_check      원격 확인 · 안전하면 fast-forward 로 받는다   ← 다른 PC 의 작업이 여기서 들어온다
    ② session_banner  진도 배너                                     ← ①이 받은 progress.json
    ③ commit_watch    마지막 학습 커밋 따라잡기                     ← ①이 받은 커밋
    ④ review_due      공백기간 · 복습 카드 · 게이트                  ← ①이 받은 review.json + ③의 기록

  병렬이면 ④가 **다른 PC 에서 이미 푼 카드를 다시 배정**할 수 있다. 그러면 두 PC 가 같은 카드의
  history 를 따로 쓰고, 그건 §15-1 이 「합칠 수 없다」고 한 충돌이다.

  ⚠ preflight · selftest -Quick 는 여기 넣지 않는다 — 원격·상태 파일과 무관해 병렬이 낫다.
     전부 순차로 돌리면 세션 시작이 약 10초 늘어난다
     (2026-09-11 노트북 실측: 여섯 스크립트 순차 합 18.8초 vs 병렬 최대 8.5초).

  ⚠ 각 단계는 **같은 프로세스에서** 부른다 — 단계마다 powershell 을 새로 띄우면 1초씩 더 든다.
     단계 안의 `exit` 는 그 스크립트만 끝내고 여기로 돌아온다 (selftest.ps1 의 Invoke-Hook 주석 참고).

  ⚠⚠ fail-open — 한 단계가 죽어도 다음 단계는 돈다. 세션 시작을 막지 않는다.
#>

$ErrorActionPreference = 'Continue'

try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8NoBom
    $OutputEncoding = $utf8NoBom
} catch { }

$startDir = $PSScriptRoot
if (-not $startDir) { try { $startDir = Split-Path -Parent $MyInvocation.MyCommand.Path } catch {} }

foreach ($step in @('sync_check.ps1', 'session_banner.ps1', 'commit_watch.ps1', 'review_due.ps1')) {
    $p = Join-Path $startDir $step
    if (-not (Test-Path -LiteralPath $p)) {
        Write-Output "[session] ⚠ $step 가 없어 건너뜁니다"
        continue
    }
    try {
        & $p
    } catch {
        Write-Output "[session] ⚠ $step 실패 — $($_.Exception.Message). 다음 단계로 넘어갑니다"
    }
}

exit 0
