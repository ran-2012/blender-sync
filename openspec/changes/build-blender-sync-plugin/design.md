## Context

Blender Sync 是一个 Blender 插件，使用 Git 在 macOS、Windows、Linux 之间同步用户设置、插件和轻量资源。Blender Python 环境有严格的限制：不支持常驻 Python 线程（会导致难以诊断的崩溃），第三方 Python 包安装受 Blender 版本和权限影响。因此设计上需要规避这些约束，使用系统级 Git 和 `bpy.app.timers` 进行调度。

## Goals / Non-Goals

**Goals:**
- 使用 Git 作为远端存储和版本管理工具
- 支持启动远端检查、定时后台同步、手动同步
- 支持覆盖本地、覆盖远端、手动解决冲突三种策略
- 跨平台支持 macOS、Windows、Linux
- 支持回滚到历史同步点，回滚生成新提交而非改写历史
- 插件大小阈值过滤，避免大文件拖慢同步
- 每次 apply 前自动创建备份

**Non-Goals:**
- 不同步缓存、临时文件、渲染输出、大型资产库
- 不同步系统自带插件
- 不同步凭据、token、SSH key
- 不提供 Git 认证管理（交给 Git 自身凭据系统）
- 不提供实时协作编辑
- 不提供二进制文件的三方合并（依赖用户逐文件选择版本）

## Decisions

### Decision 1: 系统 Git 而非 GitPython

**选择**: 通过 `subprocess` 调用系统安装的 `git` 命令。

**替代方案**:
- **GitPython**: 功能丰富但需要安装第三方包。Blender 的 Python 环境不保证有 pip，用户安装第三方包在不同平台、不同 Blender 版本下复杂度高，容易失败。
- **Dulwich**: Python 原生 Git 实现，无需系统 Git，但性能差、功能不完整（尤其 merge/conflict 处理），且未被广泛验证。

**理由**: 系统 Git 在所有主流操作系统上都有成熟安装方式，认证由 Git 自身凭据管理器处理（SSH key、HTTPS token、credential helper），插件无需处理安全问题。命令通过参数数组传递，无 shell 注入风险。

### Decision 2: Staging Repo 隔离于 Blender 用户目录

**选择**: 在插件自有可写目录下维护独立的 Git staging repo（`blender-sync-state/repo/`），同步时双向复制：
- 采集：Blender 用户目录 → staging repo
- 应用：staging repo → Blender 用户目录

**替代方案**:
- **直接 Git init Blender 用户目录**: 风险极高。Blender 用户目录包含大量不应版本控制的文件（缓存、临时文件、机器特定路径），gitignore 维护困难，且 Blender 运行时可能修改文件导致 Git 状态混乱。
- **Bare repo + worktree**: 增加复杂度，且 worktree 路径需要额外管理。

**理由**: staging repo 隔离使得 Git 工作区完全可控，只有被明确采集的文件才进入版本控制。`.gitignore` 和 `.gitattributes` 在 staging 中管理，不影响真实用户目录。

### Decision 3: Timer 调度而非线程

**选择**: 使用 `bpy.app.timers.register()` 注册周期性回调，timer 回调启动短生命周期 `subprocess` 子进程后立即返回。

**替代方案**:
- **Python `threading`**: Blender 官方文档明确指出 Python 线程可能导致难以诊断的崩溃，仅在主线程阻塞且线程结束后才相对安全。
- **`asyncio`**: 同样需要线程/事件循环支撑，不兼容 Blender 主循环。

**理由**: `bpy.app.timers` 是 Blender 官方提供的唯一安全后台调度 API。timer 回调在主线程执行，确保 Blender API 访问安全。Git 操作通过 `subprocess.Popen` 异步启动，不阻塞 UI，状态通过 JSON 文件和 timer 轮询传回。

**约束**: timer 回调 CPU 时间有限，不能执行长时间循环。Git 操作耗时不确定（网络延迟），使用 `subprocess.Popen` 非阻塞模式启动后 timer 通过 status 文件跟踪进度。

### Decision 4: 状态持久化方式

**选择**: 使用 `status.json` 文件存储当前同步状态，供 UI 和 scheduler 各模块读取。

