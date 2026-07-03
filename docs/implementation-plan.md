# 实现计划

## 阶段 1：插件骨架

创建 Blender 插件包：

```text
blender_sync/
  __init__.py
  preferences.py
  operators.py
  panel.py
  scheduler.py
  sync_service.py
  git_adapter.py
  path_resolver.py
  snapshot.py
  manifest.py
  status_store.py
  filters.py
```

功能：

- 注册 `AddonPreferences`。
- 注册手动操作按钮。
- 显示 Git、remote、last sync、status。
- 检查 `git --version`。

验收：

- 插件可安装和启用。
- Preferences 可保存 remote、branch、interval、threshold。
- Git 不存在时显示错误状态。

## 阶段 2：路径和 Snapshot

实现模块：

- `path_resolver.py`
- `filters.py`
- `snapshot.py`
- `manifest.py`

功能：

- 定位 `CONFIG`、`SCRIPTS`、`EXTENSIONS`。
- 采集允许同步的文件到 staging repo。
- 计算插件目录大小并应用阈值。
- 生成 `manifest.json`。
- 创建 `.gitignore` 和 `.gitattributes`。

验收：

- 三个平台路径使用 Blender API 返回值，不硬编码系统路径。
- 超过阈值的插件不复制。
- manifest 可解释每个 included/skipped path。

## 阶段 3：Git Adapter

实现模块：

- `git_adapter.py`

接口：

```python
class GitAdapter:
    def ensure_repo(self, repo_path: str, remote_url: str, branch: str) -> None: ...
    def status(self) -> GitStatus: ...
    def commit_all(self, message: str) -> str | None: ...
    def fetch(self, remote: str, branch: str) -> None: ...
    def relation(self, branch: str, upstream: str) -> BranchRelation: ...
    def merge_remote(self, upstream: str) -> MergeResult: ...
    def abort_merge(self) -> None: ...
    def push(self, remote: str, branch: str) -> None: ...
    def force_push_with_lease(self, remote: str, branch: str) -> None: ...
    def log(self, limit: int) -> list[CommitInfo]: ...
    def checkout_tree(self, commit: str) -> None: ...
```

验收：

- 所有 Git 命令通过参数数组执行，不拼接 shell 字符串。
- 解析 `git status --porcelain`。
- 能区分 `up_to_date`、`local_ahead`、`remote_ahead`、`diverged`。
- Git 输出写入日志并返回可展示摘要。

## 阶段 4：同步服务

实现模块：

- `sync_service.py`
- `status_store.py`

同步入口：

```python
class SyncService:
    def check_remote(self) -> SyncResult: ...
    def sync_now(self, trigger: str) -> SyncResult: ...
    def push_local(self) -> SyncResult: ...
    def pull_remote(self) -> SyncResult: ...
    def resolve_conflict(self, strategy: ConflictStrategy) -> SyncResult: ...
    def rollback_to(self, commit: str, push: bool) -> SyncResult: ...
```

验收：

- 手动同步可完成 local commit、fetch、merge、push。
- remote ahead 可应用远端到用户目录。
- diverged 可进入 conflict 状态。
- 每次 apply 前创建备份。

## 阶段 5：调度和后台同步

实现模块：

- `scheduler.py`

功能：

- `register()` 注册启动 timer。
- 按 interval 检查远端。
- 后台任务使用锁文件去重。
- UI 读取 `status.json`。

验收：

- 启动不阻塞 Blender UI。
- 同步中再次点击按钮不会启动第二个任务。
- Blender 加载新文件后 timer 仍可继续工作。

## 阶段 6：冲突 UI

实现模块：

- `operators.py`
- `panel.py`

功能：

- 展示冲突文件列表。
- 覆盖本地。
- 覆盖远端。
- 二进制文件选择 local/remote。
- 文本文件打开外部编辑器或使用系统 mergetool。

验收：

- 冲突状态不会自动覆盖文件。
- 用户选择后生成清晰提交。
- `git merge --abort` 可取消手动解决。

## 阶段 7：历史和回滚

功能：

- 展示最近 N 个同步提交。
- 展示 commit 变更摘要。
- 回滚到目标 commit。
- 回滚后生成新提交。
- 可选推送回滚提交。

验收：

- 回滚前有本地备份。
- 回滚不会改写远端历史。
- 回滚后可再次同步。

## 阶段 8：发布和兼容性

功能：

- 打包为 Blender addon zip。
- 写安装说明。
- 写故障排查说明。
- 在 Blender 4.x/5.x 目标版本测试。

验收：

- Windows、macOS、Linux 可安装。
- 未安装 Git、认证失败、remote 不可达都有可读错误。
- 插件升级不删除用户同步 repo 和备份。

## 命令清单

初始化：

```text
git init
git remote add origin <remote-url>
git checkout -B <branch>
```

采集后提交：

```text
git add -A
git commit -m "Sync from <device> at <time>"
```

检查远端：

```text
git fetch origin <branch>
git rev-list --left-right --count HEAD...origin/<branch>
```

拉取远端：

```text
git merge --no-commit origin/<branch>
git commit -m "Merge remote sync from origin/<branch>"
```

覆盖本地：

```text
git reset --hard origin/<branch>
```

覆盖远端：

```text
git push --force-with-lease origin <branch>
```

历史：

```text
git log --oneline --decorate --max-count=50
git show --stat <commit>
```

回滚：

```text
git checkout <commit> -- .
git commit -m "Rollback to <commit>"
```

## 风险

| 风险 | 处理 |
| --- | --- |
| `userpref.blend` 是二进制 | 按整文件选择 local/remote，不做文本合并 |
| 插件包含大量资产 | 阈值过滤，默认跳过 |
| Git 认证失败 | 使用系统 Git 凭据，不在插件内保存密码 |
| Blender 线程崩溃风险 | 不使用常驻 Python 线程访问 Blender API |
| 跨平台换行差异 | `.gitattributes` 统一文本属性 |
| 误覆盖用户目录 | apply 前创建备份，失败后恢复 |
