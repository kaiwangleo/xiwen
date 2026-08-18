/** DeepSeek Harness plugin that exposes Xiwen business analytics as one tool. */

import type { Context } from '@deepseek-ai/cordis'
import { defineTool, type ToolDefinition } from '@deepseek-ai/dsh-tools'
import Schema from '@deepseek-ai/schemastery'

import { queryXiwen } from './client.js'
import type { XiwenClientConfig } from './types.js'

const DEFAULT_BASE_URL = 'http://127.0.0.1:8000'
const DEFAULT_TIMEOUT_MS = 120_000
const DEFAULT_MAX_ROWS = 200
const DEFAULT_MAX_RESULT_CHARS = 50_000
const MAX_TIMER_DELAY_MS = 2_147_483_647

export const name = 'dsh-xiwen'
export const inject = ['tools']

/** Deployment-specific settings for the Xiwen tool. */
export interface Config {
  baseUrl: string
  apiToken?: string
  timeoutMs: number
  maxRows: number
  maxResultChars: number
  includeProgressSummary: boolean
}

/** Runtime configuration validated by Cordis before the plugin loads. */
export const Config: Schema<Config> = Schema.object({
  baseUrl: Schema.string()
    .min(1)
    .pattern(/^https?:\/\/\S+$/u)
    .default(DEFAULT_BASE_URL),
  apiToken: Schema.string().role('secret'),
  timeoutMs: Schema.number().step(1).min(1).max(MAX_TIMER_DELAY_MS).default(DEFAULT_TIMEOUT_MS),
  maxRows: Schema.number().step(1).min(1).max(10_000).default(DEFAULT_MAX_ROWS),
  maxResultChars: Schema.number()
    .step(1)
    .min(1_000)
    .max(1_000_000)
    .default(DEFAULT_MAX_RESULT_CHARS),
  includeProgressSummary: Schema.boolean().default(false),
})

function clientConfig(config: Config): XiwenClientConfig {
  const baseUrl = config.baseUrl.trim()
  let parsed: URL
  try {
    parsed = new URL(baseUrl)
  } catch {
    throw new Error('dsh-xiwen: baseUrl must be a valid HTTP or HTTPS URL')
  }
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error('dsh-xiwen: baseUrl must use HTTP or HTTPS')
  }
  if (parsed.username || parsed.password) {
    throw new Error('dsh-xiwen: baseUrl must not contain credentials; use apiToken')
  }
  if (parsed.search || parsed.hash) {
    throw new Error('dsh-xiwen: baseUrl must not contain a query string or fragment')
  }

  const apiToken = config.apiToken
  if (apiToken !== undefined && apiToken !== '' && apiToken.trim() !== apiToken) {
    throw new Error('dsh-xiwen: apiToken must not have leading or trailing whitespace')
  }

  return {
    baseUrl: baseUrl.replace(/\/+$/u, ''),
    ...(apiToken ? { apiToken } : {}),
    timeoutMs: config.timeoutMs,
    maxRows: config.maxRows,
    maxResultChars: config.maxResultChars,
    includeProgressSummary: config.includeProgressSummary,
  }
}

const QUERY_OUTPUT_SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    sql: {
      required: true,
      oneOf: [{ type: 'string' }, { type: 'null' }],
    },
    rows: {
      type: 'array',
      required: true,
      items: { type: 'object', additionalProperties: true },
    },
    rowCount: { type: 'integer', required: true },
    truncated: { type: 'boolean', required: true },
    message: {
      required: true,
      oneOf: [{ type: 'string' }, { type: 'null' }],
    },
  },
} as const

/** Create the registered tool; the fetch seam keeps network behavior testable. */
export function createXiwenTool(config: Config, fetchImpl: typeof fetch = fetch): ToolDefinition {
  const resolved = clientConfig(config)

  return defineTool({
    name: 'xiwen_query',
    description:
      'Answer structured business analytics questions through the Xiwen semantic layer. Use it for questions that require curated table, column, metric, or enumerated-value knowledge and a read-only analytical query.',
    parameters: {
      query: {
        type: 'string',
        required: true,
        description:
          'A non-empty business question, preferably with the desired metric, dimensions, filters, and time range.',
      },
    },
    output: {
      schema: QUERY_OUTPUT_SCHEMA,
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value) }],
    },
    async execute(args, exec) {
      const query = args.query.trim()
      if (!query) throw new Error('Xiwen query must not be empty')
      return queryXiwen(resolved, query, exec.signal, fetchImpl)
    },
  })
}

/** Register the Xiwen tool after Cordis provides the Harness tool service. */
export function apply(ctx: Context, config: Config): void {
  ctx.tools.register(createXiwenTool(config))
}

export type { JsonValue, XiwenClientConfig, XiwenQueryResult } from './types.js'