**替代方案**:
- **`bpy.context.scene` 自定义属性**: 仅当前 session 有效，Blender 重启丢失，文件切换可能导致属性丢失。
- **内存单例 + 事件通知**: 无法跨模块通信，且需要在 timer 回调间保持状态。

**理由**: JSON 文件在 timer 回调、UI 绘制、operator 执行三个上下文中都可达，是 Blender 插件中最简单的跨上下文状态通信方式。status 文件很小，读写开销可忽略。

### Decision 5: 冲突策略设计

**选择**: 三策略：覆盖本地（`git reset --hard origin/<branch>`）、覆盖远端（`git push --force-with-lease`）、手动解决（`git merge --no-commit` + 逐文件选择）。

**替代方案**:
- **`git merge -X ours` / `-X theirs`**: 仅处理冲突片段，非冲突改动仍会合并。完整覆盖语义不满足。
- **`git reset --hard` 用于回滚**: 改写历史，导致多设备间同步困难。

**理由**: `reset --hard` 对"丢弃本地"场景语义正确；`--force-with-lease` 保护远端不被意外覆盖（若有其他设备在此期间提交，push 被拒绝）；手动解决保留精准控制。

### Decision 6: 回滚生成新提交

**选择**: 回滚使用 `git checkout <commit> -- .` 更新工作区文件，然后创建新提交，不改变历史。

**理由**: 历史不可变是多设备同步的基础。若回滚使用 `reset --hard`，其他设备的分支关系将无法正常计算。新提交保持历史线性，其他设备可以 fetch 到回滚结果。

### Decision 7: 模块分层

**选择**: 6 层架构：

```
UI (panel.py, operators.py, preferences.py)
  ↓
Scheduler (scheduler.py)
  ↓
Sync Service (sync_service.py)
  ↓
Git Adapter (git_adapter.py) + Snapshot (snapshot.py, manifest.py)
  ↓
Path Resolver (path_resolver.py) + Status Store (status_store.py)
```

每层仅依赖下一层，无循环依赖。UI 不直接调用 Git Adapter，所有操作走 Sync Service。

## Risks / Trade-offs

| Risk | 影响 | 缓解措施 |
|------|------|----------|
| 系统 Git 版本差异导致命令行为不一致 | 部分 Git 命令输出格式变化（如 `status --porcelain` v2） | 固定使用 `status --porcelain` v1 格式，不使用 v2 新字段；启动时检测 Git 最低版本 |
| 大文件插件未被阈值过滤 | 同步变慢，Git 仓库膨胀 | 默认 50MB 阈值；UI 展示被跳过插件的名称和大小；用户可手动加入白名单 |
| `subprocess` 超时/崩溃无感知 | Git 进程可能卡死 | 锁文件超时机制（PID 检查），用户可手动清理过期锁 |
| 锁文件残留（Blender 崩溃） | 无法启动新同步 | 锁文件包含 PID，检查进程是否存在；超时后提示用户清理 |
| 跨平台换行符差异导致冲突 | `.blend` 二进制文件外，文本文件 CRLF/LF 差异 | `.gitattributes` 固定文本文件为 LF；二进制文件标记为 binary |
| Timer 回调频率限制 | 状态轮询有延迟 | status.json 原子写入，timer 每秒检查一次即可 |
| 多 Blender 版本间设置不兼容 | 同步 `userpref.blend` 可能在新旧版本间出错 | manifest 记录 Blender 版本号；UI 提示版本不一致时的风险 |

## Migration Plan

1. 用户克隆或下载插件 zip 安装包。
2. 在 Blender Preferences → Add-ons 中安装并启用。
3. 首次使用：在 Preferences 面板配置 Git remote URL 和分支。
4. 插件自动初始化 staging repo 并执行首次采集。
5. 首次同步：手动点击 "Sync Now"，等待完整流程完成。
6. 后续：可选启用 auto sync 和 startup check。
7. 插件升级：直接替换插件文件，不删除 `blender-sync-state/` 目录，状态和仓库保持。

## Open Questions

- Blender 5.x 中 `bpy.utils.extension_path_user` API 是否有变化？需要在 Beta 版本中验证。
- 需要测试 `bpy.app.timers` 在 Blender 后台渲染模式（`--background`）下的行为。
- 是否需要在首次同步前提供 "dry run" 预览功能？当前设计未包含。
