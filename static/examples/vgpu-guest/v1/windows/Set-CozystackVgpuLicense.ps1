[CmdletBinding()]
param([string]$TestRoot)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
if ($PSBoundParameters.ContainsKey('TestRoot')) {
    if (-not $TestRoot -or $TestRoot -ne $env:COZYSTACK_VGPU_TEST_ROOT -or
        -not (Test-Path -LiteralPath $TestRoot -PathType Container) -or
        [IO.Path]::GetPathRoot($TestRoot) -eq $TestRoot) {
        throw 'Invalid sandbox invocation'
    }
    $drive = $TestRoot
} else {
    $drive = $env:SystemDrive + '\'
}
$folder = Join-Path $drive 'Program Files\NVIDIA Corporation\vGPU Licensing\ClientConfigToken'

function Assert-DirectoryPath([string]$Path) {
    $parent = Split-Path -Parent $Path
    if ($parent -and $parent -ne $Path) { Assert-DirectoryPath $parent }
    if (Test-Path -LiteralPath $Path) {
        $item = Get-Item -LiteralPath $Path -Force
        if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'Unsafe token directory'
        }
    }
}

function Clear-TokenFolder {
    foreach ($item in @(Get-ChildItem -LiteralPath $folder -Force)) {
        if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'Unexpected token folder entry'
        }
        Remove-Item -LiteralPath $item.FullName -Force -ErrorAction Stop
    }
}

try {
    Assert-DirectoryPath $folder
    if (-not (Test-Path -LiteralPath $folder)) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
    }
    Clear-TokenFolder
} catch {
    throw 'vGPU license token cleanup failed'
}

$mediaFailed = $false
try {
    $volumes = @(Get-Volume -ErrorAction Stop | Where-Object { $_.FileSystemLabel -ceq 'GPULICENSE' })
    if ($volumes.Count -gt 1) { throw 'Ambiguous media' }
    if ($volumes.Count -eq 1) {
        if (-not $volumes[0].Path) { throw 'Missing volume path' }
        $source = Join-Path $volumes[0].Path 'client_configuration_token.tok'
        $item = Get-Item -LiteralPath $source -Force -ErrorAction Stop
        if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -or $item.Length -eq 0) {
            throw 'Invalid token file'
        }
        $temporary = Join-Path $folder '.cozystack-token.tmp'
        Copy-Item -LiteralPath $source -Destination $temporary -ErrorAction Stop
        Move-Item -LiteralPath $temporary -Destination (Join-Path $folder 'client_configuration_token.tok') -ErrorAction Stop
    }
} catch {
    $mediaFailed = $true
    try { Clear-TokenFolder } catch { throw 'vGPU license token cleanup failed' }
}

try {
    Restart-Service -Name NvDisplayContainer -ErrorAction Stop
} catch {
    throw 'vGPU license client restart failed'
}
if ($mediaFailed) { throw 'vGPU license media preparation failed' }
