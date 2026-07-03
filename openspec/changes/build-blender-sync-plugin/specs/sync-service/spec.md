## ADDED Requirements

### Requirement: Full sync flow
系统 SHALL 实现完整的同步流程：采集 → 提交 → fetch → 判断分支关系 → 合并或冲突处理 → push → 应用到 Blender 用户目录。

#### Scenario: Both sides up to date
- **WHEN** 本地无变更且远端无新 commit
- **THEN** 同步完成，状态返回 `up_to_date`
- **AND** 不执行 commit、merge、push 操作

#### Scenario: Local changes, remote up to date
- **WHEN** 本地有新变更但远端无新 commit
- **THEN** 系统提交本地快照
- **AND** push 到远端
- **AND** 状态返回同步成功

#### Scenario: Remote ahead, local clean
- **WHEN** 远端有新 commit 且本地无变更
- **THEN** 系统 fetch 后 fast-forward merge
- **AND** 将 staging repo 内容应用到 Blender 用户目录
- **AND** 状态返回同步成功

#### Scenario: Diverged branches
- **WHEN** 本地和远端各有对方不包含的 commit
- **THEN** 系统进入 conflict 状态
- **AND** 不自动覆盖任何文件

### Requirement: Backup before apply
系统 SHALL 在将远端变更应用到 Blender 用户目录之前创建本地备份。

#### Scenario: Backup created before apply
- **WHEN** 即将执行 apply（将 staging repo 写到用户目录）
- **THEN** 系统在 `backups/<timestamp>/` 下备份当前用户目录中的目标文件
- **AND** 备份时间戳使用 ISO 8601 格式

### Requirement: Apply to Blender user directory
系统 SHALL 将 staging repo 内容应用到 Blender 用户目录（反向复制）。

#### Scenario: Apply after remote pull
- **WHEN** 远端拉取完成后需要更新本地
- **THEN** staging repo 中的文件覆盖到 Blender 用户目录对应路径
- **AND** staging repo 中已删除的文件在用户目录中也删除

### Requirement: Conflict strategies
系统 SHALL 支持三种冲突处理策略：覆盖本地、覆盖远端、手动解决。

#### Scenario: Overwrite local
- **WHEN** 用户选择"覆盖本地"
- **THEN** 系统执行 `git reset --hard origin/<branch>`
- **AND** 将 staging repo 应用到 Blender 用户目录
- **AND** 丢弃本地未推送的变更

#### Scenario: Overwrite remote
- **WHEN** 用户选择"覆盖远端"
- **THEN** 系统提交本地快照
- **AND** 执行 `git push --force-with-lease`

#### Scenario: Manual resolve
- **WHEN** 用户选择"手动解决"
- **THEN** 系统保留冲突状态
- **AND** 展示冲突文件列表供用户逐文件处理

### Requirement: Rollback to commit
系统 SHALL 支持回滚到任意同步提交。

#### Scenario: Rollback with backup
- **WHEN** 用户选择目标 commit 并确认回滚
- **THEN** 系统先创建当前本地备份
- **AND** 从目标 commit checkout 文件到 staging repo
- **AND** 生成回滚提交（`git commit -m "Rollback to <commit>"`）
- **AND** 将 staging repo 应用到 Blender 用户目录

#### Scenario: Rollback does not rewrite history
- **WHEN** 回滚执行完成后
- **THEN** 回滚操作生成新 commit，不执行 `git reset --hard`

### Requirement: Manual sync entry points
系统 SHALL 提供以下手动同步入口，均可独立调用：
- `sync_now`：完整同步流程
- `check_remote`：仅检查远端
- `push_local`：仅推送本地
- `pull_remote`：仅拉取远端
- `resolve_conflict`：执行冲突策略
- `rollback_to`：回滚到指定 commit

#### Scenario: Manual sync while background task running
- **WHEN** 后台同步正在进行中且用户点击手动同步
- **THEN** 按钮显示当前任务状态
- **AND** 不启动第二个同步任务

### Requirement: Status store
系统 SHALL 通过 `status.json` 持久化当前同步状态。

#### Scenario: Status updated after sync
- **WHEN** 同步完成（成功或失败）
- **THEN** `status.json` 更新为最新状态
- **AND** UI 面板读取 status.json 刷新显示
