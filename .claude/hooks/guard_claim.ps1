# -*- coding: utf-8 -*-
<#
  PreToolUse 훅 — **규격 미달 산출물이 사용자에게 나가는 것**을 막는다.
  (CLAUDE.md §3-S 합성 표기 · §8 산출물 구조 ⑥ · §13-5 부풀리지 않는다)

  ⚠⚠ 왜 이 훅이 있는가
  ─────────────────────────────────────────────────────────────────────────────
  이 프로젝트의 주 코퍼스는 **합성**이다. 합성에서 나온 Recall 수치가
  「RAG 는 이 정도 성능이다」로 읽히는 순간 그 산출물은 **틀린 것보다 나쁘다** —
  틀린 줄 모르고 인용되기 때문이다. 포트폴리오라면 더더욱.

  그리고 「한계」 절이 없는 보고서는 §8 구조 ⑥ 미달이다. 빼면 그 문서는 위험하다.

  ⚠ 무엇을 검사하는가 — **기계적으로 확인 가능한 것만** 본다
  ─────────────────────────────────────────────────────────────────────────────
    1. outputs/ 의 .html 을 내보낼 때 「합성」 표기가 본문에 있는가
    2. 그 파일에 「한계」 절이 있는가

  ⚠ 이건 규격 검사이지 내용 검사가 아니다. 수치가 맞는지는 훅이 못 본다 —
    그건 `verify` 에이전트의 몫이다 (§5).

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

try {
    $raw = [Console]::In.ReadToEnd()
    if ($raw.Length -gt 0 -and $raw[0] -eq [char]0xFEFF) { $raw = $raw.Substring(1) }
    $payload = $raw | ConvertFrom-Json
} catch { Pass }

if (-not $payload) { Pass }
$ti = $payload.tool_input
if (-not $ti) { Pass }

# ── 내보내려는 파일 목록 모으기 ──────────────────────────────────────────────
$files = New-Object System.Collections.Generic.List[string]
try { foreach ($f in @($ti.files)) { if ($f) { $files.Add([string]$f) } } } catch { }
try { if ($ti.file_path) { $files.Add([string]$ti.file_path) } } catch { }
if ($files.Count -eq 0) { Pass }

foreach ($f in $files) {
    $norm = $f.Replace('\', '/')
    if ($norm -notmatch '\.html$') { continue }
    if ($norm -notmatch 'outputs/') { continue }

    $body = ''
    try {
        if (Test-Path -LiteralPath $f) {
            $body = Get-Content -LiteralPath $f -Raw -Encoding UTF8
        }
    } catch { continue }
    if (-not $body) { continue }

    $missing = New-Object System.Collections.Generic.List[string]
    if ($body -notmatch '합성') { $missing.Add('§3-S 합성 데이터 표기 배너') }
    if ($body -notmatch '한계') { $missing.Add('§8 구조 ⑥ 「한계」 절') }

    if ($missing.Count -eq 0) { continue }

    $leaf = Split-Path $f -Leaf
    $msg = @"
⛔ 산출물 규격 미달 — 사용자에게 내보내기 전에 채워야 합니다

  대상 : $leaf
  누락 : $($missing -join ' · ')

■ §3-S 합성 표기
  data/synthetic/ 은 전부 합성입니다. 한빛텔레콤·요금제·고객·수치 전부 가상입니다.
  **최상단 배너로 표기**하십시오. `labkit.report` 에 synthetic=True 옵션이 있습니다.
  합성에서 나온 수치를 실세계 RAG 성능처럼 읽히게 두면, 그 산출물은 틀린 것보다 나쁩니다.

■ §8 구조 ⑥ 「한계」 절
  이 방법이 **언제 틀린 답을 내는가**를 적는 자리입니다.
  잘 되는 예제만 있는 문서가 가장 해롭습니다 (§10 원칙 3).
  포트폴리오 관점에서도 한계를 아는 것이 차별점입니다 (§13-2).

빌더 `src/labkit/report.py` 를 쓰면 두 항목이 자동으로 들어갑니다.
직접 HTML 문자열을 조립했다면 그게 원인일 가능성이 높습니다 (§8).
"@
    Deny $msg
}

Pass
