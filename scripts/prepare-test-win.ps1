# 1. 找到你的 Blender addons 目录（根据实际版本号调整）
# Windows 示例（Blender 4.2）：

# find latest blender version in AppData\Blender Foundation\Blender
$blenderVersion = Get-ChildItem "$env:APPDATA\Blender Foundation\Blender" | Sort-Object Name -Descending | Select-Object -First 1

$blenderAddons = "$env:APPDATA\Blender Foundation\Blender\$($blenderVersion.Name)\scripts\addons"

# Project root is one level above the scripts/ directory
$projectRoot = Split-Path -Parent $PSScriptRoot

# Remove existing link if present
if (Test-Path "$blenderAddons\blender_sync") {
    Remove-Item "$blenderAddons\blender_sync" -Recurse -Force
}

# 2. 创建目录联结（相当于符号链接）
New-Item -ItemType Junction -Path "$blenderAddons\blender_sync" -Target "$projectRoot\blender_sync"
