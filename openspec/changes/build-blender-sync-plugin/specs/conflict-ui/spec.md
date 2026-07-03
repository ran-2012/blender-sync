## ADDED Requirements

### Requirement: Conflict file list display
系统 SHALL 在 UI 面板展示所有冲突文件，包含文件路径、大小和最后修改时间。

#### Scenario: Conflict detected and displayed
- **WHEN** 同步进入 conflict 状态
- **THEN** 面板展示冲突文件列表
- **AND** 每个文件显示相对路径和本地/远端的时间戳对比

### Requirement: Overwrite local action
系统 SHALL 提供"覆盖本地"按钮，用远端版本完全覆盖本地设置。

#### Scenario: User overwrites local
- **WHEN** 用户点击"覆盖本地"并确认
- **THEN** 系统丢弃本地未推送变更
- **AND** 应用远端版本到 Blender 用户目录
- **AND** 状态返回 idle

### Requirement: Overwrite remote action
系统 SHALL 提供"覆盖远端"按钮，用本地版本覆盖远端。

#### Scenario: User overwrites remote
- **WHEN** 用户点击"覆盖远端"并确认
- **THEN** 系统保留本地快照
- **AND** 使用 `--force-with-lease` 推送到远端
- **AND** 状态返回 idle

### Requirement: Per-file conflict resolution
在手动解决模式下，系统 SHALL 允许用户逐文件选择保留 local 或 remote 版本。

#### Scenario: Binary file resolution
- **WHEN** 冲突文件为二进制格式（.blend 等）
- **THEN** 系统展示 local 和 remote 版本的时间和大小
- **AND** 用户选择保留 local 或 remote

#### Scenario: Text file resolution
- **WHEN** 冲突文件为文本格式
- **THEN** 系统提供选项：使用本地版本、使用远端版本、打开外部编辑器
- **AND** 用户编辑后执行 `git add` 和 `git merge --continue`

### Requirement: Abort manual resolve
系统 SHALL 提供取消手动解决的能力。

#### Scenario: User aborts manual resolution
- **WHEN** 用户在手动解决过程中选择取消
- **THEN** 系统执行 `git merge --abort`
- **AND** 恢复冲突前的状态

### Requirement: Conflict resolution commit
用户解决冲突后，系统 SHALL 生成清晰的提交记录。

#### Scenario: Resolution committed
- **WHEN** 用户完成所有冲突文件的处理
- **THEN** 系统生成合并提交
- **AND** 提交消息标识为冲突解决
