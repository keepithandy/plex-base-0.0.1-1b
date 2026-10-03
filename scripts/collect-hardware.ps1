<#
.SYNOPSIS
  Prints a read-only Windows hardware inventory for the Plex training profile.
.DESCRIPTION
  Uses Windows CIM/WMI and, when installed, nvidia-smi. It does not write files,
  install software, change settings, or inspect usernames or machine names.
  Compatible with Windows PowerShell 5.1 and PowerShell 7 on Windows.
#>

$ErrorActionPreference = 'Stop'

function ConvertTo-GiB {
  param([Parameter(Mandatory = $true)][UInt64]$Bytes)
  return [Math]::Round(($Bytes / 1GB), 2)
}

function Get-CimSection {
  param([Parameter(Mandatory = $true)][string]$ClassName)
  try {
    return [PSCustomObject]@{ status = 'available'; items = @(Get-CimInstance -ClassName $ClassName -ErrorAction Stop) }
  }
  catch {
    return [PSCustomObject]@{ status = 'unavailable'; items = @(); reason = 'Windows CIM query failed.' }
  }
}

$cpuSection = Get-CimSection -ClassName 'Win32_Processor'
$computerSection = Get-CimSection -ClassName 'Win32_ComputerSystem'
$gpuSection = Get-CimSection -ClassName 'Win32_VideoController'
$diskSection = Get-CimSection -ClassName 'Win32_LogicalDisk'

$cpu = if ($cpuSection.status -eq 'available' -and $cpuSection.items.Count -gt 0) {
  $processors = @($cpuSection.items)
  $logicalCount = 0
  foreach ($processor in $processors) {
    if ($null -ne $processor.NumberOfLogicalProcessors) {
      $logicalCount += [int]$processor.NumberOfLogicalProcessors
    }
  }
  [PSCustomObject]@{
    status = 'available'
    models = @($processors | ForEach-Object { [string]$_.Name } | Where-Object { $_ } | Select-Object -Unique)
    logicalProcessorCount = $logicalCount
  }
}
else {
  [PSCustomObject]@{ status = 'unavailable'; reason = 'CPU details were not returned by Windows CIM.' }
}

$memory = if ($computerSection.status -eq 'available' -and $computerSection.items.Count -gt 0 -and
  $null -ne $computerSection.items[0].TotalPhysicalMemory) {
  $ramBytes = [UInt64]$computerSection.items[0].TotalPhysicalMemory
  [PSCustomObject]@{ status = 'available'; totalBytes = $ramBytes; totalGiB = (ConvertTo-GiB -Bytes $ramBytes) }
}
else {
  [PSCustomObject]@{ status = 'unavailable'; reason = 'Total physical memory was not returned by Windows CIM.' }
}

$gpuNames = if ($gpuSection.status -eq 'available' -and $gpuSection.items.Count -gt 0) {
  $names = @($gpuSection.items | ForEach-Object { [string]$_.Name } | Where-Object { $_ } | Select-Object -Unique)
  if ($names.Count -gt 0) {
    [PSCustomObject]@{ status = 'available'; names = $names }
  }
  else {
    [PSCustomObject]@{ status = 'unavailable'; reason = 'Windows CIM returned no GPU names.' }
  }
}
else {
  [PSCustomObject]@{ status = 'unavailable'; reason = 'GPU names were not returned by Windows CIM.' }
}

# Win32_VideoController.AdapterRAM is often capped or inaccurate, so it is not
# used as a VRAM value. nvidia-smi provides the reliable free/total VRAM query
# for supported NVIDIA devices; other adapters are clearly reported unknown.
$nvidiaSmi = Get-Command -Name 'nvidia-smi.exe' -CommandType Application -ErrorAction SilentlyContinue |
  Select-Object -First 1
$gpuMemory = if ($null -eq $nvidiaSmi) {
  [PSCustomObject]@{
    status = 'unavailable'
    reason = 'nvidia-smi is not installed; available memory for other GPU vendors is not reliably queried.'
    devices = @()
  }
}
else {
  try {
    $queryOutput = @(& $nvidiaSmi.Source '--query-gpu=name,memory.total,memory.free' '--format=csv,noheader,nounits' 2>$null)
    $queryExitCode = $LASTEXITCODE
    if ($queryExitCode -ne 0 -or $queryOutput.Count -eq 0) {
      throw 'NVIDIA query unavailable.'
    }
    $devices = @()
    foreach ($line in $queryOutput) {
      $columns = ([string]$line -split ',', 3 | ForEach-Object { $_.Trim() })
      if ($columns.Count -ne 3) { continue }
      $hasTotal = $columns[1] -match '^\d+$'
      $hasFree = $columns[2] -match '^\d+$'
      $totalMiB = if ($hasTotal) { [UInt64]$columns[1] } else { $null }
      $freeMiB = if ($hasFree) { [UInt64]$columns[2] } else { $null }
      $devices += [PSCustomObject]@{
        name = $columns[0]
        totalMiB = if ($hasTotal) { $totalMiB } else { $null }
        availableMiB = if ($hasFree) { $freeMiB } else { $null }
        status = if ($hasTotal -and $hasFree) { 'available' } else { 'unavailable' }
      }
    }
    if ($devices.Count -eq 0) { throw 'No NVIDIA adapters returned memory information.' }
    [PSCustomObject]@{ status = 'available'; units = 'MiB'; devices = $devices }
  }
  catch {
    [PSCustomObject]@{
      status = 'unavailable'
      reason = 'nvidia-smi was found but could not return GPU memory information.'
      devices = @()
    }
  }
}

$fixedDrives = if ($diskSection.status -eq 'available') {
  $drives = @($diskSection.items | Where-Object { $_.DriveType -eq 3 -and $_.DeviceID })
  $driveResults = @()
  foreach ($drive in $drives) {
    if ($null -eq $drive.FreeSpace -or $null -eq $drive.Size) { continue }
    $freeBytes = [UInt64]$drive.FreeSpace
    $sizeBytes = [UInt64]$drive.Size
    $driveResults += [PSCustomObject]@{
      drive = [string]$drive.DeviceID
      freeBytes = $freeBytes
      freeGiB = (ConvertTo-GiB -Bytes $freeBytes)
      totalBytes = $sizeBytes
      totalGiB = (ConvertTo-GiB -Bytes $sizeBytes)
    }
  }
  if ($driveResults.Count -gt 0) {
    [PSCustomObject]@{ status = 'available'; drives = $driveResults }
  }
  else {
    [PSCustomObject]@{ status = 'unavailable'; reason = 'No fixed local drive capacity was returned by Windows CIM.'; drives = @() }
  }
}
else {
  [PSCustomObject]@{ status = 'unavailable'; reason = 'Fixed drive information was not returned by Windows CIM.'; drives = @() }
}

$report = [ordered]@{
  schemaVersion = 1
  collectedAtUtc = [DateTime]::UtcNow.ToString('o')
  collection = 'Read-only Windows CIM; nvidia-smi used only when already installed.'
  cpu = $cpu
  memory = $memory
  gpuNames = $gpuNames
  gpuMemory = $gpuMemory
  fixedDrives = $fixedDrives
  userInputs = [ordered]@{
    trainingBudget = 'unknown'
    acceptableTrainingDuration = 'unknown'
    inferenceRequirements = 'Windows local inference; CPU support required; optional GPU acceleration.'
  }
}

$report | ConvertTo-Json -Depth 8
