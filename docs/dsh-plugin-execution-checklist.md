# 析问 DeepSeek Harness 插件改造与投稿执行清单

## 目标

将现有析问（Xiwen）Data Agent 改造成可由 DeepSeek Harness 安装和调用的社区插件，并在满足收录要求后提交到 `awesome-dsh-plugin`。

推荐采用以下架构：保留现有 Python/FastAPI Data Agent 作为后端服务，在同一仓库增加 TypeScript/Cordis 插件适配层，不重写整个后端。

```text
DeepSeek Harness
    │ 调用 xiwen_query 工具
    ▼
TypeScript/Cordis 插件
    │ POST /api/query + 解析 SSE
    ▼
现有 Data Agent（FastAPI + LangGraph）
    │
    ├─ MySQL
    ├─ Qdrant
    ├─ Elasticsearch
    ├─ Embedding
    └─ LLM
```

## 当前状态和主要阻塞项

| 项目 | 当前状态 | 完成标准 |
|---|---|---|
| 仓库可见性 | `kaiwangleo/xiwen` 为私有仓库 | 投稿前改为公开 |
| Git 提交数 | 当前只有 1 个提交 | 至少 10 个有实际意义的提交 |
| 仓库年龄 | 2026-08-17 创建 | 满足至少 1 天的要求 |
| Harness 清单 | 尚无 `package.json`、`dsh.bundle` | 增加可安装的插件子包 |
| GitHub Topic | 尚未配置 | 添加 `dsh-plugin` topic |
| 功能重复 | 已有 `omdsh-dev/dsh-data-agent` | 证明析问具有明确、真实的差异化能力 |
| SQL 安全 | `EXPLAIN` 后直接执行模型生成的 SQL | 强制只读、单语句、超时和结果上限 |
| 开源完备性 | 根 README、许可证和自动化测试不完整 | 补齐文档、许可证和测试 |

## 阶段 1：确定实施范围

- [x] 确认采用“TypeScript 插件适配现有 Python 服务”方案，不重写 Data Agent。
- [x] 插件名称使用 `dsh-xiwen`，避免与现有 `dsh-data-agent` 重名。
- [x] npm 包名暂定为 `@kaiwangleo/dsh-xiwen`。
- [x] 第一版只提供 Harness 工具，不集成 Harness Web UI。
- [x] 第一版只注册一个核心工具：`xiwen_query`。
- [x] 确认目标仓库为 `kaiwangleo/xiwen`、目标远端为 `origin`。
- [x] 创建不含 `codex` 的开发分支，例如 `feat/dsh-xiwen-plugin`。
- [x] 将本次改造范围限制在插件接入、安全加固、测试、文档和发布准备，不做无关重构。

## 阶段 2：完善开源仓库

- [x] 添加根目录 `README.md`，说明析问的定位、架构、功能、启动方式和限制。
- [x] 添加明确的开源许可证，例如 MIT 或 Apache-2.0。
- [x] 将 `data-agent/pyproject.toml` 的占位描述替换为真实项目描述。
- [x] 检查 Git 历史和工作区，确保不存在 API Key、密码、访问令牌、模型权重或私有数据。
  - 2026-08-18：唯一历史提交和拟提交文本中未发现高置信 API Key、Token 或私钥；本地模型权重已忽略。
  - `python_uploads/` 下的本地 PDF 已经用户确认删除；该目录仍由 `.gitignore` 防止未来误提交。
- [x] 确认日志、`.venv`、构建产物和本地配置已被 `.gitignore` 排除。
  - 忽略规则已补齐；活动配置 `data-agent/conf/app_config.yaml` 已从 Git 索引暂存移除，本地副本保持不变。
- [x] 为后端和插件分别提供示例配置，不提交真实凭据。
- [ ] 投稿前将 GitHub 仓库改为公开。
  - 2026-08-18：GitHub API 确认当前可见性为 `PRIVATE`。
- [ ] 为 GitHub 仓库添加 `dsh-plugin` topic。
  - 2026-08-18：GitHub API 确认当前没有 Topics。
- [ ] 累积至少 10 个有实际意义的提交，不使用空提交凑数。
  - 2026-08-18：当前仅有 1 个提交。
- [ ] 确保仓库公开可访问且满足社区的仓库年龄要求。
  - 仓库创建于 2026-08-17 11:21:38 UTC；2026-08-18 10:11:47 UTC 核对时尚未满 24 小时，且仍为私有仓库。

## 阶段 3：加固 Data Agent 后端

### 3.1 SQL 安全

