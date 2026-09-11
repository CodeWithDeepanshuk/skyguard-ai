param([switch]$RefreshHistoricalReports)
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot
. (Join-Path $projectRoot "tools/verification_helpers.ps1")
try {
    Invoke-CheckedCommand -Executable python -Arguments @("-m", "pytest", "-q", "-p", "no:cacheprovider")
    foreach ($script in @("app.js", "station-map.js", "sensor-trace.js", "live-qc.js")) {
        Invoke-CheckedCommand -Executable node -Arguments @("--check", "dashboard/$script")
    }
    Invoke-CheckedCommand -Executable node -Arguments @("tests/test_dashboard_selection.cjs")
    Invoke-CheckedCommand -Executable node -Arguments @("tests/test_live_qc.cjs")
    if ($RefreshHistoricalReports) {
        # Explicit opt-in: these legacy programs rewrite historical reports.
        # They are not fresh final tests or operational accuracy validation.
        foreach ($script in @("validate_correction_health.py", "validate_safe_repair.py", "validate_streaming_platform.py", "profile_competition_readiness.py", "validate_dashboard.py", "final_verification.py")) {
            Invoke-CheckedCommand -Executable python -Arguments @("src/data/$script")
        }
    }
    Invoke-CheckedCommand -Executable python -Arguments @("tools/r0_baseline.py", "verify")
    Write-Host "R0 code/contract verification passed. This is not a model-accuracy or SIH-completion certification."
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}
