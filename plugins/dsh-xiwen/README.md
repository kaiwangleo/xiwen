# dsh-xiwen

`dsh-xiwen` connects [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) to Xiwen (析问), a Chinese business analytics agent backed by a curated semantic layer.

The plugin registers one model-facing tool, `xiwen_query`. It sends a business question to a separately deployed Xiwen service, consumes the JSON-over-SSE response, and returns bounded structured data to Harness.

> This package has not been published to npm yet. Install it from a local checkout or a locally built tarball until a release is available.

## Architecture and responsibilities

```text
DeepSeek Harness
    | xiwen_query
    v
@kaiwangleo/dsh-xiwen
    | POST /api/query + Bearer token + SSE
    v
Xiwen FastAPI / LangGraph service
    |-- MySQL metadata and read-only warehouse access
    |-- Qdrant field and metric recall
    |-- Elasticsearch enumerated-value recall
    |-- Embedding service
    `-- OpenAI-compatible LLM service
```

The plugin is only the Harness adapter. It does **not** install, start, configure, or monitor the Python service, MySQL, Qdrant, Elasticsearch, the Embedding service, an LLM, or the Xiwen web workbench.

## What `xiwen_query` does

The tool accepts one required argument:

```json
{
  "query": "统计 2025 年各地区的销售总额"
}
```

Use it for structured business questions that depend on curated tables, columns, metrics, aliases, enumerated values, filters, or time dimensions. It is not a general web-search or arbitrary database administration tool.

A successful call returns this canonical JSON shape:

```json
{
  "sql": "SELECT ...",
  "rows": [],
  "rowCount": 0,
  "truncated": false,
  "message": null
}
```

The adapter understands Xiwen's `progress`, `result`, `error`, and `chat` SSE events. It forwards Harness cancellation to the HTTP stream, applies its own timeout, and bounds results by both row count and serialized row characters.

## Requirements

- Node.js `^22.19.0` or `>=24.0.0`.
- A compatible DeepSeek Harness installation. The supported tool-runtime range is declared in [`package.json`](package.json).
- A separately running Xiwen backend and all of its dependencies.
- A configured semantic layer and a completed knowledge build before the first analytical query.

The current Xiwen warehouse implementation supports MySQL only.

## Start the Xiwen backend

From the Xiwen repository, create local configuration files and replace every `CHANGE_ME` value:

```bash
cd data-agent
cp .env.example .env
cp conf/app_config.example.yaml conf/app_config.yaml
```

Keep the metadata and warehouse credentials in `conf/app_config.yaml` consistent with `.env`. In particular, `db_dw` should use the dedicated read-only warehouse account rather than `root` or the metadata account.

Place a compatible `BAAI/bge-large-zh-v1.5` model under `data-agent/docker/embedding/models/bge-large-zh-v1.5`, then start the infrastructure containers:

```bash
docker compose up -d
```

This Compose file starts MySQL, Qdrant, Elasticsearch, and the Embedding service. Start the Python API separately:

```bash
uv sync
uv run python main.py
```

The default API address is `http://127.0.0.1:8000`. Check dependency readiness before connecting Harness:

```bash
curl http://127.0.0.1:8000/api/health
```

The response should report `"status": "ok"`. A degraded response identifies unavailable dependencies without exposing credentials or connection details.

Before the first query, use the Xiwen workbench to select warehouse tables, maintain table/column/metric metadata, and complete a knowledge build. See the [repository setup guide](../../README.md) and [technical architecture](../../data-agent/docs/技术架构.md).

## Install into a Harness profile

### Local checkout

From the Xiwen repository root, install dependencies and build the ESM entry point:

```bash
npm --prefix plugins/dsh-xiwen ci
npm --prefix plugins/dsh-xiwen run build
dsh plugin --profile xiwen add ./plugins/dsh-xiwen
```

### Local tarball

To exercise the same package boundary used by a future registry release:

```bash
cd plugins/dsh-xiwen
npm ci
npm pack
dsh plugin --profile xiwen add ./kaiwangleo-dsh-xiwen-0.1.0.tgz
```

Verify that Harness loaded the bundle layer:

```bash
dsh --profile xiwen --dump-config
```

The output should contain an `xiwen` row whose package name is `@kaiwangleo/dsh-xiwen`. Start Harness with the same profile:

```bash
dsh --profile xiwen
```

