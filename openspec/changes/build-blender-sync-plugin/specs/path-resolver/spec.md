## ADDED Requirements

### Requirement: Cross-platform user resource paths
系统 SHALL 使用 `bpy.utils.user_resource()` 定位 Blender 用户资源目录，不硬编码系统路径。

#### Scenario: Get config path on any platform
- **WHEN** 在 Windows、macOS 或 Linux 上调用 config 路径解析
- **THEN** 返回当前平台 Blender 版本的 config 目录绝对路径
- **AND** 路径来源于 Blender API 返回值

#### Scenario: Get scripts path on any platform
- **WHEN** 调用 scripts 路径解析
- **THEN** 返回 `scripts/` 子目录路径（含 addons、presets）

#### Scenario: Get extensions path on any platform
- **WHEN** 调用 extensions 路径解析
- **THEN** 返回当前 Blender 版本的 extensions 目录路径

### Requirement: Plugin own writable directory
系统 SHALL 使用 `bpy.utils.extension_path_user(__package__, create=True)` 获取插件可写目录，用于存放 Git staging repo、状态文件、锁文件和备份。

#### Scenario: Get plugin data directory
- **WHEN** 首次调用插件数据目录解析
- **THEN** 自动创建 `blender-sync-state/` 目录
- **AND** 返回该目录的绝对路径

### Requirement: Sync target path list
系统 SHALL 根据配置返回需要同步的文件和目录清单：
- `config/userpref.blend`
- `config/startup.blend`
- `config/bookmarks.txt`
- `config/recent-files.txt`（默认关闭，可配置）
- `scripts/presets/`
- `scripts/addons/` 中用户安装的插件
- `extensions/` 中用户安装的扩展

#### Scenario: Default sync targets
- **WHEN** 用户使用默认配置
- **THEN** 返回清单包含 userpref.blend、startup.blend、bookmarks.txt、presets、addons、extensions
- **AND** recent-files.txt 不在清单中

#### Scenario: recent-files enabled
- **WHEN** 用户在配置中启用 recent-files 同步
- **THEN** 返回清单包含 recent-files.txt

#### Scenario: Exclude patterns applied
- **WHEN** 用户配置了排除规则（如 `*.log`）
- **THEN** 匹配规则的路径不在返回清单中
