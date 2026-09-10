# -*- coding: utf-8 -*-
<#
  PreToolUse 훅 — **아직 안 푼 단계의 정답 열람을 막는다.** (CLAUDE.md §5-T · §3-5)

  ⚠⚠ 왜 이 훅이 있는가
  ─────────────────────────────────────────────────────────────────────────────
  `guard_handson` 은 Claude 가 `src/raglab/` 에 **쓰는 것**을 막는다.
  그런데 대필의 다른 경로가 있다 — `solutions/` 를 먼저 **읽고** 그 내용을
  설명·힌트에 흘리는 것이다. 파일에 안 썼을 뿐 결과는 같다.

  참조 구현 대조는 **가장 마지막에** 한다 (CLAUDE.md §3 검증 루프 5번).
  그 단계를 통과하기 전에는 열지 않는다.

  ⚠ 판정 — 파일명에 박힌 단계 번호와 `progress.json` 의 완료 단계를 비교한다
  ─────────────────────────────────────────────────────────────────────────────
      solutions/stage03_retrieval.py  →  단계 3
      완료 단계가 2 까지면            →  차단
      완료 단계가 3 이상이면          →  통과 (대조해도 되는 시점)

  ⚠ 단계 번호를 못 읽으면 통과시킨다 (README·__init__ 등). fail-open 이 맞다.

  ⚠⚠ fail-open — 훅 자체의 오류로는 아무것도 막지 않는다.
#>

$ErrorActionPreference = 'Stop'

# ⚠⚠ 출력 인코딩을 UTF-8 로 고정한다.
#   Windows PowerShell 5.1 기본값은 OEM 코드페이지(cp949)라,
#   차단 사유의 한글이 깨진 채 Claude 에게 전달된다 → 훅이 반쯤 무력화된다.
try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8NoBom
    $OutputEncoding = $utf8NoBom
} catch { }


function Pass { exit 0 }

function Deny([string]$Message) {
    [Console]::Error.Write($Message)
    exit 2
}

# ── 루트 찾기 (자체 폴백 포함) ───────────────────────────────────────────────
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

# ── 입력 파싱 ───────────────────────────────────────────────────────────────
try {
    $raw = [Console]::In.ReadToEnd()
    if ($raw.Length -gt 0 -and $raw[0] -eq [char]0xFEFF) { $raw = $raw.Substring(1) }
    $payload = $raw | ConvertFrom-Json
} catch { Pass }

if (-not $payload) { Pass }

$tool = [string]$payload.tool_name
$ti = $payload.tool_input
if (-not $ti) { Pass }

# ── 무엇을 건드리려 하는지 한 문자열로 모은다 ────────────────────────────────
$target = ''
foreach ($k in @('file_path', 'path', 'pattern', 'command', 'notebook_path')) {
    try {
        $v = [string]$ti.$k
        if ($v) { $target += ' ' + $v }
    } catch { }
}
if (-not $target) { Pass }

$norm = $target.Replace('\', '/')
if ($norm -notmatch 'solutions/') { Pass }

# ── 대상 단계 번호를 뽑는다 ─────────────────────────────────────────────────
# solutions/stage03_retrieval.py → 3
$m = [regex]::Match($norm, 'solutions/[^\s]*?stage[_-]?(\d{1,2})')
if (-not $m.Success) {
    # 디렉터리 통째 열람(ls solutions/, grep -r solutions/)도 위험하다.
    # 단계를 특정할 수 없으므로 「가장 이른 미완료 단계」 기준으로 본다.
    $wildcard = ($norm -match 'solutions/\s*$') -or ($norm -match 'solutions/\*') -or ($norm -match '-r[a-z]*\s+[^\s]*solutions')
    if (-not $wildcard) { Pass }
    $wantStage = -1
} else {
    $wantStage = [int]$m.Groups[1].Value
}

# ── 진도 확인 ───────────────────────────────────────────────────────────────
$prog = $null
try { $prog = Get-Progress -Root $root } catch { }

# 진도 파일이 없으면 아무 단계도 통과하지 않은 것으로 본다.
# ⚠ 여기서 fail-open 하면 훅이 무의미해진다 — 진도 파일은 저장소에 커밋돼 있다.
$completed = @()
try { if ($prog -and $prog.completed_stages) { $completed = @($prog.completed_stages) } } catch { }

$maxDone = -1
foreach ($c in $completed) {
    try { $ci = [int]$c; if ($ci -gt $maxDone) { $maxDone = $ci } } catch { }
}

if (($wantStage -ge 0) -and ($wantStage -le $maxDone)) { Pass }

# ── 차단 ────────────────────────────────────────────────────────────────────
$stageKo = if ($wantStage -ge 0) { "Stage $wantStage" } else { "solutions/ 전체" }
$doneKo = if ($maxDone -ge 0) { "Stage $maxDone 까지" } else { "아직 없음" }

$msg = @"
⛔ CLAUDE.md §3 검증 루프 — 참조 구현 대조는 **가장 마지막에** 합니다

  열려던 것 : $stageKo 의 참조 구현
  완료 단계 : $doneKo

`solutions/` 는 해당 단계를 **사용자가 통과한 뒤에** 여는 자료입니다.
지금 열면 그 내용이 설명·힌트로 새어 나가고, 그것은 §5-T(대필 금지)의 우회입니다.

■ 지금 대신 해야 할 것
  · 힌트가 필요하면 `hint` 스킬 — 정답이 아니라 **단계적 방향**을 줍니다
  · 사용자 코드가 왜 안 도는지 봐야 하면 `code-coach` 에 위임하십시오
  · 테스트가 무엇을 요구하는지는 ``tests/`` 를 읽으면 됩니다. 그건 명세이지 정답이 아닙니다

■ 정말 열어야 하는 경우
  사용자가 Stage $wantStage 를 통과했다면 `.claude/state/progress.json` 의
  `completed_stages` 에 그 번호가 들어 있어야 합니다. `checkpoint` 스킬이 갱신합니다.
  진도 기록이 실제보다 뒤처져 있다면 **먼저 진도를 바로잡으십시오.**
"@

Deny $msg
