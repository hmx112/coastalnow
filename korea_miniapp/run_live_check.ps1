# Windows PowerShell 5.1+ / PowerShell 7
# Enter both API keys locally. Neither key is printed or written to disk.
$ErrorActionPreference = 'Stop'
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) { throw 'Python 3.10+ is required. Install Python, reopen PowerShell and retry.' }

$highInput = Read-Host '고·저조 API 인증키를 입력하세요 (표시되지 않음)' -AsSecureString
$seriesInput = Read-Host '시계열 API 인증키를 입력하세요 (같은 키라도 다시 입력)' -AsSecureString

try {
    $env:KHOA_HIGH_LOW_KEY = [System.Net.NetworkCredential]::new('', $highInput).Password
    $env:KHOA_SERIES_KEY = [System.Net.NetworkCredential]::new('', $seriesInput).Password
    if ([string]::IsNullOrWhiteSpace($env:KHOA_HIGH_LOW_KEY) -or [string]::IsNullOrWhiteSpace($env:KHOA_SERIES_KEY)) {
        throw 'Both KHOA keys are required for the two endpoint test.'
    }

    Write-Host '=== Offline validation ==='
    & $PythonCmd.Source -m unittest discover -s $PSScriptRoot -p 'test_*.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed; live API calls were skipped.' }

    $outDir = Join-Path $PSScriptRoot 'output'
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    $failures = 0
    foreach ($station in @('incheon', 'busan', 'jeju')) {
        Write-Host ("=== Live test: {0} ===" -f $station)
        & $PythonCmd.Source (Join-Path $PSScriptRoot 'pipeline.py') --station $station --output (Join-Path $outDir "$station.json")
        if ($LASTEXITCODE -ne 0) {
            $failures++
            Write-Warning ("KHOA live validation failed: {0}" -f $station)
        }
    }
    if ($failures -eq 0) {
        Write-Host 'PASS: all 3 stations validated. Share the summary output only; do not share API keys.'
        Write-Host ("Local JSON output directory: {0}" -f $outDir)
    } else {
        Write-Warning ("Incomplete validation: {0} of 3 stations failed. Report only the sanitized error messages." -f $failures)
    }
} finally {
    Remove-Item Env:KHOA_HIGH_LOW_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:KHOA_SERIES_KEY -ErrorAction SilentlyContinue
}
