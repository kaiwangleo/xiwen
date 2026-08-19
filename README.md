# Xiwen（析问）

析问是一个面向中文业务问数的开源 Data Agent。它把人工维护的表、字段和指标语义层，与 Qdrant 向量召回、Elasticsearch 枚举值召回及固定的 SQL 生成链路结合起来，将自然语言业务问题转换为 MySQL 分析查询。

本项目仍处于早期开发阶段，适合本地验证和二次开发；生产部署前请完成权限隔离、安全审计和真实数据集评估。

## 架构

```text
Vue 3 工作台 / DeepSeek Harness 插件
                         │ HTTP + SSE
                         ▼
                  FastAPI / LangGraph
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  MySQL 元数据与数仓   Qdrant 字段/指标   Elasticsearch 枚举值
                         │
                         ▼
                 Embedding + LLM 服务
```

DeepSeek Harness 适配层位于 [`plugins/dsh-xiwen`](plugins/dsh-xiwen)，只负责把 `xiwen_query` 工具请求转发给析问服务；它不会安装或托管 Python 后端及其数据依赖。

## 主要能力

- 使用人工维护的表、字段、别名和指标元数据表达业务语义。
- 通过 Qdrant 召回相关字段和指标，通过 Elasticsearch 对齐枚举值。
- 使用固定的 LangGraph 链路完成关键词提取、召回、过滤、SQL 生成、校验、纠错和执行。
- 提供基于 SSE 的问数接口以及语义配置、知识构建和会话管理接口。
- 提供 Vue 3 工作台，用于问数、配置语义层和触发知识构建。

## 仓库结构

```text
data-agent/          Python 3.12+ / FastAPI 后端
data-agent-fronted/  Vue 3 / Vite 工作台（保留历史目录名）
plugins/dsh-xiwen/   DeepSeek Harness 插件适配层
docs/                项目计划与补充文档
```

## 本地启动

### 前置条件

- Python 3.12 或更高版本，以及 [uv](https://docs.astral.sh/uv/)
- Node.js 和 npm
- Docker 与 Docker Compose
- 一个 OpenAI 兼容的 LLM 接口
- 本地 `BAAI/bge-large-zh-v1.5` 模型文件，或可替代的兼容 Embedding 服务

### 1. 配置后端

复制示例配置并填写本地连接信息。活动配置 `data-agent/conf/app_config.yaml` 已被 Git 忽略，请勿提交其中的密码或 Token。

```bash
cd data-agent
cp .env.example .env
cp conf/app_config.example.yaml conf/app_config.yaml
```

`.env` 为 Docker Compose 提供本地 MySQL 凭据，`app_config.yaml` 中的元数据库和只读数仓账号必须与其保持一致。MySQL 初始化脚本只会在新数据卷首次创建时配置 `xiwen_meta` 和 `xiwen_readonly`；已有数据卷需要手动创建这两个账号，或在备份数据后主动重建。

至少需要配置 `llm.model_name`、`llm.base_url` 和 `llm.api_key`。远程部署还应设置非空的 `api.auth_token`。示例配置中的占位密码不能用于生产环境；应用层认证不能替代 TLS 和网络访问控制。

Embedding 容器默认从以下目录读取模型，模型权重不会进入 Git：

```text
data-agent/docker/embedding/models/bge-large-zh-v1.5
```

### 2. 启动依赖和后端

```bash
cd data-agent
docker compose up -d
uv sync
uv run python main.py
```

`python main.py` 默认绑定 `0.0.0.0:8000`，本机可通过 `http://127.0.0.1:8000` 访问。若不需要局域网访问，请改用仅绑定 `127.0.0.1` 的 Uvicorn 启动参数。首次问数前，需要在工作台中确认数据源和语义配置，并完成一次知识构建。

### 3. 启动工作台

```bash
cd data-agent-fronted
npm install
npm run dev
```

Vite 开发服务器通常监听 `http://127.0.0.1:5173`，并将 `/api` 转发到后端的 `8000` 端口。

更完整的链路和配置说明见 [`data-agent/docs/技术架构.md`](data-agent/docs/技术架构.md)。

### 4. 连接 DeepSeek Harness

插件 `0.1.0` 已发布到 npm，也可以从本地检出或本地 tarball 安装，并通过独立的 Harness profile 启用：

```bash
dsh plugin --profile xiwen add @kaiwangleo/dsh-xiwen@0.1.0
dsh --profile xiwen --dump-config
```

本地检出安装仍可使用：

```bash
npm --prefix plugins/dsh-xiwen ci
npm --prefix plugins/dsh-xiwen run build
dsh plugin --profile xiwen add ./plugins/dsh-xiwen
```

安装、配置、安全边界和卸载方法见 [`plugins/dsh-xiwen/README.md`](plugins/dsh-xiwen/README.md)。

## 配置示例

- 后端：[`data-agent/conf/app_config.example.yaml`](data-agent/conf/app_config.example.yaml)
- Harness 插件：[`plugins/dsh-xiwen/cordis.patch.example.yml`](plugins/dsh-xiwen/cordis.patch.example.yml)

示例只包含本机地址和明显的占位凭据。请通过受控的本地配置或密钥管理系统提供真实凭据。

## 当前限制与安全边界

- 当前数据仓库实现只支持 MySQL，且需要人工维护语义层。
- MySQL、Qdrant、Elasticsearch、Embedding 和 LLM 服务必须单独部署。
- 查询质量取决于语义元数据、模型能力和真实数据分布，不能保证生成结果始终正确。
- 应为查询执行配置专用的只读数据库账号、查询超时和结果上限；不要使用 root 账号处理真实数据。
- 应用层认证不能替代 TLS、网络访问控制、速率限制和反向代理加固。
- 不要将服务直接暴露到不受信任的网络，也不要在未审查的生产数据上直接执行模型生成的 SQL。

## License

本项目采用 [MIT License](LICENSE)。
