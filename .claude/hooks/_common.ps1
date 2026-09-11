# -*- coding: utf-8 -*-
<#
  훅 공용 — **저장소 루트를 스스로 찾는다.**

  ⚠ oil_DA `.claude/hooks/_common.ps1` 에서 이식했다. 거기서 배운 것:
     환경변수 CLAUDE_PROJECT_DIR 이 없거나 현재 디렉터리가 저장소 밖이면
     훅들이 **조용히 엉뚱한 곳을 루트로 잡고 fail-open** 한다.
     침묵하는 방어선은 없는 방어선보다 나쁘다.

  ⚠⚠ 이 파일을 못 읽어도 훅은 죽으면 안 된다.
     각 훅은 dot-source 를 try/catch 로 감싸고 자체 폴백을 갖는다.

  ⚠ 이 파일은 **함수 정의만** 한다. 로드 시 부수효과·출력이 없어야 dot-source 가 안전하다.

  ⚠⚠ 이 파일은 **UTF-8 BOM** 으로 저장돼야 한다.
     Windows PowerShell 5.1 은 BOM 없는 UTF-8 을 ANSI(cp949)로 읽어 한글이 깨진다.
#>

function Resolve-RepoRoot {
    <#
      .SYNOPSIS
        저장소 루트를 찾는다. **현재 디렉터리(Get-Location)에 의존하지 않는다.**

      .PARAMETER StartDir
        위로 올라가기 시작할 디렉터리. 보통 훅의 $PSScriptRoot (= <루트>\.claude\hooks).

      .PARAMETER Markers
        「여기가 루트다」의 증거로 삼을 상대경로들. 하나라도 실재하면 그 디렉터리를 루트로 본다.

      .OUTPUTS
        [pscustomobject] Root / Method / MethodKo / Marker / Searched
    #>
    param(
        [string]$StartDir,
        [string[]]$Markers = @('.claude\hooks'),
        [int]$MaxUp = 6
    )

    $searched    = New-Object System.Collections.Generic.List[string]
    $rootFound   = $null
    $methodFound = 'none'
    $markerFound = $null

    # ① 환경변수 — 있고, **그 아래 marker 가 실재할 때만** 채택한다.
    #    가리키기만 하는 값은 믿지 않는다.
    if ($env:CLAUDE_PROJECT_DIR) {
        foreach ($marker in $Markers) {
            $candidate = $null
            try { $candidate = Join-Path $env:CLAUDE_PROJECT_DIR $marker } catch { }
            if (-not $candidate) { continue }
            $searched.Add($candidate)
            $found = $false
            try { $found = Test-Path -LiteralPath $candidate } catch { $found = $false }
            if ($found) {
                $rootFound = $env:CLAUDE_PROJECT_DIR
                $methodFound = 'env'
                $markerFound = $marker
                break
            }
        }
    }

    # ② 스크립트 자신의 위치에서 **위로** 올라가며 찾는다
    if (-not $rootFound -and $StartDir) {
        $probeDir = $StartDir
        for ($upStep = 0; ($upStep -lt $MaxUp) -and $probeDir; $upStep++) {
            foreach ($marker in $Markers) {
                $candidate = $null
                try { $candidate = Join-Path $probeDir $marker } catch { }
                if (-not $candidate) { continue }
                $searched.Add($candidate)
                $found = $false
                try { $found = Test-Path -LiteralPath $candidate } catch { $found = $false }
                if ($found) {
                    $rootFound = $probeDir
                    $methodFound = 'self'
                    $markerFound = $marker
                    break
                }
            }
            if ($rootFound) { break }
            $parentDir = $null
            try { $parentDir = Split-Path -Parent $probeDir } catch { }
            if (-not $parentDir -or ($parentDir -eq $probeDir)) { break }
            $probeDir = $parentDir
        }
    }

    $methodKo = switch ($methodFound) {
        'env'   { 'CLAUDE_PROJECT_DIR 환경변수' }
        'self'  { '자가탐색(스크립트 위치 기준)' }
        default { '못 찾음' }
    }

    return [pscustomobject]@{
        Root     = $rootFound
        Method   = $methodFound
        MethodKo = $methodKo
        Marker   = $markerFound
        Searched = @($searched)
    }
}

