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
 "profiles": {"defaults": {"font":{"face":"keep-font"}}, "list":[{"guid":"keep-guid","colorScheme":"old","opacity":85,"useAcrylic":false},]},
 "schemes": [{"name":"unrelated","background":"#123456"},{"name":"Chocolatier Light"},{"name":"Kimbie Light","background":"#FFFFFF"}],
}
'@)
    [IO.File]::WriteAllText($schemes, '[{"name":"Chocolatier"},{"name":"Kimbie Light","background":"#FBEBD4"}]')
    $original = [IO.File]::ReadAllText($settings)
    & "$PSScriptRoot\Apply-Theme.ps1" -Mode light -SchemesPath $schemes -SettingsPath $settings -CheckOnly
    if ([IO.File]::ReadAllText($settings) -ne $original) { throw 'Preflight changed settings' }
    & "$PSScriptRoot\Apply-Theme.ps1" -Mode light -SchemesPath $schemes -SettingsPath $settings
    $config = [IO.File]::ReadAllText($settings) | ConvertFrom-Json
    if ($config.custom -ne 'https://example.com/a//b' -or $config.defaultProfile -ne 'keep-guid' -or $config.profiles.defaults.font.face -ne 'keep-font' -or $config.profiles.list[0].opacity -ne 75) { throw 'Unrelated setting changed' }
    if ($config.profiles.defaults.opacity -ne 75 -or -not $config.profiles.defaults.useAcrylic -or -not $config.profiles.list[0].useAcrylic) { throw 'Opacity/acrylic update failed' }
    if ($config.theme -ne 'light' -or $config.profiles.list[0].colorScheme -ne 'Kimbie Light' -or $config.schemes.Count -ne 3) { throw 'Theme update failed' }
    if ($config.profiles.defaults.colorScheme -ne 'Kimbie Light' -or @($config.schemes | Where-Object name -eq 'Chocolatier Light').Count -ne 0 -or @($config.schemes | Where-Object name -eq 'Kimbie Light').Count -ne 1 -or ($config.schemes | Where-Object name -eq 'Kimbie Light').background -ne '#FBEBD4') { throw 'Scheme migration failed' }
    $before = [IO.File]::ReadAllText($settings)
    & "$PSScriptRoot\Apply-Theme.ps1" -Mode light -SchemesPath $schemes -SettingsPath $settings
    if ((Get-ChildItem "$settings.dotfiles-*.bak").Count -ne 1 -or [IO.File]::ReadAllText($settings) -ne $before) { throw 'Repeated apply not idempotent' }
    [IO.File]::WriteAllText($settings, '{bad json')
    $rejected = $false
    try { & "$PSScriptRoot\Apply-Theme.ps1" -Mode dark -SchemesPath $schemes -SettingsPath $settings } catch { $rejected = $true }
    if (-not $rejected -or [IO.File]::ReadAllText($settings) -ne '{bad json') { throw 'Malformed JSON was modified' }
    Write-Output 'PASS: JSONC, preservation, profile overrides, backup, idempotence, malformed JSON'
} finally { Remove-Item -LiteralPath $temporary -Recurse -Force }
