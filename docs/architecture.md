# 架构设计

## 作用

Blender Sync 在多台电脑之间同步 Blender 用户设置、用户插件和轻量资源。Git 保存历史和远端状态。插件提供启动检查、后台同步、手动同步、冲突处理、历史查看和回滚。

## 范围

同步内容：

- `config/userpref.blend`
- `config/startup.blend`
- `config/bookmarks.txt`
- `config/recent-files.txt`，默认关闭，可配置
- `scripts/presets`
- `scripts/addons` 中低于阈值的用户插件
- `extensions` 中低于阈值的用户扩展

不默认同步：

- 缓存目录
- 临时文件
- 渲染输出
- 大型资产库
- 系统插件
- 凭据、token、SSH key
- 机器专属路径配置

## 分层

| 层 | 职责 |
| --- | --- |
| UI | Preferences 面板、侧栏面板、操作按钮、状态展示 |
| Scheduler | 启动检查、定时同步、任务去重 |
| Sync Service | 采集、过滤、提交、拉取、应用、回滚 |
| Git Adapter | 执行 Git 命令、解析状态、处理错误 |
| Snapshot Store | staging 目录、manifest、状态文件、锁文件 |
| Path Resolver | 跨平台定位 Blender 用户目录和插件可写目录 |

## 数据目录

插件目录使用 `bpy.utils.extension_path_user(__package__, create=True)`：

```text
blender-sync-state/
  repo/                 # Git staging repo
  runtime/
    status.json          # UI 状态
    lock                 # 同步锁
    last_error.log
  backups/
    <timestamp>/         # 应用远端前的本地备份
```

真实 Blender 用户目录只在采集和应用阶段读写。Git 只管理 `repo/`。

## Snapshot

staging repo 内部结构：

```text
config/
  userpref.blend
  startup.blend
  bookmarks.txt
scripts/
  presets/
  addons/
extensions/
manifest.json
.gitignore
.gitattributes
```

`manifest.json` 保存：

- Blender version
- OS
- sync schema version
- included paths
- excluded paths
- plugin size threshold
- file hash
- last exported time

机器本地字段不要进入 manifest，例如本机用户名、绝对 HOME 路径、Git 凭据。

## 同步流程

1. `register()` 注册 timer。
2. timer 检查 remote 配置、Git 可用性和同步锁。
3. 采集 Blender 用户目录到 staging repo。
4. `git status --porcelain` 检查本地变化。
5. 有变化时提交本地快照。
6. `git fetch origin <branch>` 检查远端。
7. 无分歧时 fast-forward 或 push。
8. 有分歧时按策略处理。
9. 同步成功后把 staging repo 应用回 Blender 用户目录。
10. 更新 `status.json`。

## 启动检查

启动检查只做轻量任务：

- 检查 Git 是否存在。
- 检查 remote 是否配置。
- 读取上次同步状态。
- 异步触发 `git fetch`。

启动时不直接执行耗时 merge 或 apply。发现远端更新后，状态显示为 `remote_update_available`，再按用户设置决定自动拉取或等待用户点击。

## 后台同步

后台同步由 `bpy.app.timers` 调度。timer 本身不执行长时间工作，只启动短生命周期 Git 子进程或分阶段任务。

状态机：

| 状态 | 含义 |
| --- | --- |
| `idle` | 空闲 |
| `checking_remote` | 检查远端 |
| `exporting_snapshot` | 采集本地设置 |
| `committing_local` | 提交本地变化 |
| `pulling_remote` | 拉取远端 |
| `applying_snapshot` | 应用到 Blender 用户目录 |
| `conflict` | 需要用户处理 |
| `error` | 同步失败 |

同一时间只允许一个同步任务。锁文件包含 PID、开始时间、操作类型。锁超时后可由用户清理。

## 冲突处理

冲突来源：

- 同一设置文件被两台电脑修改。
- 插件目录同名文件被修改。
- 一端删除文件，另一端修改文件。
- 二进制文件无法自动合并。

策略：

| 用户选择 | 行为 |
| --- | --- |
| 覆盖本地 | 丢弃本地未推送快照，使用远端版本应用到 Blender 用户目录 |
| 覆盖远端 | 保留本地快照，使用 `--force-with-lease` 更新远端 |
| 手动解决 | 保留冲突状态，展示冲突文件，允许逐文件选择 local/remote 或打开外部工具 |

二进制文件默认不能手动文本合并。UI 提供 local、remote、base 的时间和大小，用户选择保留版本。

文本文件可显示冲突标记，手动编辑后执行 `git add` 和 `git merge --continue`。

## 手动同步

手动同步按钮调用同一条 Sync Service 流程，区别是：

- 忽略定时间隔。
- UI 显示实时进度。
- 若已有后台任务，按钮显示当前任务状态，不启动第二个任务。

按钮：

- `Sync Now`
- `Check Remote`
- `Push Local`
- `Pull Remote`
- `Resolve Conflict`
- `View History`
- `Rollback`

## 历史和回滚

历史列表来自 Git commit。每次自动同步提交使用固定格式：

```text
Sync from <device-name> at <iso-time>
```

回滚流程：

1. 用户选择 commit。
2. 插件显示 commit 信息和变更文件。
3. 创建当前本地备份。
4. 从目标 commit checkout 到 staging。
5. 生成回滚提交。
6. 应用 staging 到 Blender 用户目录。
7. 可选 push 到 remote。

## 插件同步

插件同步默认只包含用户目录下的插件和扩展，不同步 Blender 自带插件。

阈值规则：

- 用户设置单个插件目录大小阈值，默认 `50 MB`。
- 超过阈值的插件写入 `manifest.json` 的 skipped 列表。
- UI 展示被跳过插件名称、大小和原因。
- 用户可单独允许某个插件超过阈值。

过滤规则：

- 排除 `__pycache__`、`.pytest_cache`、`.git`、构建产物、日志。
- 排除常见二进制缓存。
- 保留 `.py`、`.json`、`.txt`、`.toml`、`.yaml`、`.blend`、预设文件和插件资源。

## 安全

- 不保存 Git 密码或 token。
- 不同步 SSH key、credential helper 文件、系统 keychain 数据。
- remote URL 可保存，但需要遮蔽用户名和 token。
- 应用远端快照前创建本地备份。
- 操作真实用户目录前先在 staging repo 完成 Git 状态确认。

## 错误处理

| 错误 | 处理 |
| --- | --- |
| 未安装 Git | UI 显示安装指引，禁用同步按钮 |
| remote 不可访问 | 保留本地提交，稍后重试 |
| 认证失败 | 显示 Git 输出摘要，不要求用户在插件中输入密码 |
| merge conflict | 进入 `conflict` 状态 |
| apply 失败 | 回滚到应用前备份 |
| 文件被占用 | 稍后重试，并列出失败路径 |

## 测试

- macOS、Windows、Linux 路径解析测试。
- staging repo 初始化测试。
- include/exclude 过滤测试。
- 插件大小阈值测试。
- fast-forward、local ahead、remote ahead、diverged 场景测试。
- 覆盖本地、覆盖远端、手动冲突测试。
- 二进制冲突测试。
- 回滚测试。
- Git 不存在、remote 失败、认证失败测试。