- [x] 只允许单条 SQL 语句。
- [x] 只允许 `SELECT` 和安全的只读 CTE。
- [x] 拒绝 `INSERT`、`UPDATE`、`DELETE`、`REPLACE`、DDL、存储过程和管理语句。
- [x] 拒绝多语句、注释绕过和危险 MySQL 扩展。
- [x] 推荐并验证使用数据库只读账号。
- [x] 为 SQL 执行增加超时。
- [x] 为查询结果增加强制行数上限。
- [x] 在响应中返回 `truncated` 和行数信息。
- [x] 为只读规则增加正常和绕过场景测试。

### 3.2 HTTP 与 SSE 接口

- [x] 保持现有 `POST /api/query` 路径和 SSE 字段兼容。
- [x] 明确定义 `progress`、`result`、`error` 和 `chat` 的响应结构。
- [x] 增加 `/api/health` 健康检查接口。
- [x] 客户端断开时取消 LangGraph 和数据库查询。
- [x] 对异常返回稳定错误代码，避免暴露内部堆栈和凭据。
- [x] 如支持远程部署，增加 Bearer Token 或等效认证机制。
- [x] 限制请求体大小和查询文本长度。
- [x] 为 SSE 分块、空结果、异常和中途取消增加测试。

阶段 3 单元验证（2026-08-18）：WSL 中运行后端测试共 79 项；Ruff、锁文件、MySQL 初始化脚本语法和 Compose 配置解析均通过。Docker 服务的真实联调留在阶段 6 执行。

## 阶段 4：创建 Harness 插件

建议目录结构：

```text
plugins/dsh-xiwen/
├─ src/
│  ├─ index.ts
│  ├─ client.ts
│  ├─ sse.ts
│  └─ types.ts
├─ tests/
├─ package.json
├─ cordis.patch.yml
├─ tsconfig.json
├─ tsdown.config.ts
└─ README.md
```

### 4.1 插件清单和构建

- [x] 创建 ESM `package.json`。
- [x] 声明 `main`、`types`、`exports` 和 `files`。
- [x] 声明以下 `dsh.bundle` 清单：

  ```json
  {
    "dsh": {
      "bundle": {
        "patch": "./cordis.patch.yml"
      }
    }
  }
  ```

- [x] 将官方 `@deepseek-ai/*` 包声明为 `peerDependencies`，而非普通运行时依赖。
- [x] 使用能覆盖 Harness 预发布版本的显式 semver 分支。
- [x] 添加 `build`、`typecheck`、`test` 和 `pack` 脚本。
- [x] 生成可直接安装的 `lib/` 构建产物。
- [x] 确保发布包不包含 Python 虚拟环境、日志、数据库文件或模型文件。

### 4.2 Cordis 插件配置

- [x] 导出稳定的插件 `name`。
- [x] 声明 `inject = ['tools']`。
- [x] 使用 Schemastery 定义并校验以下配置：
  - [x] `baseUrl`
  - [x] `timeoutMs`
  - [x] `maxRows`
  - [x] 可选认证凭据
  - [x] 可选进度摘要开关
- [x] 配置错误在插件加载时明确失败。
- [x] 不硬编码部署相关参数。
- [x] 在 `cordis.patch.yml` 中插入插件行。
- [x] 默认服务地址只指向本机，避免意外访问外部服务。

### 4.3 `xiwen_query` 工具

- [x] 参数包含必填的业务问题 `query`。
- [x] 工具描述明确说明其适用于结构化业务问数。
- [x] 调用后端 `POST /api/query`。
- [x] 正确处理 SSE 数据的任意网络分块。
- [x] 识别 `progress`、`result`、`error` 和 `chat` 事件。
- [x] 将 Harness 的 `exec.signal` 传递给网络请求。
- [x] 超时或取消后停止所有受插件控制的后台工作。
- [x] 返回规范化 JSON：

  ```json
  {
    "sql": "SELECT ...",
    "rows": [],
    "rowCount": 0,
    "truncated": false,
    "message": null
  }
  ```

- [x] 限制返回给模型的结果大小。
- [x] 将后端错误转换成简洁、可操作的工具错误。
- [x] 为成功、空结果、错误、超时、取消和分块 SSE 增加测试。

阶段 4 单元验证（2026-08-18）：WSL 中插件类型检查、23 项单元测试、ESM 构建和 npm dry-run 打包均通过；实际安装到干净 Harness profile 留在阶段 6 执行。

## 阶段 5：文档和差异化定位

