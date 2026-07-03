## ADDED Requirements

### Requirement: Plugin registration
插件 SHALL 以标准 Blender 多文件插件形式注册，包含 `bl_info` 字典，支持 Blender 4.x/5.x。

#### Scenario: Plugin installed and enabled
- **WHEN** 用户通过 Blender Preferences 安装插件 zip 包并启用
- **THEN** 插件在 Add-ons 列表中显示为已启用
- **AND** 侧栏面板（Sidebar）中出现 Blender Sync 面板

### Requirement: AddonPreferences configuration
插件 SHALL 通过 `AddonPreferences` 提供配置界面，保存并持久化以下配置项：
- Git remote URL
- branch（默认 `main`）
- sync interval（默认 0 表示仅手动）
- auto sync enabled
- startup remote check enabled
- conflict policy（默认 `manual`）
- plugin size threshold（默认 50 MB）
- include/exclude patterns

#### Scenario: Save and persist preferences
- **WHEN** 用户在 Preferences 面板修改 remote URL 并保存
- **THEN** 配置持久化在 Blender 用户偏好中
- **AND** 下次启动 Blender 时配置保持不丢失

#### Scenario: Default values
- **WHEN** 插件首次启用且用户未配置任何选项
- **THEN** 所有配置项显示设计文档中定义的默认值

### Requirement: Git availability check
插件启动时 SHALL 检测系统是否安装了 Git。

#### Scenario: Git not installed
- **WHEN** 系统未安装 Git 或 `git --version` 执行失败
- **THEN** 面板状态显示 "Git not found"
- **AND** 所有同步按钮禁用

#### Scenario: Git available
- **WHEN** `git --version` 返回成功
- **THEN** 面板显示 Git 版本号
- **AND** 同步按钮根据 remote 配置状态决定是否可用

### Requirement: UI status panel
插件 SHALL 在 Blender 3D View 侧栏提供状态面板，显示：
- Git 版本和可用性
- Remote URL 和分支
- 上次同步时间
- 当前同步状态（idle / checking / syncing / conflict / error）
- 各操作按钮

#### Scenario: Idle status display
- **WHEN** 同步状态为 idle 且上次同步成功
- **THEN** 面板显示 "Last sync: <time>" 和 "Status: Up to date"

#### Scenario: Error status display
- **WHEN** 同步过程发生错误
- **THEN** 面板显示错误摘要
- **AND** 提供 "View Log" 按钮查看详细信息
