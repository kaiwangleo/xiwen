/** HTTP client for Xiwen's JSON-over-SSE query endpoint. */

import { parseSseStream } from './sse.js'
import type { JsonValue, XiwenClientConfig, XiwenQueryResult } from './types.js'


const MAX_ERROR_MESSAGE_CHARS = 500
const MAX_PROGRESS_SUMMARY_CHARS = 1000


type ProgressStatus = 'running' | 'success' | 'error'


interface ProgressState {
  label: string
  status: ProgressStatus
}


function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}


function cancellationReason(signal: AbortSignal): Error {
  return signal.reason instanceof Error
    ? signal.reason
    : new DOMException('The operation was aborted', 'AbortError')
}


function boundRows(
  input: Array<Record<string, JsonValue>>,
  maxRows: number,
  maxResultChars: number,
): Array<Record<string, JsonValue>> {
  const rows: Array<Record<string, JsonValue>> = []
  let serializedChars = 2

  for (const row of input) {
    if (rows.length >= maxRows) break
    let serialized: string
    try {
      serialized = JSON.stringify(row)
    } catch (error) {
      throw new Error('Invalid Xiwen result rows', { cause: error })
    }
    const nextSize = serializedChars + serialized.length + (rows.length === 0 ? 0 : 1)
    if (nextSize > maxResultChars) break
    rows.push(row)
    serializedChars = nextSize
  }

  return rows
}


function progressMessage(progress: Map<string, ProgressState>): string | null {
  if (progress.size === 0) return null
  const detail = [...progress.values()]
    .map(({ label, status }) => `${label} (${status})`)
    .join(' -> ')
  const message = `Xiwen progress: ${detail}`
  if (message.length <= MAX_PROGRESS_SUMMARY_CHARS) return message
  return `${message.slice(0, MAX_PROGRESS_SUMMARY_CHARS - 3)}...`
}


function normalizeProgress(
  event: Record<string, unknown>,
  progress: Map<string, ProgressState>,
): void {
  const { step, status } = event
  if (
    typeof step !== 'string'
    || !['running', 'success', 'error'].includes(String(status))
  ) {
    throw new Error('Invalid Xiwen progress event')
  }
  const label = typeof event.desc === 'string' && event.desc.trim()
    ? event.desc.trim()
    : step
  progress.set(step, { label, status: status as ProgressStatus })
}


function normalizeResult(
  event: Record<string, unknown>,
  config: XiwenClientConfig,
  progress: Map<string, ProgressState>,
): XiwenQueryResult {
  if (
    !Array.isArray(event.data)
    || typeof event.sql !== 'string'
    || !Number.isSafeInteger(event.rowCount)
    || (event.rowCount as number) < 0
    || event.rowCount !== event.data.length
    || typeof event.truncated !== 'boolean'
  ) {
    throw new Error('Invalid Xiwen result event')
  }
  if (!event.data.every(isRecord)) throw new Error('Invalid Xiwen result rows')

  const input = event.data as Array<Record<string, JsonValue>>
  const rows = boundRows(input, config.maxRows, config.maxResultChars)
  return {
    sql: event.sql,
    rows,
    rowCount: rows.length,
    truncated: event.truncated || input.length > rows.length,
    message: config.includeProgressSummary ? progressMessage(progress) : null,
  }
}


function normalizeChat(event: Record<string, unknown>): XiwenQueryResult {
  if (typeof event.message !== 'string') throw new Error('Invalid Xiwen chat event')
  return {
    sql: null,
    rows: [],
    rowCount: 0,
    truncated: false,
    message: event.message,
  }
}


function cleanErrorText(value: unknown, fallback: string): string {
  if (typeof value !== 'string') return fallback
  const cleaned = value.replace(/[\u0000-\u001f\u007f]+/gu, ' ').trim()
  return cleaned ? cleaned.slice(0, MAX_ERROR_MESSAGE_CHARS) : fallback
}