function Get-Progress {
    <#
      .SYNOPSIS
        .claude/state/progress.json 을 읽는다. 없거나 깨졌으면 $null.

      .DESCRIPTION
        여러 훅과 스킬이 「지금 몇 단계인가」를 물어본다. 한 곳에 모은다.
    #>
    param([string]$Root)

    if (-not $Root) { return $null }
    $p = Join-Path $Root '.claude\state\progress.json'
    if (-not (Test-Path -LiteralPath $p)) { return $null }
    try {
        return (Get-Content -LiteralPath $p -Raw -Encoding UTF8 | ConvertFrom-Json)
    } catch {
        return $null
    }
}

function Get-MemoryLinkStatus {
    <#
      .SYNOPSIS
        이 저장소의 Claude 메모리 폴더가 저장소 `.claude\memory` 로 정션 연결돼 있는지 본다. (CLAUDE.md §15-4)

      .DESCRIPTION
        Claude Code 는 세션을 연 경로의 **영숫자가 아닌 글자를 전부 `-` 로 바꾼 이름**으로
        `%USERPROFILE%\.claude\projects\` 아래에 폴더를 만든다.
          C:\projects\rag-ontology-lab → C--projects-rag-ontology-lab   (2026-09-11 노트북 실측으로 대조)
        ⚠ 내부 규칙이라 바뀔 수 있다. 바뀌면 State 가 missing 으로 나와 preflight 가 알린다.

      .OUTPUTS
        [pscustomobject] State(linked|missing|plain|elsewhere) / Real / Target / LinkTarget
    #>
    param([string]$Root)

    $enc    = ($Root.TrimEnd('\', '/') -replace '[^A-Za-z0-9]', '-')
    $real   = Join-Path $env:USERPROFILE ".claude\projects\$enc\memory"
    $target = Join-Path $Root '.claude\memory'

    $state = 'missing'
    $linkTarget = $null
    $item = Get-Item -LiteralPath $real -Force -ErrorAction SilentlyContinue
    if ($item) {
        if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            $linkTarget = [string](@($item.Target)[0])
            $norm = $linkTarget -replace '^\\\\\?\\', '' -replace '^\\\?\?\\', ''
            if ($norm.TrimEnd('\') -ieq $target.TrimEnd('\')) { $state = 'linked' } else { $state = 'elsewhere' }
        } else {
            $state = 'plain'
        }
    }

    return [pscustomobject]@{
        State      = $state
        Real       = $real
        Target     = $target
        LinkTarget = $linkTarget
    }
}

function Count-LogicLines {
    <#
      .SYNOPSIS
        파이썬 코드 문자열에서 「실제 로직 줄」 개수를 센다.

      .DESCRIPTION
        주석·빈 줄·독스트링·import·def/class 선언·pass·NotImplementedError 는 로직이 아니다.
        뼈대(시그니처 + 독스트링 + TODO)와 구현을 구분하는 데 쓴다 (CLAUDE.md §5-T).

        ⚠ 완벽한 파서가 아니다. **경계선을 재는 근사값**이고, 그래서 임계값을 넉넉히 잡는다.
           애매하면 통과시킨다 — 훅이 오탐으로 작업을 막는 것이 더 나쁘다.
    #>
    param([string]$Code)

    if (-not $Code) { return 0 }

    # 삼중따옴표 블록(독스트링)을 통째로 제거한다
    $stripped = $Code
    try {
        $stripped = [regex]::Replace($stripped, '(?s)""".*?"""', '')
        $stripped = [regex]::Replace($stripped, "(?s)'''.*?'''", '')
    } catch { }

    $n = 0
    foreach ($line in ($stripped -split "`n")) {
        $t = $line.Trim()
        if (-not $t) { continue }
        if ($t.StartsWith('#')) { continue }
        if ($t -match '^(import|from)\s') { continue }
        if ($t -match '^(def|class|@)') { continue }
        if ($t -match '^(pass|\.\.\.)$') { continue }
        if ($t -match 'NotImplementedError') { continue }
        if ($t -match '^(\)|\]|\}|"\)|\)\s*->.*:)$') { continue }
        $n++
    }
    return $n
}