- [x] 插件 README 明确说明 Python 后端必须单独部署。
- [x] 提供 Docker Compose 启动说明。
- [x] 提供最小 Harness 安装和配置示例。
- [x] 说明数据库只读账号、认证和网络暴露风险。
- [x] 说明插件不会自动安装 MySQL、Qdrant、Elasticsearch、Embedding 服务或模型。
- [x] 提供完整卸载方法。
- [x] 增加至少一张真实运行截图。
  - 2026-08-18：使用真实 Xiwen 后端、MySQL、Qdrant、Elasticsearch 和 Embedding 容器完成查询并截图；LLM 响应来自本地确定性 OpenAI-compatible mock，未使用外部模型服务。
- [x] 使用 `Xiwen/析问` 品牌，不以泛化的 `Data Agent` 作为主要名称。
- [x] 在 README 和投稿描述中突出以下真实差异：
  - [x] 中文业务问数
  - [x] 人工维护的语义层
  - [x] 表、字段和指标元数据
  - [x] Qdrant 字段/指标向量召回
  - [x] Elasticsearch 枚举值召回
  - [x] SQL 生成、校验、纠错和执行的固定链路
  - [x] 语义配置与知识构建工作台
- [x] 避免声称支持当前代码尚未实现的数据库、工具或安全能力。

阶段 5 文档验证（2026-08-18）：插件 README 已覆盖部署、安装、配置、安全、差异化定位、故障排查和卸载；真实运行截图待阶段 6 完成端到端验证后补充。

建议英文条目描述：

> Semantic-layer analytics tool that uses curated table, column and metric metadata with Qdrant and Elasticsearch recall to generate, validate and execute MySQL analytical queries through the Xiwen service.

## 阶段 6：本地验证

代码修复、构建和测试默认在用户配置的 WSL 环境中执行。

### 6.1 后端验证

- [x] 运行 Python 格式和静态检查。
- [x] 运行后端单元测试。
- [x] 启动 MySQL、Qdrant、Elasticsearch 和 Embedding 服务。
- [x] 执行一次完整知识构建。
- [x] 调用 `/api/health` 并验证依赖状态。
- [x] 调用 `/api/query` 并验证完整 SSE 链路。
- [x] 验证危险 SQL 被拒绝。
- [x] 验证多语句和绕过形式被拒绝。
- [x] 验证超大结果被截断。
- [x] 验证查询超时和客户端取消。

### 6.2 插件验证

- [x] 运行插件格式检查。
- [x] 运行插件 `typecheck`。
- [x] 运行插件单元测试。
- [x] 构建插件。
- [x] 执行 `pnpm pack` 或 npm 等价命令。
- [x] 检查 tarball 内容，确认只包含发布文件。
- [x] 在干净 Harness profile 中安装 tarball。
- [x] 运行 `dsh --profile <name> --dump-config`。
- [x] 启动 Harness 并实际调用 `xiwen_query`。
- [x] 测试后端不可用、认证失败、超时和取消场景。
- [x] 验证卸载插件后 profile 可以正常启动。

阶段 6 本地验证（2026-08-18）：

- 后端 83 项测试通过；10 个变更 Python 文件通过 Ruff 格式与静态检查。
- 完整知识构建的 6 个步骤全部成功，`/api/health` 的 7 个依赖项均为 `ok`。
- HTTP/SSE 联调覆盖认证、闲聊、完整问数、危险 SQL、多语句、注释绕过、请求限制、结果截断、查询超时和客户端断连；断连后未继续执行召回或数据库节点。
- 插件通过 Prettier、类型检查、23 项测试、ESM 构建和 npm dry-run 打包；tarball 仅包含发布入口、类型声明、source map、补丁、README、截图和 manifest。
- tarball 已安装到干净的 Harness `0.1.0-rc.7` profile，并通过 `ctx.tools.execute()` 实际调用 `xiwen_query`；成功结果为 2 行且 `truncated: true`，后端不可用、认证失败、插件超时和取消均返回预期工具错误。
- 卸载 `@kaiwangleo/dsh-xiwen` 后 profile 仍能成功 `--dump-config`，且输出不再包含 `xiwen` bundle。
- 所有 LLM 相关联调均使用本地确定性 OpenAI-compatible mock，不代表对任何外部模型提供商完成了验证。

## 阶段 7：发布插件

