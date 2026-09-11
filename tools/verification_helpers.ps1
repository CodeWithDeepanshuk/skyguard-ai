function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [string[]]$Arguments = @()
    )
    # Windows PowerShell does not turn a native nonzero exit into a terminating
    # error merely because ErrorActionPreference is Stop.
    & $Executable @Arguments
    # Do not create a local LASTEXITCODE variable: it shadows the global value
    # updated by native processes and can turn failed tests into false passes.
    $commandExitCode = $global:LASTEXITCODE
    if ($commandExitCode -ne 0) {
        throw "Verification stopped: $Executable exited with code $commandExitCode."
    }
}
