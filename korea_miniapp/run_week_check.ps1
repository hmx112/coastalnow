# Experimental 7-day data validation. Requires 280 total KHOA API calls for 20 stations.
# On the PC, open a PowerShell window inside korea_miniapp and run this script.
$ErrorActionPreference = 'Stop'
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { throw 'Python 3.10+ is required' }
$h = Read-Host '고·저조 API 인증키를 입력하세요 (화면에 표시되지 않음)' -AsSecureString
$s = Read-Host '시계열 API 인증키를 입력하세요 (화면에 표시되지 않음)' -AsSecureString
try {
    $env:KHOA_HIGH_LOW_KEY = [System.Net.NetworkCredential]::new('', $h).Password
    $env:KHOA_SERIES_KEY = [System.Net.NetworkCredential]::new('', $s).Password
    & $py.Source -m unittest discover -s $PSScriptRoot -p 'test_*.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Offline tests failed. Skipping API requests.' }
    & $py.Source (Join-Path $PSScriptRoot 'build_week.py') --station all
    if ($LASTEXITCODE -ne 0) { throw '7-day collection incomplete. Existing cache is preserved.' }
    Write-Host '7-day data ready (development-only). Do not upload private API keys.'
} finally {
    Remove-Item Env:KHOA_HIGH_LOW_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:KHOA_SERIES_KEY -ErrorAction SilentlyContinue
}