- [ ] 确定首个版本号，例如 `0.1.0`。
- [ ] 检查发布包的许可证、README、入口和类型声明。
- [ ] 优先发布预构建 npm 包，避免 Git 安装所需的构建授权。
- [ ] 在全新 profile 中从 npm 重新安装验证。
- [ ] 创建 GitHub Release。
- [ ] 如不发布 npm，将预构建 `.tgz` 附加到 GitHub Release。
- [ ] 记录准确的构建和验证命令及结果。

## 阶段 8：提交到 `awesome-dsh-plugin`

- [ ] 再次确认仓库公开、至少 10 个提交且包含 `dsh-plugin` topic。
- [ ] 确认社区 CI 能在 `plugins/dsh-xiwen/package.json` 中找到 `dsh.bundle`。
- [ ] 在 `awesome-dsh-plugin/data/plugins/` 新增一个 YAML 文件。
- [ ] monorepo 条目 URL 指向 `plugins/dsh-xiwen` 子目录。
- [ ] 条目名称采用 `kaiwangleo/xiwen#dsh-xiwen` 格式。
- [ ] 分类选择 `tools`。
- [ ] 英文描述只写已经实现并验证的功能，不使用营销词。
- [ ] 如使用 GitHub Release tarball，填写 `tarball` 字段。
- [ ] 可选地在 `data/screenshots.json` 添加 GitHub 托管截图。
- [ ] 在 `awesome-dsh-plugin` 中执行：

  ```sh
  npm ci
  node scripts/generate-readme.mjs
  ```

- [ ] 检查生成结果没有修改其他插件条目。
- [ ] 运行仓库规定的格式、构建和提交检查。
- [ ] 检查暂存区差异和 `git diff --cached --check`。
- [ ] 准备简洁的英文 PR 标题和描述。
- [ ] PR 描述列出实际执行的验证命令和结果。

## 建议的自然提交序列

以下改动可以自然形成独立、有意义的提交；不要为了满足数量要求创建空提交或机械拆分提交。

1. `docs: add project overview and license`
2. `test: add backend test foundation`
3. `fix: enforce read-only SQL execution`
4. `feat: bound query execution and results`
5. `feat: add service health and authentication`
6. `feat: stabilize query SSE contract`
7. `feat(plugin): scaffold Xiwen DSH bundle`
8. `feat(plugin): add Xiwen query tool`
9. `test(plugin): cover SSE parsing and failures`
10. `docs(plugin): add installation and security guide`

提交信息不得包含任何 `Generated-by:` provenance 行。

## 提交和远程操作确认点

每次准备提交或发布前，必须先向用户展示以下内容：

- [ ] 完整代码差异。
- [ ] 暂存区差异。
- [ ] 拟使用的英文提交信息。
- [ ] 拟发布的 Issue/PR 回复或 PR 描述。
- [ ] 目标 Issue、PR、仓库、分支和远端。
- [ ] 计划执行的提交、推送、npm 发布、Release、PR 或仓库可见性修改。

只有得到用户明确确认后，才可以执行提交、推送、发布、创建或更新 PR、发送 GitHub 评论，或者修改远端仓库状态。

## GitHub 投稿和审查流程

- [ ] GitHub Issue、PR、审查回复和 PR 描述默认使用英文。
- [ ] 执行 Issue 或 PR 操作前，阅读正文、现有评论、审查线程和当前检查状态。
- [ ] 最终操作前检查当前提交、差异、检查状态和未解决的人类审查线程。
- [ ] 完成实现后，用英文更新实际结果和验证状态。
- [ ] GitHub Markdown 使用真实换行，不发送字面量 `\\n`。
- [ ] 不强制推送或改写远端历史，除非用户另行明确授权。

## 参考资料

- [DeepSeek Harness：第一个插件](https://deepseek-harness.github.io/deepseek-harness/develop/basic/)
- [DeepSeek Harness：开发一个 Tool](https://deepseek-harness.github.io/deepseek-harness/develop/basic/tool)
- [DeepSeek Harness：插件配置](https://deepseek-harness.github.io/deepseek-harness/develop/basic/config)
- [DeepSeek Harness：打包与安装插件](https://deepseek-harness.github.io/deepseek-harness/develop/basic/publish)
- [`awesome-dsh-plugin` 贡献指南](../awesome-dsh-plugin/contributing.md)
- [析问技术架构](../data-agent/docs/技术架构.md)
- [析问查询接口](../data-agent/app/api/routers/query_router.py)
- [析问 SQL 仓储实现](../data-agent/app/repositories/mysql/dw/dw_mysql_repository.py)
- [现有 `omdsh-dev/dsh-data-agent`](https://github.com/omdsh-dev/dsh-data-agent)
