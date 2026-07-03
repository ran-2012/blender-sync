## ADDED Requirements

### Requirement: Startup remote check
插件 `register()` 时 SHALL 注册一个 timer 执行启动远端检查。

#### Scenario: Startup check does not block UI
- **WHEN** Blender 启动且插件被加载
- **THEN** timer 异步触发，不阻塞 Blender 主界面
- **AND** 检查任务仅包含 Git 版本检测、remote 配置检查、异步 fetch

#### Scenario: Remote available at startup
- **WHEN** 启动检查发现远端有新 commit
- **THEN** 状态更新为 `remote_update_available`
- **AND** 根据 auto-sync 配置决定自动拉取或等待用户操作

### Requirement: Periodic background sync
系统 SHALL 按配置的 sync interval 定时执行后台同步。

#### Scenario: Interval-based sync
- **WHEN** sync interval 设置为非零值（如 300 秒）
- **THEN** 每隔指定时间触发一次同步检查

#### Scenario: Interval disabled
- **WHEN** sync interval 设置为 0
- **THEN** 不触发定时同步
- **AND** 仅支持手动同步

### Requirement: Timer-based task scheduling
系统 SHALL 使用 `bpy.app.timers` 调度后台任务，timer 不直接执行长时间操作。

#### Scenario: Timer triggers short task
- **WHEN** timer 触发同步
- **THEN** timer 回调启动短生命周期 Git 子进程
- **AND** 不创建常驻 Python 线程

#### Scenario: Timer survives file load
- **WHEN** Blender 加载新 .blend 文件
- **THEN** timer 继续工作，不因文件切换而中断

### Requirement: Lock file deduplication
系统 SHALL 使用锁文件防止并发同步任务。

#### Scenario: Lock acquired
- **WHEN** 无锁文件存在且同步开始
- **THEN** 创建锁文件，包含 PID、开始时间、操作类型

#### Scenario: Lock prevents concurrent sync
- **WHEN** 锁文件存在且锁进程仍在运行
- **THEN** 新的同步请求被拒绝
- **AND** UI 显示当前正在进行的任务状态

#### Scenario: Stale lock cleanup
- **WHEN** 锁文件存在但对应 PID 已不存在
- **THEN** 系统提示用户锁已过期
- **AND** 用户可手动清理锁文件

### Requirement: Sync state machine
系统 SHALL 遵循以下状态机管理同步生命周期：

| 状态 | 含义 |
|------|------|
| `idle` | 空闲 |
| `checking_remote` | 检查远端 |
| `exporting_snapshot` | 采集本地设置 |
| `committing_local` | 提交本地变化 |
| `pulling_remote` | 拉取远端 |
| `applying_snapshot` | 应用到 Blender 用户目录 |
| `conflict` | 需要用户处理 |
| `error` | 同步失败 |

#### Scenario: State transitions
- **WHEN** 同步流程从 idle 开始
- **THEN** 按顺序经历 `checking_remote → exporting_snapshot → committing_local → pulling_remote → applying_snapshot → idle`
- **AND** 若发生冲突，进入 `conflict` 状态
- **AND** 若发生错误，进入 `error` 状态