function errorFromEvent(event: Record<string, unknown>): Error {
  const rawCode = typeof event.code === 'string' ? event.code : ''
  const code = /^[A-Z][A-Z0-9_]{0,63}$/u.test(rawCode) ? rawCode : 'QUERY_FAILED'
  const message = cleanErrorText(event.message, 'Xiwen query failed')
  return new Error(`Xiwen query failed (${code}): ${message}`)
}


function httpError(status: number): Error {
  if (status === 401 || status === 403) {
    return new Error('Xiwen authentication failed; check the configured apiToken')
  }
  if (status === 413) return new Error('Xiwen rejected the request because it was too large')
  if (status === 422) return new Error('Xiwen rejected the query; check that it is non-empty and within the configured length limit')
  if (status === 429) return new Error('Xiwen is rate-limiting requests; retry later')
  if (status >= 500) return new Error(`Xiwen service is unavailable (HTTP ${status})`)
  return new Error(`Xiwen request failed (HTTP ${status})`)
}


function validateClientConfig(config: XiwenClientConfig): void {
  if (!Number.isSafeInteger(config.maxRows) || config.maxRows <= 0) {
    throw new Error('maxRows must be a positive integer')
  }
  if (!Number.isSafeInteger(config.maxResultChars) || config.maxResultChars <= 0) {
    throw new Error('maxResultChars must be a positive integer')
  }
  if (!Number.isSafeInteger(config.timeoutMs) || config.timeoutMs <= 0) {
    throw new Error('timeoutMs must be a positive integer')
  }
}


/** Query Xiwen and return one bounded canonical result for the DSH tool runtime. */
export async function queryXiwen(
  config: XiwenClientConfig,
  query: string,
  signal: AbortSignal,
  fetchImpl: typeof fetch = fetch,
): Promise<XiwenQueryResult> {
  validateClientConfig(config)
  if (signal.aborted) throw cancellationReason(signal)

  const controller = new AbortController()
  let timedOut = false
  const onAbort = () => controller.abort(signal.reason)
  signal.addEventListener('abort', onAbort, { once: true })
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, config.timeoutMs)

  const headers: Record<string, string> = { 'content-type': 'application/json' }
  if (config.apiToken) headers.authorization = `Bearer ${config.apiToken}`

  try {
    const response = await fetchImpl(
      `${config.baseUrl.replace(/\/$/u, '')}/api/query`,
      {
        method: 'POST',
        headers,
        body: JSON.stringify({ query }),
        signal: controller.signal,
      },
    )
    if (!response.ok) throw httpError(response.status)
    if (response.body === null) throw new Error('Xiwen response did not include an SSE stream')
    const contentType = response.headers.get('content-type')?.toLowerCase() ?? ''
    if (!contentType.includes('text/event-stream')) {
      throw new Error('Xiwen response was not an SSE stream')
    }

    const progress = new Map<string, ProgressState>()
    let terminal: XiwenQueryResult | undefined
    for await (const rawEvent of parseSseStream(response.body, controller.signal)) {
      if (!isRecord(rawEvent) || typeof rawEvent.type !== 'string') {
        throw new Error('Invalid Xiwen SSE event')
      }
      if (terminal !== undefined) throw new Error('Xiwen stream included data after its terminal event')

      if (rawEvent.type === 'progress') {
        normalizeProgress(rawEvent, progress)
      } else if (rawEvent.type === 'result') {
        terminal = normalizeResult(rawEvent, config, progress)
      } else if (rawEvent.type === 'chat') {
        terminal = normalizeChat(rawEvent)
      } else if (rawEvent.type === 'error') {
        throw errorFromEvent(rawEvent)
      } else {
        throw new Error(`Unsupported Xiwen SSE event type: ${rawEvent.type}`)
      }
    }
    if (terminal === undefined) throw new Error('Xiwen stream ended without a result')
    return terminal
  } catch (error) {
    if (signal.aborted) throw cancellationReason(signal)
    if (timedOut) {
      throw new Error(`Xiwen request timed out after ${config.timeoutMs}ms`, { cause: error })
    }
    if (error instanceof TypeError) {
      throw new Error('Unable to reach the Xiwen service', { cause: error })
    }
    throw error
  } finally {
    clearTimeout(timer)
    signal.removeEventListener('abort', onAbort)
  }
}
