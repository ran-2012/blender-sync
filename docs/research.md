# 实现调研

## 结论

Blender Sync 应使用 Blender 官方用户目录作为同步源，使用插件自有可写目录保存 Git 工作区、状态文件和锁文件。后台同步通过 `bpy.app.timers` 触发短任务，Git 操作通过 `subprocess` 调用系统 `git` 命令。不要使用常驻 Python 线程访问 Blender API。

## Blender API

### 插件配置

`bpy.types.AddonPreferences` 可保存插件配置，并在 Preferences 中绘制 UI。配置项应包含：

- remote URL
- branch
- sync interval
- auto sync enabled
- startup remote check enabled
- conflict policy
- plugin size threshold
- include/exclude patterns

`AddonPreferences.bl_idname` 需要匹配插件包名。多文件插件使用 `__package__`。

### 启动和定时任务

`bpy.app.timers.register(function, first_interval=..., persistent=True)` 可注册延迟任务。函数返回 `None` 时取消注册，返回秒数时继续调度。

`bpy.app.handlers.load_post` 可在加载文件后触发任务，`@persistent` 可让 handler 在加载新文件后保留。启动检查远端更适合在插件 `register()` 中注册 timer，避免在 Blender 启动阶段阻塞 UI。

### 路径

`bpy.utils.user_resource(resource_type, path='', create=False)` 返回跨平台用户资源路径。可用类型包含 `CONFIG`、`SCRIPTS`、`EXTENSIONS`、`DATAFILES`。

`bpy.utils.extension_path_user(package, path='', create=True)` 可返回插件自己的可写目录。插件运行状态、Git 工作区和临时文件应放在这里，不写入插件安装目录。

Blender 用户目录默认位置：

| 平台 | 用户目录 |
| --- | --- |
| Linux | `$HOME/.config/blender/<version>/` 或 `$XDG_CONFIG_HOME/blender/<version>/` |
| macOS | `/Users/$USER/Library/Application Support/Blender/<version>/` |
| Windows | `%USERPROFILE%\AppData\Roaming\Blender Foundation\Blender\<version>\` |

相关子目录：

| 子目录 | 用途 |
| --- | --- |
| `config/userpref.blend` | 用户偏好 |
| `config/startup.blend` | 启动文件 |
| `config/bookmarks.txt` | 文件浏览器书签 |
| `config/recent-files.txt` | 最近文件 |
| `scripts/addons` | 用户安装的传统插件 |
| `extensions` | Blender 扩展仓库 |
| `scripts/presets` | 用户预设 |

## 后台限制

Blender 文档说明 Python 线程可能导致难以诊断的崩溃。线程只有在主线程被阻塞且线程结束后才相对安全；后台线程运行期间不得访问 `bpy` 或 Blender API。

实现约束：

- 不创建常驻 Python 线程。
- 不在 Git 子进程中访问 Blender API。
- `bpy.app.timers` 只负责调度、读取状态、触发 UI 刷新。
- Git 操作使用短生命周期 `subprocess.run` 或 `subprocess.Popen`。
- 状态通过 JSON 文件或内存队列传回主线程，主线程再更新 UI。

## Git 方案

Git 适合存储配置、预设、脚本、小型插件和历史。大文件插件不适合直接提交，需使用阈值过滤。

推荐策略：

- 使用普通 Git 工作区，不使用 bare repo，便于执行 `status`、`merge`、`checkout`。
- 同步源文件复制到插件管理的 staging 目录，再由 Git 管理 staging 目录。
- 不直接把整个 Blender 用户目录变成 Git repo，避免误提交缓存、绝对路径、临时文件和权限问题。
- 使用 `.gitattributes` 固定文本换行，减少跨平台冲突。
- 使用 `.gitignore` 排除缓存、日志、临时文件、大文件和机器本地配置。

### 冲突能力

`git merge` 默认使用三方合并。出现冲突时，Git 会在工作区写入冲突标记，并可用 `git merge --abort` 回退到合并前状态。

覆盖策略：

| 策略 | Git 操作 | 语义 |
| --- | --- | --- |
| 覆盖本地 | `git reset --hard origin/<branch>`，再应用到 Blender 用户目录 | 远端为准 |
| 覆盖远端 | 提交本地 staging，`git push --force-with-lease` | 本机为准，保护远端不被意外覆盖 |
| 手动解决 | `git merge --no-commit origin/<branch>`，保留冲突文件 | 用户逐文件选择 ours/theirs/manual |

`git merge -X ours` 和 `git merge -X theirs` 只处理冲突片段，非冲突改动仍会合并。完整覆盖应使用 `reset --hard` 或重新生成提交，不依赖 `-X`。

### 历史和回滚

历史查看使用：

- `git log --oneline --decorate --max-count=N`
- `git show --stat <commit>`
- `git diff <old> <new>`

回滚使用：

- 预览：`git diff <commit>..HEAD`
- 回滚 staging：`git checkout <commit> -- .`
- 生成回滚提交：`git commit -m "Rollback to <commit>"`
- 应用到 Blender 用户目录：从 staging 复制到真实目录

不要默认使用 `git reset --hard <commit>` 作为用户可见回滚，因为它会改写本地历史，不利于多设备同步。

## 依赖

推荐依赖系统 `git` 命令。原因：

- GitPython 不一定随 Blender Python 安装。
- 插件安装第三方 Python 包会受 Blender 版本、权限和平台影响。
- 系统 Git 在 macOS、Windows、Linux 都有成熟安装路径。

插件启动时检查：

- `git --version`
- remote URL 是否配置
- staging repo 是否已初始化
- remote 是否可访问

认证不由插件保存密码。HTTPS token、SSH key、系统凭据管理器交给 Git 自身处理。

## 参考

- Blender Python API: `AddonPreferences`
- Blender Python API: `bpy.app.timers`
- Blender Python API: `bpy.app.handlers`
- Blender Python API: `bpy.utils.user_resource`
- Blender Manual: Blender Directory Layout
- Blender Python API Gotchas: Python Threads are Not Supported
- Git Manual: `git merge`
- Git Manual: `git worktree`
