$ErrorActionPreference = 'Stop'
$temporary = Join-Path ([IO.Path]::GetTempPath()) ('dotfiles-theme-test-' + [guid]::NewGuid())
[IO.Directory]::CreateDirectory($temporary) | Out-Null
try {
    $settings = Join-Path $temporary 'settings.json'
    $schemes = Join-Path $temporary 'schemes.json'
    [IO.File]::WriteAllText($settings, @'
{
 // JSONC must parse without damaging URL strings.
 "custom": "https://example.com/a//b",
 "defaultProfile": "keep-guid",
 "profiles": {"defaults": {"font":{"face":"keep-font"}}, "list":[{"guid":"keep-guid","colorScheme":"old","opacity":85},]},
 "schemes": [{"name":"unrelated","background":"#123456"}],
}
'@)
    [IO.File]::WriteAllText($schemes, '[{"name":"Chocolatier"},{"name":"Chocolatier Light"}]')
    & "$PSScriptRoot\Apply-Theme.ps1" -Mode light -SchemesPath $schemes -SettingsPath $settings
    $config = [IO.File]::ReadAllText($settings) | ConvertFrom-Json
    if ($config.custom -ne 'https://example.com/a//b' -or $config.defaultProfile -ne 'keep-guid' -or $config.profiles.defaults.font.face -ne 'keep-font' -or $config.profiles.list[0].opacity -ne 85) { throw 'Unrelated setting changed' }
    if ($config.theme -ne 'light' -or $config.profiles.list[0].colorScheme -ne 'Chocolatier Light' -or $config.schemes.Count -ne 3) { throw 'Theme update failed' }
    $before = [IO.File]::ReadAllText($settings)
    & "$PSScriptRoot\Apply-Theme.ps1" -Mode light -SchemesPath $schemes -SettingsPath $settings
    if ((Get-ChildItem "$settings.dotfiles-*.bak").Count -ne 1 -or [IO.File]::ReadAllText($settings) -ne $before) { throw 'Repeated apply not idempotent' }
    [IO.File]::WriteAllText($settings, '{bad json')
    $rejected = $false
    try { & "$PSScriptRoot\Apply-Theme.ps1" -Mode dark -SchemesPath $schemes -SettingsPath $settings } catch { $rejected = $true }
    if (-not $rejected -or [IO.File]::ReadAllText($settings) -ne '{bad json') { throw 'Malformed JSON was modified' }
    Write-Output 'PASS: JSONC, preservation, profile overrides, backup, idempotence, malformed JSON'
} finally { Remove-Item -LiteralPath $temporary -Recurse -Force }
