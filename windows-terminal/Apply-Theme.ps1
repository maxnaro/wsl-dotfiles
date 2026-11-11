[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('dark', 'light')][string]$Mode,
    [Parameter(Mandatory)][string]$SchemesPath,
    [string]$SettingsPath,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
if (-not $SettingsPath) {
    $candidates = @(
        "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json",
        "$env:LOCALAPPDATA\Packages\Microsoft.WindowsTerminalPreview_8wekyb3d8bbwe\LocalState\settings.json",
        "$env:LOCALAPPDATA\Microsoft\Windows Terminal\settings.json"
    )
    $SettingsPath = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
    if (-not $SettingsPath) { Write-Output 'Windows Terminal not installed; skipped.'; return }
}
$text = [IO.File]::ReadAllText($SettingsPath)
# Preserve quoted strings when stripping JSONC comments and trailing commas.
$json = [regex]::Replace($text, '("(?:\\.|[^"\\])*")|(/\*[\s\S]*?\*/|//[^\r\n]*)', {
    param($match)
    if ($match.Groups[1].Success) { return $match.Value }; return ' '
})
$json = [regex]::Replace($json, '("(?:\\.|[^"\\])*")|,(\s*[}\]])', {
    param($match)
    if ($match.Groups[1].Success) { return $match.Value }; return $match.Groups[2].Value
})
$config = $json | ConvertFrom-Json
$schemes = [IO.File]::ReadAllText($SchemesPath) | ConvertFrom-Json
function Put($object, $name, $value) { $object | Add-Member -NotePropertyName $name -NotePropertyValue $value -Force }
if (-not $config.profiles) { Put $config 'profiles' ([pscustomobject]@{}) }
if (-not $config.profiles.defaults) { Put $config.profiles 'defaults' ([pscustomobject]@{}) }
$name = if ($Mode -eq 'dark') { 'Chocolatier' } else { 'Kimbie Light' }
Put $config 'theme' $Mode
Put $config.profiles.defaults 'colorScheme' $name
Put $config.profiles.defaults 'opacity' 75
Put $config.profiles.defaults 'useAcrylic' $true
foreach ($profile in $config.profiles.list) {
    if ($profile.PSObject.Properties['opacity']) { Put $profile 'opacity' 75 }
    if ($profile.PSObject.Properties['useAcrylic']) { Put $profile 'useAcrylic' $true }
    if ($profile.PSObject.Properties['colorScheme']) { Put $profile 'colorScheme' $name }
}
Put $config 'schemes' @(@($config.schemes | Where-Object { $_.name -notin @('Chocolatier', 'Chocolatier Light', 'Gruvbox Light', 'Kimbie Light') }) + @($schemes))
$updated = $config | ConvertTo-Json -Depth 100
if (($json | ConvertFrom-Json | ConvertTo-Json -Depth 100) -eq $updated) { return }
if ($CheckOnly) {
    $directory = Split-Path $SettingsPath
    if ((Get-Item -LiteralPath $SettingsPath).IsReadOnly) { throw 'Windows Terminal settings are read-only' }
    $probe = Join-Path $directory ([IO.Path]::GetRandomFileName())
    try {
        $stream = [IO.File]::Open($probe, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
        $stream.Dispose()
    } finally { if (Test-Path -LiteralPath $probe) { Remove-Item -LiteralPath $probe } }
    return
}
$backup = $SettingsPath + '.dotfiles-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fffffff') + '.bak'
Copy-Item -LiteralPath $SettingsPath -Destination $backup
$temporary = Join-Path (Split-Path $SettingsPath) ([IO.Path]::GetRandomFileName())
try {
    [IO.File]::WriteAllText($temporary, $updated, (New-Object Text.UTF8Encoding $false))
    [IO.File]::Replace($temporary, $SettingsPath, $backup)
} finally { if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary } }
Write-Output "Windows Terminal updated. Backup: $backup"
