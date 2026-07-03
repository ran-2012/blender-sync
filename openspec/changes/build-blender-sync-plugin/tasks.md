## 1. 插件骨架

- [x] 1.1 创建 `blender_sync/__init__.py`：`bl_info` 字典、`register()` / `unregister()` 入口
- [x] 1.2 创建 `preferences.py`：`AddonPreferences` 子类，定义 remote、branch、interval、threshold、auto_sync、conflict_policy 等配置项，提供 `draw()` 方法
- [x] 1.3 创建 `panel.py`：3D View 侧栏面板，显示 Git 版本、remote、上次同步时间、当前状态
- [x] 1.4 创建 `operators.py`：注册 Sync Now、Check Remote、Push Local、Pull Remote 按钮的 operator stub
- [x] 1.5 实现 Git 可用性检测：启动时执行 `git --version`，结果写入状态
- [ ] 1.6 验收：插件可安装启用，Preferences 面板可保存配置，Git 不存在时显示错误状态

## 2. 路径解析

- [x] 2.1 创建 `path_resolver.py`：使用 `bpy.utils.user_resource()` 获取 CONFIG、SCRIPTS、EXTENSIONS 路径
- [x] 2.2 实现 `extension_path_user()` 获取插件自有可写目录，自动创建 `blender-sync-state/` 子目录
- [x] 2.3 实现同步目标路径列表生成，包含 userpref.blend、startup.blend、bookmarks.txt、presets、addons、extensions
- [x] 2.4 支持 recent-files.txt 可选同步（默认关闭）
- [x] 2.5 支持 include/exclude pattern 过滤
- [ ] 2.6 验收：三平台路径均使用 Blender API 返回，不硬编码系统路径

## 3. Snapshot 和 Manifest

- [x] 3.1 创建 `snapshot.py`：实现 Blender 用户目录 → staging repo 的文件复制逻辑
- [x] 3.2 实现增量更新：仅复制变更文件，删除 staging 中已移除的源文件
- [x] 3.3 创建 `filters.py`：实现插件目录大小计算和阈值过滤
- [x] 3.4 支持用户对特定插件设置白名单，越过阈值限制
- [x] 3.5 创建 `manifest.py`：生成 `manifest.json`，记录 Blender 版本、OS、schema version、included/excluded paths、文件哈希、导出时间
- [x] 3.6 生成 `.gitignore`（排除缓存/日志/临时文件）和 `.gitattributes`（文本 LF、二进制标记）
- [ ] 3.7 验收：超阈值插件被跳过并记录在 manifest；manifest 不含本机敏感信息

## 4. Git Adapter

- [x] 4.1 创建 `git_adapter.py`：封装 `subprocess` Git 命令执行，参数以数组传递
- [x] 4.2 实现 `ensure_repo()`：`git init`、`git remote add`、`git checkout -B`
- [x] 4.3 实现 `status()`：解析 `git status --porcelain` 返回结构化状态
- [x] 4.4 实现 `commit_all()`：`git add -A` + `git commit -m "Sync from <device> at <time>"`
- [x] 4.5 实现 `fetch()`：`git fetch origin <branch>`，处理认证失败和网络错误
- [x] 4.6 实现 `relation()`：判断 `up_to_date` / `local_ahead` / `remote_ahead` / `diverged`
- [x] 4.7 实现 `merge_remote()` 和 `abort_merge()`
- [x] 4.8 实现 `push()` 和 `force_push_with_lease()`
- [x] 4.9 实现 `log()` 和 `checkout_tree()`
- [ ] 4.10 验收：所有 Git 命令无 shell 拼接；能正确判断分支关系；错误写入日志

## 5. Sync Service

- [x] 5.1 创建 `sync_service.py`：`SyncService` 类，包含 sync_now、check_remote、push_local、pull_remote、resolve_conflict、rollback_to 方法
- [x] 5.2 实现完整同步流程：采集 → commit → fetch → 判断关系 → merge/push → apply
- [x] 5.3 实现本地超前场景：commit 后直接 push
- [x] 5.4 实现远端超前场景：fetch + fast-forward merge + apply 到用户目录
- [x] 5.5 实现分叉场景：进入 conflict 状态，不自动覆盖
- [x] 5.6 实现 apply 前备份：将当前 Blender 用户目录目标文件备份到 `backups/<timestamp>/`
- [x] 5.7 实现 apply：staging repo → Blender 用户目录反向复制
- [x] 5.8 创建 `status_store.py`：`status.json` 读写，原子写入保护
- [ ] 5.9 验收：手动同步可完成全流程；分叉进入 conflict；apply 前有备份

## 6. Scheduler 和后台同步

- [x] 6.1 创建 `scheduler.py`：`register()` 注册启动 timer，`unregister()` 清理
- [x] 6.2 实现启动远端检查：Git 版本检测 → remote 配置检查 → 异步 fetch
- [x] 6.3 实现定时同步：按 sync_interval 注册 timer 回调
- [x] 6.4 实现锁文件机制：`blender-sync-state/runtime/lock`，包含 PID、开始时间、操作类型
- [x] 6.5 实现锁超时检测：PID 不存在时提示用户清理
- [x] 6.6 实现同步状态机：idle → checking_remote → exporting → committing → pulling → applying → idle
- [ ] 6.7 验收：启动不阻塞 UI；同步中不启动第二个任务；文件切换后 timer 仍工作

## 7. 冲突 UI

- [x] 7.1 实现冲突文件列表显示：文件路径、大小、本地/远端修改时间
- [x] 7.2 实现"覆盖本地"按钮：确认后 reset --hard + apply
- [x] 7.3 实现"覆盖远端"按钮：确认后 commit + force-with-lease push
- [ ] 7.4 实现二进制文件逐文件选择：展示 local/remote 时间和大小，用户选择保留版本
- [ ] 7.5 实现文本文件逐文件处理：local/remote/外部编辑器三种选项
- [x] 7.6 实现 Abort 按钮：`git merge --abort` 恢复合并前状态
- [ ] 7.7 实现冲突解决后的提交：生成合并提交消息
- [ ] 7.8 验收：冲突不自动覆盖文件；每步操作有确认；abort 可恢复

## 8. 历史和回滚

- [x] 8.1 实现 View History 按钮：展示最近 20 个同步提交（SHA、消息、时间、设备名）
- [x] 8.2 实现 commit 详情展示：`git show --stat <commit>` 变更文件列表
- [x] 8.3 实现回滚预览：`git diff <target>..HEAD` 展示差异
- [x] 8.4 实现回滚执行：备份 → checkout → 新提交 → apply → 可选 push
- [ ] 8.5 验收：回滚前有备份；回滚生成新提交不改写历史；回滚后可继续同步

## 9. 发布和兼容性

- [x] 9.1 编写 `blender_sync/__init__.py` 的 `bl_info` 目标 Blender 版本范围
- [ ] 9.2 打包为 Blender addon zip
- [x] 9.3 编写安装说明（README 更新）
- [x] 9.4 编写故障排查说明（Git 未安装、认证失败、remote 不可达）
- [ ] 9.5 在 Windows、macOS、Linux 目标 Blender 版本上测试安装
- [ ] 9.6 验证插件升级不删除 `blender-sync-state/` 目录
