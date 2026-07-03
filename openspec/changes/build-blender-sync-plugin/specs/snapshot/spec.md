## ADDED Requirements

### Requirement: Collect files to staging repo
系统 SHALL 将 Blender 用户目录中需同步的文件复制到 staging repo（`blender-sync-state/repo/`），保持相对目录结构。

#### Scenario: First snapshot creation
- **WHEN** staging repo 为空且触发首次采集
- **THEN** 系统复制所有同步目标文件到 staging repo 对应路径
- **AND** staging repo 结构与设计文档一致

#### Scenario: Subsequent snapshot update
- **WHEN** Blender 用户目录中有文件变更后触发采集
- **THEN** 系统仅更新已变更的文件到 staging repo
- **AND** 删除 staging repo 中已不存在于源目录的文件

### Requirement: Generate manifest.json
系统 SHALL 在 staging repo 根目录生成 `manifest.json`，记录：
- Blender version
- OS（操作系统名称）
- sync schema version
- included paths（已包含的文件路径及哈希）
- excluded paths（被排除的路径及原因）
- plugin size threshold
- last exported time（ISO 8601 格式）

#### Scenario: Manifest created with correct metadata
- **WHEN** 采集完成后生成 manifest
- **THEN** manifest.json 包含当前 Blender 版本号和操作系统名称
- **AND** 每个 included 文件记录其文件哈希
- **AND** last exported time 为采集时刻的 ISO 8601 时间

#### Scenario: No machine-local data in manifest
- **WHEN** manifest.json 被生成
- **THEN** manifest 不包含本机用户名、绝对 HOME 路径、Git 凭据

### Requirement: Plugin size threshold filtering
系统 SHALL 根据用户设置的插件大小阈值过滤需同步的插件目录。

#### Scenario: Plugin under threshold
- **WHEN** 某插件目录总大小小于或等于阈值
- **THEN** 该插件被包含在 staging repo 中
- **AND** manifest.json 的 included 列表中记录该插件

#### Scenario: Plugin exceeds threshold
- **WHEN** 某插件目录总大小超过阈值
- **THEN** 该插件不被复制到 staging repo
- **AND** manifest.json 的 excluded 列表中记录插件名称、大小和跳过原因

#### Scenario: User overrides threshold for specific plugin
- **WHEN** 用户将某超大插件加入白名单
- **THEN** 该插件被包含在 staging repo 中，忽略阈值限制

### Requirement: Generate .gitignore and .gitattributes
系统 SHALL 在 staging repo 中生成 `.gitignore` 和 `.gitattributes` 文件。

#### Scenario: .gitignore content
- **WHEN** staging repo 初始化时
- **THEN** .gitignore 排除缓存、日志、临时文件

#### Scenario: .gitattributes content
- **WHEN** staging repo 初始化时
- **THEN** .gitattributes 固定文本文件换行为 LF，减少跨平台冲突
