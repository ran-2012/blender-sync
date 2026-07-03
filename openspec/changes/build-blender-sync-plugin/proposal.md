## Why

Blender 用户在多台电脑上工作时，设置、预设、插件需要手动复制才能保持一致，容易遗漏或冲突。需要一款 Blender 插件，用 Git 自动在多台设备间同步这些轻量配置，并提供冲突处理和版本回滚能力。

## What Changes

- 新增 Blender 插件包 `blender_sync`，提供完整的跨设备设置同步能力。
- 新增加载项偏好设置面板（AddonPreferences）：配置 Git remote、分支、同步间隔、插件大小阈值、包含/排除规则。
- 新增路径解析模块：跨平台（Windows/macOS/Linux）定位 Blender 用户目录（config、scripts、extensions）。
- 新增 Snapshot 模块：将用户设置采集到 staging 目录，生成 manifest.json 记录 Blender 版本、文件哈希、跳过的大文件插件。
- 新增 Git Adapter 模块：封装 git init、add、commit、fetch、merge、push、log、checkout 等操作，使用 subprocess 调用系统 git。
- 新增 Sync Service：完整同步流程（采集→提交→拉取→合并/冲突→推送→应用到用户目录），支持覆盖本地、覆盖远端、手动解决冲突、回滚。
- 新增 Scheduler 模块：通过 `bpy.app.timers` 实现启动远端检查和定时后台同步，使用锁文件防止并发。
- 新增 UI 面板和操作按钮：Sync Now、Check Remote、Push Local、Pull Remote、Resolve Conflict、View History、Rollback。
- 新增冲突处理界面：展示冲突文件列表，支持逐文件选择 local/remote 版本。
- 新增历史查看和回滚功能：展示最近 N 个同步提交，支持回滚到任意 commit。

## Capabilities

### New Capabilities

- `plugin-skeleton`: Blender 插件注册、AddonPreferences 配置面板、Git 可用性检测、状态展示
- `path-resolver`: 跨平台 Blender 用户目录定位（CONFIG、SCRIPTS、EXTENSIONS）
- `snapshot`: 用户设置采集到 staging 仓库、manifest 生成、插件大小过滤
- `git-adapter`: Git 命令封装（init、commit、fetch、merge、push、log、checkout），状态解析，分支关系判断
- `sync-service`: 完整同步流程编排，备份创建，冲突策略执行，回滚操作
- `scheduler`: 启动远端检查，定时后台同步，锁文件去重，状态机管理
- `conflict-ui`: 冲突文件展示，逐文件 local/remote 选择，覆盖操作
- `history-rollback`: 同步提交历史查看，commit 变更摘要，回滚到目标 commit

### Modified Capabilities

<!-- 无现有 capabilities 需要修改 -->

## Impact

- 插件包：`blender_sync/`（约 12 个 Python 模块），安装在 Blender addons 或 extensions 目录。
- 数据目录：插件在自有可写目录 `blender-sync-state/` 下管理 Git staging repo、状态文件、锁文件和备份。
- 外部依赖：系统需安装 Git（不依赖 GitPython 等第三方 Python 包）。
- Blender 版本：目标兼容 Blender 4.x/5.x。
