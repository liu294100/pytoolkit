param(
    [string]$SelectedIndex = ""
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$candidates = New-Object System.Collections.Generic.List[string]
$seen = @{}

function Add-Candidate {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    if (-not (Test-Path $Path)) { return }
    $full = (Resolve-Path $Path).Path
    if ($seen.ContainsKey($full)) { return }
    $seen[$full] = $true
    $candidates.Add($full)
}

try {
    $lines = & py -0p 2>$null
    foreach ($line in $lines) {
        $m = [regex]::Match($line, '([A-Za-z]:\\.*python\.exe)$')
        if ($m.Success) {
            Add-Candidate $m.Groups[1].Value
        }
    }
} catch {
}

foreach ($name in @("python", "python3", "py")) {
    try {
        $cmds = Get-Command $name -ErrorAction SilentlyContinue
        foreach ($cmd in $cmds) {
            if ($cmd.Source) {
                Add-Candidate $cmd.Source
            }
        }
    } catch {
    }
}

if ($candidates.Count -eq 0) {
    Write-Host "No Python interpreter found"
    exit 1
}

Write-Host "Detected Python interpreters:"
for ($i = 0; $i -lt $candidates.Count; $i++) {
    Write-Host ("[{0}] {1}" -f ($i + 1), $candidates[$i])
}

$idx = $SelectedIndex
if ([string]::IsNullOrWhiteSpace($idx)) {
    $idx = Read-Host "Enter index number"
}

if ($idx -notmatch '^[1-9]\d*$') {
    Write-Host "Invalid input"
    exit 1
}

$n = [int]$idx
if ($n -lt 1 -or $n -gt $candidates.Count) {
    Write-Host "Input out of range"
    exit 1
}

$pythonExe = $candidates[$n - 1]
Write-Host ("Using: {0}" -f $pythonExe)
& $pythonExe "app.py"
exit $LASTEXITCODE
