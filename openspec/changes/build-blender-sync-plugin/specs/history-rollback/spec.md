## ADDED Requirements

### Requirement: History list display
系统 SHALL 在 UI 中展示最近 N 个同步提交的历史列表。

#### Scenario: View commit history
- **WHEN** 用户点击 "View History"
- **THEN** 显示最近 20 个同步提交列表
- **AND** 每条记录包含 commit SHA（短格式）、提交消息、时间、设备名

### Requirement: Commit detail view
系统 SHALL 支持查看单个 commit 的变更摘要。

#### Scenario: Show commit changes
- **WHEN** 用户在历史列表中选择某个 commit
- **THEN** 展示该 commit 变更的文件列表（`git show --stat`）
- **AND** 展示每个文件的变更类型（新增/修改/删除）

### Requirement: Preview rollback diff
回滚前，系统 SHALL 展示当前 staging 与目标 commit 的差异。

#### Scenario: Preview before rollback
- **WHEN** 用户选择回滚到某 commit 但未确认
- **THEN** 展示 `git diff <commit>..HEAD` 的摘要
- **AND** 用户确认后才执行回滚

### Requirement: Rollback execution
系统 SHALL 执行从 staging repo checkout 目标 commit 文件的回滚操作。

#### Scenario: Rollback with new commit
- **WHEN** 用户确认回滚
- **THEN** 系统创建当前本地备份
- **AND** 从目标 commit checkout 文件
- **AND** 创建回滚提交
- **AND** 应用 staging 到 Blender 用户目录

#### Scenario: Rollback does not rewrite history
- **WHEN** 回滚完成
- **THEN** 生成新的 "Rollback to <commit>" 提交
- **AND** 不执行 `git reset --hard` 改写历史

### Requirement: Optional push after rollback
回滚后，系统 SHALL 允许用户选择是否将回滚提交推送到远端。

#### Scenario: Push rollback to remote
- **WHEN** 用户选择推送回滚提交
- **THEN** 回滚提交被 push 到远端
- **AND** 其他设备可同步到此回滚结果

#### Scenario: Keep rollback local
- **WHEN** 用户不选择推送
- **THEN** 回滚提交仅保留在本地
- **AND** 下次同步时可能再次出现分歧

### Requirement: Post-rollback sync capability
回滚后，系统 SHALL 仍可正常执行后续同步操作。

#### Scenario: Sync after rollback
- **WHEN** 回滚完成后触发同步
- **THEN** 同步流程正常工作
- **AND** 远端状态与本地回滚后状态正确比较
