[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$SqlFile,

    [ValidateNotNullOrEmpty()]
    [string]$ProjectId,

    [ValidateNotNullOrEmpty()]
    [string]$DatasetId = "vitality_engagement_dev",

    [ValidateNotNullOrEmpty()]
    [string]$Location = "asia-southeast1",

    [ValidateRange(1, [long]::MaxValue)]
    [long]$MaximumBytesBilled = 100000000,

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Get-Command "bq" -ErrorAction Stop | Out-Null
Get-Command "gcloud" -ErrorAction Stop | Out-Null

if ([string]::IsNullOrWhiteSpace($ProjectId)) {
    $previousErrorActionPreference = $ErrorActionPreference

    try {
        # Windows PowerShell 5.1 can treat gcloud's informational
        # stderr output as a terminating error when preference is Stop.
        $ErrorActionPreference = "SilentlyContinue"

        $activeProjectOutput = @(
            gcloud config get project --quiet 2>$null
        )

        $gcloudExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    if ($gcloudExitCode -ne 0) {
        throw "Unable to read the active Google Cloud project."
    }

    $activeProject = $activeProjectOutput |
        Where-Object {
            -not [string]::IsNullOrWhiteSpace($_)
        } |
        Select-Object -Last 1

    if (
        [string]::IsNullOrWhiteSpace($activeProject) -or
        $activeProject.Trim() -eq "(unset)"
    ) {
        throw "No active Google Cloud project is configured."
    }

    $ProjectId = $activeProject.Trim()
}

$resolvedSqlFile = Resolve-Path `
    -LiteralPath $SqlFile `
    -ErrorAction Stop

if (
    [System.IO.Path]::GetExtension(
        $resolvedSqlFile.Path
    ) -ne ".sql"
) {
    throw "The input file must have a .sql extension."
}

$sql = Get-Content `
    -LiteralPath $resolvedSqlFile.Path `
    -Raw

if ([string]::IsNullOrWhiteSpace($sql)) {
    throw "The SQL file is empty: $($resolvedSqlFile.Path)"
}

Write-Output "Running SQL file: $($resolvedSqlFile.Path)"
Write-Output "Project:          $ProjectId"
Write-Output "Dataset:          $DatasetId"
Write-Output "Location:         $Location"
Write-Output "Dry run:          $DryRun"

$bqArguments = @(
    "--location=$Location"
    "--dataset_id=$ProjectId`:$DatasetId"
    "query"
    "--use_legacy_sql=false"
    "--maximum_bytes_billed=$MaximumBytesBilled"
)

if ($DryRun) {
    $bqArguments += "--dry_run"
}

$previousErrorActionPreference = $ErrorActionPreference

try {
    # Let bq write progress information without PowerShell 5.1
    # treating stderr output as a terminating script error.
    $ErrorActionPreference = "Continue"

    $sql | & bq @bqArguments

    $bqExitCode = $LASTEXITCODE
}
finally {
    $ErrorActionPreference = $previousErrorActionPreference
}

if ($bqExitCode -ne 0) {
    throw "BigQuery execution failed with exit code $bqExitCode."
}

Write-Output "BigQuery SQL execution completed successfully."
