# PowerShell 5.1+; one station x two API requests. No keys are printed or saved.
$ErrorActionPreference = 'Stop'
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) { throw 'Python 3.10+ is required.' }

$highInput = Read-Host '고·저조 API 인증키 (입력 내용은 숨김)' -AsSecureString
$seriesInput = Read-Host '시계열 API 인증키 (입력 내용은 숨김)' -AsSecureString
try {
    $env:KHOA_HIGH_LOW_KEY = [System.Net.NetworkCredential]::new('', $highInput).Password
    $env:KHOA_SERIES_KEY = [System.Net.NetworkCredential]::new('', $seriesInput).Password
    if ([string]::IsNullOrWhiteSpace($env:KHOA_HIGH_LOW_KEY) -or [string]::IsNullOrWhiteSpace($env:KHOA_SERIES_KEY)) {
        throw 'Both keys must be entered.'
    }
    & $PythonCmd.Source (Join-Path $PSScriptRoot 'schema_probe.py') --station incheon
    if ($LASTEXITCODE -ne 0) { Write-Warning 'Probe was incomplete. Share only the sanitized output.' }
} finally {
    Remove-Item Env:KHOA_HIGH_LOW_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:KHOA_SERIES_KEY -ErrorAction SilentlyContinue
}
