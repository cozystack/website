BeforeAll {
    $Asset = Join-Path $PSScriptRoot '../static/examples/vgpu-guest/v1/windows/Set-CozystackVgpuLicense.ps1'
    # Keep cmdlet objects: module-qualified names can still resolve to Pester mocks.
    $RemoveItemCmdlet = Get-Command -Name Remove-Item -Module Microsoft.PowerShell.Management -CommandType Cmdlet -All -ErrorAction Stop
    $CopyItemCmdlet = Get-Command -Name Copy-Item -Module Microsoft.PowerShell.Management -CommandType Cmdlet -All -ErrorAction Stop

    function Remove-GuestFixture([string]$Path, [switch]$Recurse) {
        if (-not $Path.StartsWith($Root + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Fixture cleanup outside owned TestDrive root'
        }
        & $RemoveItemCmdlet -LiteralPath $Path -Recurse:$Recurse -Force -ErrorAction Stop
    }
}

Describe 'Platform vGPU guest token' {
    BeforeEach {
        $Root = Join-Path $TestDrive ([guid]::NewGuid().ToString())
        # Same separators as the script: the mocks compare paths as strings.
        $Folder = Join-Path $Root 'Program Files\NVIDIA Corporation\vGPU Licensing\ClientConfigToken'
        $Media = Join-Path $Root 'media with spaces'
        New-Item -ItemType Directory -Path $Folder, $Media -Force | Out-Null
        Set-Content -LiteralPath (Join-Path $Folder 'old.tok') -Value 'SYNTHETIC-STALE'
        Set-Content -LiteralPath (Join-Path $Media 'client_configuration_token.tok') -Value 'SYNTHETIC-TOKEN-A'
        Set-Content -LiteralPath (Join-Path $Media 'gridd.conf') -Value 'FeatureType=4'
        $env:COZYSTACK_VGPU_TEST_ROOT = $Root
        $Events = [System.Collections.Generic.List[string]]::new()
        Mock Get-Volume { [pscustomobject]@{ FileSystemLabel = 'GPULICENSE'; Path = $Media } }
        Mock Remove-Item {
            if (-not $LiteralPath.StartsWith($Folder + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Deletion outside TestDrive token directory'
            }
            $Events.Add('cleanup')
            & $RemoveItemCmdlet -LiteralPath $LiteralPath -Force -ErrorAction Stop
        }
        Mock Copy-Item {
            if (-not $Destination.StartsWith($Folder + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
                throw 'Copy outside TestDrive token directory'
            }
            $Events.Add('copy')
            & $CopyItemCmdlet -LiteralPath $LiteralPath -Destination $Destination -ErrorAction Stop
        }
        $Client = @{ State = 'Running'; Restarts = 0 }
        Mock Restart-Service {
            $Client.State | Should -Be 'Running'
            $Events.Add('restart')
            $Client.State = 'Restarted'
            $Client.Restarts++
        }
        Mock Set-ItemProperty { throw 'Registry writes are forbidden' }
    }

    AfterEach {
        $env:COZYSTACK_VGPU_TEST_ROOT = $null
    }

    It 'cleans an already-running client folder, copies only token, then restarts the actual client' {
        & $Asset -TestRoot $Root
        @($Events) -join ',' | Should -Be 'cleanup,copy,restart'
        (@(Get-ChildItem -LiteralPath $Folder).Name -join ',') | Should -Be 'client_configuration_token.tok'
        Get-Content -LiteralPath (Join-Path $Folder 'client_configuration_token.tok') | Should -Be 'SYNTHETIC-TOKEN-A'
        Should -Invoke Restart-Service -Times 1 -Exactly -ParameterFilter { $Name -eq 'NvDisplayContainer' }
        Should -Invoke Set-ItemProperty -Times 0
        $Client.State | Should -Be 'Restarted'
        $Client.Restarts | Should -Be 1
        $Client.State = 'Running'
        & $Asset -TestRoot $Root
        $Client.State | Should -Be 'Restarted'
        $Client.Restarts | Should -Be 2
        Should -Invoke Restart-Service -Times 2 -Exactly
    }

    It 'cleans stale tokens and restarts when media is absent' {
        Mock Get-Volume { @() }
        & $Asset -TestRoot $Root
        @(Get-ChildItem -LiteralPath $Folder).Count | Should -Be 0
        @($Events) -join ',' | Should -Be 'cleanup,restart'
    }

    It 'creates a missing token directory and restarts without media' {
        Remove-GuestFixture -Path $Folder -Recurse
        Mock Get-Volume { @() }
        & $Asset -TestRoot $Root
        Test-Path -LiteralPath $Folder -PathType Container | Should -BeTrue
        @($Events) -join ',' | Should -Be 'restart'
    }

    It 'rejects ambiguous media after cleanup and still restarts' {
        Mock Get-Volume { @([pscustomobject]@{ FileSystemLabel = 'GPULICENSE'; Path = $Media }) * 2 }
        { & $Asset -TestRoot $Root } | Should -Throw '*vGPU license media preparation failed*'
        @(Get-ChildItem -LiteralPath $Folder).Count | Should -Be 0
        @($Events) -join ',' | Should -Be 'cleanup,restart'
    }

    It 'fails closed for a <Kind> token' -ForEach @(
        @{ Kind = 'missing' }, @{ Kind = 'empty' }, @{ Kind = 'directory' }, @{ Kind = 'symlink' }
    ) {
        $token = Join-Path $Media 'client_configuration_token.tok'
        Remove-GuestFixture -Path $token
        switch ($Kind) {
            empty { New-Item -ItemType File -Path $token | Out-Null }
            directory { New-Item -ItemType Directory -Path $token | Out-Null }
            symlink { New-Item -ItemType Junction -Path $token -Target $Folder | Out-Null }
        }
        { & $Asset -TestRoot $Root } | Should -Throw '*vGPU license media preparation failed*'
        @(Get-ChildItem -LiteralPath $Folder).Count | Should -Be 0
        Should -Invoke Copy-Item -Times 0
        Should -Invoke Restart-Service -Times 1 -Exactly
    }

    It 'removes partial copies before restart and emits no payload on copy failure' {
        Mock Copy-Item {
            Set-Content -LiteralPath $Destination -Value 'SYNTHETIC-PARTIAL'
            throw 'SYNTHETIC-SECRET-ERROR'
        }
        try {
            & $Asset -TestRoot $Root
            throw 'Expected failure was missing'
        } catch {
            $_.Exception.Message | Should -Be 'vGPU license media preparation failed'
        }
        @(Get-ChildItem -LiteralPath $Folder).Count | Should -Be 0
        Should -Invoke Restart-Service -Times 1 -Exactly
    }

    It 'reports cleanup failure without copying or claiming a restart succeeded' {
        Mock Remove-Item { throw 'SYNTHETIC-SECRET-ERROR' }
        { & $Asset -TestRoot $Root } | Should -Throw '*vGPU license token cleanup failed*'
        Should -Invoke Remove-Item -Times 1 -Exactly
        Should -Invoke Copy-Item -Times 0
        Should -Invoke Restart-Service -Times 0
    }

    It 'reports a real locked-file cleanup error before copy or restart' {
        $stale = Join-Path $Folder 'old.tok'
        $handle = [IO.File]::Open($stale, [IO.FileMode]::Open, [IO.FileAccess]::Read, [IO.FileShare]::None)
        try {
            { & $Asset -TestRoot $Root } | Should -Throw '*vGPU license token cleanup failed*'
            Test-Path -LiteralPath $stale | Should -BeTrue
            Should -Invoke Remove-Item -Times 1 -Exactly
            Should -Invoke Copy-Item -Times 0
            Should -Invoke Restart-Service -Times 0
        } finally {
            $handle.Dispose()
        }
    }

    It 'reports service restart failure' {
        Mock Restart-Service { throw 'SYNTHETIC-SECRET-ERROR' }
        { & $Asset -TestRoot $Root } | Should -Throw '*vGPU license client restart failed*'
    }

    It 'rejects fixture cleanup outside the owned TestDrive subdirectory' {
        $outside = Join-Path $TestDrive ([guid]::NewGuid().ToString() + '.tok')
        Set-Content -LiteralPath $outside -Value 'SYNTHETIC-OUTSIDE'
        { Remove-GuestFixture -Path $outside } | Should -Throw '*Fixture cleanup outside owned TestDrive root*'
        Get-Content -LiteralPath $outside | Should -Be 'SYNTHETIC-OUTSIDE'
    }

    It 'rejects a foreign sandbox before filesystem or service operations' {
        { & $Asset -TestRoot 'C:\' } | Should -Throw '*Invalid sandbox invocation*'
        Should -Invoke Remove-Item -Times 0
        Should -Invoke Restart-Service -Times 0
    }
}

Describe 'Nonempty Windows CI selection' {
    BeforeAll {
        $workflow = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot '../.github/workflows/vgpu-guest.yml')
        $guard = [regex]::Match($workflow, '(?ms)^          if \(\$null -eq \$result.*?^          \}')
        if (-not $guard.Success) { throw 'Missing nonempty Pester selection guard' }
        $SelectionGuard = [scriptblock]::Create($guard.Value)
    }

    It 'rejects a run with <Total> tests and <Passed> passes' -ForEach @(
        @{ Total = 0; Passed = 0 }, @{ Total = 4; Passed = 0 }
    ) {
        $result = [pscustomobject]@{ TotalCount = $Total; PassedCount = $Passed }
        { & $SelectionGuard } | Should -Throw '*No vGPU guest tests passed*'
    }

    It 'accepts a nonempty passing run' {
        $result = [pscustomobject]@{ TotalCount = 1; PassedCount = 1 }
        { & $SelectionGuard } | Should -Not -Throw
    }
}

Describe 'Documented Windows startup task wiring' {
    It 'registers only the owned task under SYSTEM at startup without a policy bypass' {
        Mock New-ScheduledTaskAction { [Microsoft.Management.Infrastructure.CimInstance]::new('MSFT_TaskAction', 'root/Microsoft/Windows/TaskScheduler') }
        Mock New-ScheduledTaskTrigger { [Microsoft.Management.Infrastructure.CimInstance]::new('MSFT_TaskTrigger', 'root/Microsoft/Windows/TaskScheduler') }
        Mock New-ScheduledTaskPrincipal { [Microsoft.Management.Infrastructure.CimInstance]::new('MSFT_TaskPrincipal', 'root/Microsoft/Windows/TaskScheduler') }
        Mock Register-ScheduledTask { }
        $guide = Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot '../content/en/docs/next/virtualization/vgpu-licensing.md')
        $blocks = [regex]::Matches($guide, '(?s)```powershell\r?\n(.*?)```')
        $task = @($blocks | Where-Object { $_.Groups[1].Value.Contains('Register-ScheduledTask') })
        $task.Count | Should -Be 1
        $code = $task[0].Groups[1].Value
        $code | Should -Not -Match 'ExecutionPolicy|Bypass|Unregister-ScheduledTask'
        & ([scriptblock]::Create($code)) | Out-Null
        Should -Invoke New-ScheduledTaskAction -Times 1 -Exactly -ParameterFilter {
            $Execute -eq (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -and
            $Argument -eq '-NoProfile -NonInteractive -File "C:\ProgramData\Cozystack\Set-CozystackVgpuLicense.ps1"'
        }
        Should -Invoke New-ScheduledTaskTrigger -Times 1 -Exactly -ParameterFilter { $AtStartup }
        Should -Invoke New-ScheduledTaskPrincipal -Times 1 -Exactly -ParameterFilter {
            $UserId -eq 'SYSTEM' -and $LogonType -eq 'ServiceAccount' -and $RunLevel -eq 'Highest'
        }
        Should -Invoke Register-ScheduledTask -Times 1 -Exactly -ParameterFilter {
            $TaskName -eq 'Cozystack-vGPU-License' -and $Force
        }
    }
}
