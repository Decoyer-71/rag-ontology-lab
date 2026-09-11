# -*- coding: utf-8 -*-
<#
  **메모리를 저장소와 잇는다.** (CLAUDE.md §15-4) — 훅이 아니라 PC 마다 한 번 돌리는 설정 도구다.

  ⚠⚠ 왜 필요한가
  ─────────────────────────────────────────────────────────────────────────────
  Claude 가 실제로 읽고 쓰는 메모리는 저장소 밖에 있다:
      %USERPROFILE%\.claude\projects\<세션을 연 경로를 인코딩한 이름>\memory\
  그래서 한 PC 에서 새로 생긴 메모리는 반대쪽 PC 로 갈 길이 **손 복사뿐**이었고,
  2026-09-11 에 노트북 세션이 실제로 **메모리 0개**로 돌고 있었다.

  → 그 폴더를 저장소의 `.claude/memory/` 를 가리키는 **디렉터리 정션**으로 바꾼다.
    그러면 메모리도 git 으로 따라온다. 정션은 관리자 권한이 필요 없다.

  ⚠⚠ 대가 — 메모리가 **공개 저장소에 커밋된다.** 개인정보를 적지 않는다 (§15-5 관문이 한 번 더 본다).

  ⚠ 폴더 이름 규칙은 _common.ps1 의 Get-MemoryLinkStatus 에 있다.
     Claude Code 내부 규칙이라 바뀔 수 있다 — 그래서 preflight 가 매 세션 연결 상태를 확인한다.

  사용:
      .claude\hooks\link_memory.ps1           연결 (이미 연결돼 있으면 아무것도 안 한다)
      .claude\hooks\link_memory.ps1 -Check    상태만 보고

  ⚠⚠ 기존 메모리 폴더에 파일이 있으면
      · 저장소에 없는 파일 → 저장소로 복사
      · 같은 내용          → 그대로 둔다
      · **내용이 다른 파일** → 멈추고 목록을 보여준다. 어느 쪽이 맞는지는 사람이 정한다
      옛 폴더는 지우지 않고 `memory.bak-<시각>` 으로 이름만 바꾼다 (비어 있을 때만 지운다).
#>

param([switch]$Check)

$ErrorActionPreference = 'Stop'

try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [Console]::OutputEncoding = $utf8NoBom
    $OutputEncoding = $utf8NoBom
} catch { }

$startDir = $PSScriptRoot
if (-not $startDir) { $startDir = Split-Path -Parent $MyInvocation.MyCommand.Path }
. (Join-Path $startDir '_common.ps1')

$root = (Resolve-RepoRoot -StartDir $startDir -Markers @('.claude\hooks')).Root
if (-not $root) {
    Write-Output "[memory] ⛔ 저장소 루트를 못 찾았습니다"
    exit 1
}

$st = Get-MemoryLinkStatus -Root $root

if ($Check) {
    switch ($st.State) {
        'linked'    { Write-Output "[memory] ✅ 저장소와 연결됨 → .claude\memory" }
        'elsewhere' { Write-Output "[memory] ⛔ 다른 곳으로 연결돼 있습니다: $($st.LinkTarget)" }
        default     { Write-Output "[memory] ⛔ 저장소와 연결돼 있지 않습니다 ($($st.State)) → .claude\hooks\link_memory.ps1" }
    }
    exit 0
}

switch ($st.State) {
    'linked' {
        Write-Output "[memory] ✅ 이미 연결돼 있습니다 → .claude\memory"
        exit 0
    }
    'elsewhere' {
        Write-Output "[memory] ⛔ 메모리 폴더가 다른 곳을 가리킵니다: $($st.LinkTarget)"
        Write-Output "         무엇을 가리키는지 확인한 뒤 손으로 정리하십시오. 이 도구는 남의 연결을 끊지 않습니다."
        exit 1
    }
    'plain' {
        $files = @(Get-ChildItem -LiteralPath $st.Real -File -Force)
        $dirs  = @(Get-ChildItem -LiteralPath $st.Real -Directory -Force)
        $conflicts = New-Object System.Collections.Generic.List[string]
        $toCopy = New-Object System.Collections.Generic.List[object]
        foreach ($f in $files) {
            $dest = Join-Path $st.Target $f.Name
            if (-not (Test-Path -LiteralPath $dest)) { $toCopy.Add($f); continue }
            $h1 = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash
            $h2 = (Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash
            if ($h1 -ne $h2) { $conflicts.Add($f.Name) }
        }
        foreach ($d in $dirs) { $conflicts.Add("$($d.Name)\ (하위 폴더)") }

        if ($conflicts.Count -gt 0) {
            Write-Output "[memory] ⛔ 저장소 사본과 내용이 다른 파일이 있어 멈춥니다 — 어느 쪽이 맞는지 정한 뒤 다시 실행하십시오"
            foreach ($c in $conflicts) { Write-Output "         · $c" }
            Write-Output "         기존 폴더: $($st.Real)"
            exit 1
        }

        foreach ($f in $toCopy) {
            Copy-Item -LiteralPath $f.FullName -Destination $st.Target
            Write-Output "[memory] 저장소로 복사: $($f.Name)"
        }

        if ($files.Count -eq 0 -and $dirs.Count -eq 0) {
            Remove-Item -LiteralPath $st.Real -Force
        } else {
            $bakName = 'memory.bak-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
            Rename-Item -LiteralPath $st.Real -NewName $bakName
            Write-Output "[memory] 옛 폴더는 지우지 않고 $bakName 으로 남겼습니다"
        }
    }
    'missing' {
        $parent = Split-Path -Parent $st.Real
        if (-not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
    }
}

New-Item -ItemType Junction -Path $st.Real -Target $st.Target | Out-Null

$after = Get-MemoryLinkStatus -Root $root
if ($after.State -eq 'linked') {
    $n = @(Get-ChildItem -LiteralPath $st.Real -File -Force).Count
    Write-Output "[memory] ✅ 연결했습니다 — 메모리 폴더가 이제 저장소 .claude\memory 를 봅니다 (파일 $n 개)"
    exit 0
}
Write-Output "[memory] ⛔ 정션을 만들었지만 확인에 실패했습니다 (상태: $($after.State))"
exit 1
