## ADDED Requirements

### Requirement: Git command execution
系统 SHALL 通过 `subprocess` 调用系统 `git` 命令，所有参数以数组形式传递，不拼接 shell 字符串。

#### Scenario: Execute git command successfully
- **WHEN** 调用 `git status --porcelain` 且 Git 可用
- **THEN** 返回 stdout 内容和退出码 0

#### Scenario: Git command failure
- **WHEN** Git 命令执行失败（非零退出码）
- **THEN** 返回错误信息包含 stderr 内容和退出码
- **AND** 错误信息写入日志文件

### Requirement: Ensure repo initialized
系统 SHALL 在指定路径创建 Git 仓库或确认已有仓库可用。

#### Scenario: Repo does not exist
- **WHEN** 目标路径不是 Git 仓库
- **THEN** 执行 `git init`、`git remote add origin <url>`、`git checkout -B <branch>`

#### Scenario: Repo already exists
- **WHEN** 目标路径已是 Git 仓库
- **THEN** 确认 remote 和 branch 配置正确
- **AND** 不再重复 init

### Requirement: Git status parsing
系统 SHALL 解析 `git status --porcelain` 输出，返回结构化状态信息。

#### Scenario: Working tree clean
- **WHEN** `git status --porcelain` 输出为空
- **THEN** 返回 `is_dirty: false`

#### Scenario: Working tree has changes
- **WHEN** `git status --porcelain` 有输出行
- **THEN** 返回 `is_dirty: true`
- **AND** 返回变更文件列表（新增/修改/删除）

### Requirement: Branch relation detection
系统 SHALL 在 fetch 后判断本地分支与远端分支的关系。

#### Scenario: Branches up to date
- **WHEN** 本地 HEAD 与 `origin/<branch>` 指向同一 commit
- **THEN** 返回 `up_to_date`

#### Scenario: Local ahead of remote
- **WHEN** 本地有远端不包含的新 commit
- **THEN** 返回 `local_ahead`

#### Scenario: Remote ahead of local
- **WHEN** 远端有本地不包含的新 commit
- **THEN** 返回 `remote_ahead`

#### Scenario: Branches diverged
- **WHEN** 本地和远端各有对方不包含的 commit
- **THEN** 返回 `diverged`

### Requirement: Commit all changes
系统 SHALL 执行 `git add -A` 和 `git commit` 提交所有变更。

#### Scenario: Commit with auto-generated message
- **WHEN** staging repo 有变更需要提交
- **THEN** 提交消息格式为 `Sync from <device-name> at <iso-time>`
- **AND** 返回新 commit 的 SHA

#### Scenario: Nothing to commit
- **WHEN** staging repo 无变更
- **THEN** 返回 None，不创建空提交

### Requirement: Fetch from remote
系统 SHALL 执行 `git fetch origin <branch>` 获取远端更新。

#### Scenario: Fetch succeeds
- **WHEN** remote 可访问且有新数据
- **THEN** fetch 完成，远端引用更新

#### Scenario: Fetch fails with authentication error
- **WHEN** remote 需要认证且未配置凭据
- **THEN** 返回错误，提示用户检查 Git 认证配置

#### Scenario: Fetch fails with network error
- **WHEN** remote 不可达（网络问题）
- **THEN** 返回错误，包含网络超时信息

### Requirement: Merge operations
系统 SHALL 支持 `git merge` 操作，包含 abort 能力。

#### Scenario: Fast-forward merge
- **WHEN** 本地无分叉，可 fast-forward
- **THEN** merge 成功，HEAD 指向远端最新 commit

#### Scenario: Merge conflict
- **WHEN** 出现合并冲突
- **THEN** 返回冲突状态，列出冲突文件

#### Scenario: Abort merge
- **WHEN** 用户决定取消合并
- **THEN** `git merge --abort` 恢复到合并前状态

### Requirement: Push operations
系统 SHALL 支持 `git push` 和 `git push --force-with-lease`。

#### Scenario: Normal push
- **WHEN** 本地领先于远端且无冲突
- **THEN** push 成功，远端更新

#### Scenario: Force push with lease
- **WHEN** 用户选择覆盖远端
- **THEN** 使用 `--force-with-lease` 推送
- **AND** 若远端有本地未知的新 commit，push 被拒绝

### Requirement: History log
系统 SHALL 执行 `git log --oneline --max-count=N` 获取提交历史。

#### Scenario: Get recent commits
- **WHEN** 请求最近 20 个提交
- **THEN** 返回最多 20 条记录，每条包含 SHA、消息、时间、作者

### Requirement: Checkout tree
系统 SHALL 支持从指定 commit checkout 文件到工作区。

#### Scenario: Checkout specific commit files
- **WHEN** 用户选择回滚到某 commit
- **THEN** `git checkout <commit> -- .` 更新 staging repo 文件到目标版本
- **AND** 不改变当前 HEAD（保留历史）