Then ask the model to use `xiwen_query`, for example:

```text
Use xiwen_query to answer: 统计 2025 年各地区的销售总额
```

## Configuration

The bundled patch defaults to the loopback Xiwen service. To override it, add an `xiwen` row to the profile's `cordis.patch.yml`:

```yaml
- insert:
    - id: xiwen
      name: '@kaiwangleo/dsh-xiwen'
      config:
        baseUrl: 'http://127.0.0.1:8000'
        apiToken: 'REPLACE_WITH_THE_BACKEND_API_AUTH_TOKEN'
        timeoutMs: 120000
        maxRows: 200
        maxResultChars: 50000
        includeProgressSummary: false
```

Do not commit a real `apiToken`. Omit it when the local backend has no token configured.

| Setting | Default | Meaning |
|---|---:|---|
| `baseUrl` | `http://127.0.0.1:8000` | Xiwen service root. Only HTTP and HTTPS URLs without embedded credentials, query strings, or fragments are accepted. |
| `apiToken` | unset | Optional Bearer token matching `api.auth_token` in the backend configuration. |
| `timeoutMs` | `120000` | Whole-request timeout, including SSE consumption. |
| `maxRows` | `200` | Maximum rows returned to the model; accepted range is 1–10,000. |
| `maxResultChars` | `50000` | Maximum serialized row characters returned to the model; accepted range is 1,000–1,000,000. |
| `includeProgressSummary` | `false` | When enabled, include the final state of observed progress steps in `message` for result events. |

Invalid configuration fails when the plugin loads. A trailing slash in `baseUrl` is accepted; the adapter appends `/api/query` exactly once.

## Security and data handling

- Use a dedicated MySQL account limited to `SELECT` and `SHOW VIEW` on the warehouse database. Xiwen's health endpoint verifies that the active warehouse grants are read-only.
- Configure `api.auth_token` for any deployment beyond an isolated local machine and set the same value as the plugin's `apiToken`.
- Use HTTPS through a trusted reverse proxy when traffic leaves the host. A Bearer token does not provide transport encryption.
- Keep Xiwen and its dependency ports off untrusted networks. Apply firewall rules, reverse-proxy request limits, and rate limiting appropriate to the deployment.
- Treat returned rows as data disclosed to the configured Harness model provider. Do not query sensitive production data unless that disclosure is permitted.
- Keep the backend SQL timeout and row limit enabled. The plugin's `timeoutMs`, `maxRows`, and `maxResultChars` are additional model-output bounds, not substitutes for database-side controls.
- Review generated SQL and query results during evaluation. Read-only enforcement prevents mutation but does not guarantee analytical correctness or prevent expensive reads within the configured timeout.

## Why Xiwen is different

Xiwen is centered on Chinese business analytics rather than generic text-to-SQL. Its query path uses:

- manually curated table, column, alias, and metric metadata;
- Qdrant vector recall for relevant fields and business metrics;
- Elasticsearch recall for enumerated values found in business questions;
- a fixed LangGraph sequence for keyword extraction, recall, filtering, SQL generation, validation, correction, and execution; and
- a separate workbench for maintaining the semantic layer and building retrieval knowledge.

The adapter exposes those existing Xiwen capabilities to Harness; it does not claim support for databases or retrieval systems that the backend does not implement.

Suggested catalog description:

> Semantic-layer analytics tool that uses curated table, column and metric metadata with Qdrant and Elasticsearch recall to generate, validate and execute MySQL analytical queries through the Xiwen service.

## Troubleshooting

- `Xiwen authentication failed`: make `apiToken` exactly match the backend's `api.auth_token`.
- `Xiwen service is unavailable`: check `/api/health`, the Python process, and every Compose dependency.
- `Xiwen stream ended without a result`: inspect backend logs for a terminated query graph or reverse-proxy buffering/timeout issue.
- `truncated: true`: the backend or plugin result bound was reached; narrow the requested dimensions or filters rather than increasing limits without review.

## Uninstall

Remove the package and its bundle layer from the profile:

```bash
dsh plugin --profile xiwen remove @kaiwangleo/dsh-xiwen
dsh --profile xiwen --dump-config
```

Removing the plugin does not stop or delete the Xiwen backend, databases, Docker volumes, model files, or local configuration. Remove those separately only when their data is no longer needed.

## License

[MIT](../../LICENSE)
