/** JSON values exchanged with the Xiwen service and DSH tool runtime. */
export type JsonValue =
  | null
  | boolean
  | number
  | string
  | JsonValue[]
  | { [key: string]: JsonValue }

export interface XiwenClientConfig {
  baseUrl: string
  apiToken?: string
  timeoutMs: number
  maxRows: number
  maxResultChars: number
  includeProgressSummary: boolean
}

export interface XiwenQueryResult {
  sql: string | null
  rows: Array<Record<string, JsonValue>>
  rowCount: number
  truncated: boolean
  message: string | null
}
