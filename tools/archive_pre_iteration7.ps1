param(
    [string]$DownloadsRoot = 'C:\Users\deepa\Downloads',
    [string]$ProjectRoot = 'C:\Users\deepa\OneDrive\Desktop\Sih 73',
    [string]$ArchiveName = 'archive_pre_iteration7_2026-08-29'
)

$ErrorActionPreference = 'Stop'

$archiveRoot = Join-Path $ProjectRoot "reports\gpu_iterations\$ArchiveName"
$snapshotPath = Join-Path $ProjectRoot 'deliverables\SkyGuard_PreIteration7_Code_Artifacts_Snapshot_2026-08-29.zip'

if (Test-Path -LiteralPath $archiveRoot) {
    throw "Archive already exists and will not be overwritten: $archiveRoot"
}
if (Test-Path -LiteralPath $snapshotPath) {
    throw "Snapshot already exists and will not be overwritten: $snapshotPath"
}

$null = New-Item -ItemType Directory -Path $archiveRoot
$null = New-Item -ItemType Directory -Path (Join-Path $archiveRoot 'notebooks')
$null = New-Item -ItemType Directory -Path (Join-Path $archiveRoot 'results')
$null = New-Item -ItemType Directory -Path (Join-Path $archiveRoot 'models')
$null = New-Item -ItemType Directory -Path (Join-Path $archiveRoot 'prompts')

$candidatePattern = '^(SkyGuard_AI_GPU_|SIH_Weather_Station_Quality_|iteration|development_|blind_2025_|weak_union_)'
$downloadFiles = @(Get-ChildItem -LiteralPath $DownloadsRoot -File | Where-Object {
    $_.Name -match $candidatePattern -and $_.Extension -in @('.ipynb', '.csv', '.json', '.joblib', '.cbm', '.md')
} | Sort-Object Name)

$hashMap = @{}
$downloadManifest = foreach ($file in $downloadFiles) {
    $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    $category = switch ($file.Extension.ToLowerInvariant()) {
        '.ipynb' { 'notebooks' }
        '.joblib' { 'models' }
        '.cbm' { 'models' }
        '.md' { 'prompts' }
        default { 'results' }
    }

    $isDuplicate = $hashMap.ContainsKey($hash)
    if ($isDuplicate) {
        $destinationRelative = $hashMap[$hash]
    }
    else {
        $destinationRelative = Join-Path $category $file.Name
        $destinationAbsolute = Join-Path $archiveRoot $destinationRelative
        Copy-Item -LiteralPath $file.FullName -Destination $destinationAbsolute
        $hashMap[$hash] = $destinationRelative
    }

    [pscustomobject]@{
        source_path = $file.FullName
        source_name = $file.Name
        bytes = $file.Length
        modified_utc = $file.LastWriteTimeUtc.ToString('o')
        sha256 = $hash
        duplicate_content = $isDuplicate
        archived_as = $destinationRelative
    }
}

$downloadManifestPath = Join-Path $archiveRoot 'download_artifact_manifest.csv'
$downloadManifest | Export-Csv -LiteralPath $downloadManifestPath -NoTypeInformation -Encoding utf8

$workspaceRoots = @('src', 'tests', 'tools', 'notebooks', 'docs', 'reports', 'models', 'dashboard', 'config')
$workspaceFiles = foreach ($relativeRoot in $workspaceRoots) {
    $absoluteRoot = Join-Path $ProjectRoot $relativeRoot
    if (Test-Path -LiteralPath $absoluteRoot) {
        Get-ChildItem -LiteralPath $absoluteRoot -File -Recurse | Where-Object {
            $_.FullName -notmatch '\\__pycache__\\' -and
            $_.FullName -notlike "$archiveRoot*"
        }
    }
}

$rootFiles = @('README.md', 'requirements.txt', 'Dockerfile', 'start_skyguard.ps1',
               'start_skyguard.bat', 'verify_skyguard.ps1') | ForEach-Object {
    $candidate = Join-Path $ProjectRoot $_
    if (Test-Path -LiteralPath $candidate) { Get-Item -LiteralPath $candidate }
}

$workspaceFiles = @($workspaceFiles) + @($rootFiles)
$workspaceManifest = foreach ($file in ($workspaceFiles | Sort-Object FullName -Unique)) {
    [pscustomobject]@{
        relative_path = [IO.Path]::GetRelativePath($ProjectRoot, $file.FullName)
        bytes = $file.Length
        modified_utc = $file.LastWriteTimeUtc.ToString('o')
        sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    }
}

$workspaceManifestPath = Join-Path $archiveRoot 'workspace_code_artifact_manifest.csv'
$workspaceManifest | Export-Csv -LiteralPath $workspaceManifestPath -NoTypeInformation -Encoding utf8

$snapshotSources = @(
    (Join-Path $ProjectRoot 'src'),
    (Join-Path $ProjectRoot 'tests'),
    (Join-Path $ProjectRoot 'tools'),
    (Join-Path $ProjectRoot 'notebooks'),
    (Join-Path $ProjectRoot 'docs'),
    (Join-Path $ProjectRoot 'reports'),
    (Join-Path $ProjectRoot 'models'),
    (Join-Path $ProjectRoot 'dashboard'),
    (Join-Path $ProjectRoot 'config'),
    (Join-Path $ProjectRoot 'README.md'),
    (Join-Path $ProjectRoot 'requirements.txt'),
    (Join-Path $ProjectRoot 'Dockerfile'),
    (Join-Path $ProjectRoot 'start_skyguard.ps1'),
    (Join-Path $ProjectRoot 'start_skyguard.bat'),
    (Join-Path $ProjectRoot 'verify_skyguard.ps1'),
    (Join-Path $ProjectRoot 'data\manifest'),
    (Join-Path $ProjectRoot 'data\blind_2025\manifest'),
    (Join-Path $ProjectRoot 'data\blind_2025\blind_protocol.json'),
    (Join-Path $ProjectRoot 'data\labelled\manifest.csv'),
    (Join-Path $ProjectRoot 'data\features\manifest.csv'),
    (Join-Path $ProjectRoot 'data\features\feature_spec.json'),
    (Join-Path $ProjectRoot 'data\features_phase10\feature_spec.json')
) | Where-Object { Test-Path -LiteralPath $_ }

Compress-Archive -LiteralPath $snapshotSources -DestinationPath $snapshotPath -CompressionLevel Optimal

$summary = [ordered]@{
    created_utc = [DateTime]::UtcNow.ToString('o')
    archive_root = $archiveRoot
    download_candidates = $downloadFiles.Count
    unique_download_artifacts = $hashMap.Count
    duplicate_download_copies = @($downloadManifest | Where-Object duplicate_content).Count
    workspace_manifest_files = $workspaceManifest.Count
    snapshot_path = $snapshotPath
    snapshot_bytes = (Get-Item -LiteralPath $snapshotPath).Length
    snapshot_sha256 = (Get-FileHash -LiteralPath $snapshotPath -Algorithm SHA256).Hash.ToLowerInvariant()
    raw_data_note = 'Raw/generated NOAA data remains in the OneDrive project and is represented by manifests; it is intentionally not duplicated into this compact snapshot.'
}

$summaryPath = Join-Path $archiveRoot 'archive_summary.json'
$summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $summaryPath -Encoding utf8
$summary | ConvertTo-Json -Depth 5
