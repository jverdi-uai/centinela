$ErrorActionPreference = "Stop"
$baseUrl = if ($env:CENTINELA_BASE_URL) { $env:CENTINELA_BASE_URL } else { "http://127.0.0.1:8000/api/v1" }
$health = Invoke-RestMethod -Uri "$baseUrl/health"
if ($health.status -ne "ok") { throw "Health check falló" }
$metrics = Invoke-RestMethod -Uri "$baseUrl/metrics"
Write-Output "health=ok mock_mode=$($health.mock_mode) total_cases=$($metrics.total)"

