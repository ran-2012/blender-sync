# Blender Sync

Blender Sync 是一个 Blender 插件，使用 Git 在多台电脑之间同步用户设置、插件和轻量资源。

## 安装

1. **安装 Git**：确保系统已安装 Git（[git-scm.com](https://git-scm.com)）。

2. **下载插件**：将 `blender_sync/` 文件夹打包为 zip：
   ```bash
   # 在项目根目录
   zip -r blender_sync.zip blender_sync/
   ```

3. **安装到 Blender**：
   - 打开 Blender → Edit → Preferences → Add-ons
   - 点击 "Install..." 选择 `blender_sync.zip`
   - 搜索 "Blender Sync" 并启用

4. **配置远程仓库**：
   - 在 Blender Preferences 中找到 Blender Sync 配置
   - 填入 Git remote URL（如 `git@github.com:user/blender-sync-data.git`）
   - 设置分支名（默认 `main`）

## 使用

| 操作 | 说明 |
|------|------|
| **Sync Now** | 完整同步：采集 → 提交 → 拉取 → 合并 → 推送 → 应用 |
| **Check Remote** | 仅检查远端是否有更新 |
| **Push Local** | 导出本地设置并推送到远端 |
| **Pull Remote** | 拉取远端设置并应用到本地 |
| **Resolve Conflict** | 冲突时选择覆盖本地或覆盖远端 |
| **View History** | 查看同步提交历史 |
| **Rollback** | 回滚到历史同步点 |

## 同步内容

- `config/userpref.blend` — 用户偏好
- `config/startup.blend` — 启动文件
- `config/bookmarks.txt` — 文件浏览器书签
- `scripts/presets/` — 用户预设
- `scripts/addons/` — 用户安装的传统插件（默认最大 50MB/个）
- `extensions/` — Blender 扩展

默认**不同步**：缓存、渲染输出、临时文件、大文件资产库、系统插件、SSH key 和凭据。

## 故障排查

### Git 未安装
Blender Sync 面板显示 "Git not found"。请安装 [Git](https://git-scm.com) 并确保 `git` 命令在系统 PATH 中。

### 认证失败
`git fetch` 或 `git push` 报 "Authentication failed"：
- **SSH**：确保 SSH key 已添加到 GitHub/GitLab，且 `ssh -T git@github.com` 可以连接。
- **HTTPS**：使用 Git credential helper 保存 token 或使用 SSH URL。

### 远端不可达
"Remote is unreachable"：检查网络连接和 remote URL 是否正确。

### 锁文件残留
如果 Blender 崩溃，`blender-sync-state/runtime/lock` 可能残留。删除该文件即可恢复同步。

## 开发文档

- [docs/research.md](docs/research.md)：Blender API、目录、线程和 Git 方案调研。
- [docs/architecture.md](docs/architecture.md)：功能边界、模块设计、同步流程、冲突处理和回滚设计。
- [docs/implementation-plan.md](docs/implementation-plan.md)：实现阶段、目录结构、关键接口和测试清单。

## 目标

- 使用 Git 作为远端存储。
- 支持启动检查远端、后台同步、手动同步。
- 支持覆盖远端、覆盖本地、手动解决冲突。
- 支持 macOS、Windows、Linux。
- 支持设置回滚和历史查看。
- 支持同步设置和插件，并允许用户设置插件大小阈值。
