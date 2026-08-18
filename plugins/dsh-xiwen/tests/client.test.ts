import { describe, expect, it, vi } from 'vitest'

import { queryXiwen } from '../src/client.js'
import type { XiwenClientConfig } from '../src/types.js'


const encoder = new TextEncoder()


function sseResponse(events: unknown[], status = 200): Response {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const event of events) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`))
      }
      controller.close()
    },
  })
  return new Response(body, {
    status,
    headers: { 'content-type': 'text/event-stream' },
  })
}


function config(overrides: Partial<XiwenClientConfig> = {}): XiwenClientConfig {
  return {
    baseUrl: 'http://127.0.0.1:8000/',
    apiToken: '',
    timeoutMs: 1000,
    maxRows: 2,
    maxResultChars: 50_000,
    includeProgressSummary: false,
    ...overrides,
  }
}


describe('queryXiwen', () => {
  it('sends an authenticated request and bounds returned rows', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(sseResponse([
      { type: 'progress', step: 'recall', status: 'running' },
      {
        type: 'result',
        data: [{ id: 1 }, { id: 2 }, { id: 3 }],
        sql: 'SELECT id FROM orders',
        rowCount: 3,
        truncated: false,
      },
    ]))

    const result = await queryXiwen(
      config({ apiToken: 'secret' }),
      '统计订单',
      new AbortController().signal,
      fetchMock,
    )

    expect(result).toEqual({
      sql: 'SELECT id FROM orders',
      rows: [{ id: 1 }, { id: 2 }],
      rowCount: 2,
      truncated: true,
      message: null,
    })
    expect(fetchMock).toHaveBeenCalledOnce()
    const [url, init] = fetchMock.mock.calls[0] ?? []
    expect(url).toBe('http://127.0.0.1:8000/api/query')
    expect(init?.method).toBe('POST')
    expect(init?.headers).toEqual({
      authorization: 'Bearer secret',
      'content-type': 'application/json',
    })
    expect(init?.body).toBe(JSON.stringify({ query: '统计订单' }))
  })

  it('returns chat messages as a canonical result', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(sseResponse([
      { type: 'chat', message: '我是析问。' },
    ]))

    const result = await queryXiwen(
      config(),
      '你好',
      new AbortController().signal,
      fetchMock,
    )

    expect(result).toEqual({
      sql: null,
      rows: [],
      rowCount: 0,
      truncated: false,
      message: '我是析问。',
    })
  })

  it('returns an empty result without treating it as a missing result', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(sseResponse([
      {
        type: 'result',
        data: [],
        sql: 'SELECT id FROM orders WHERE 1 = 0',
        rowCount: 0,
        truncated: false,
      },
    ]))

    const result = await queryXiwen(
      config(),
      '查找不存在的订单',
      new AbortController().signal,
      fetchMock,
    )

    expect(result).toEqual({
      sql: 'SELECT id FROM orders WHERE 1 = 0',
      rows: [],
      rowCount: 0,
      truncated: false,
      message: null,
    })
  })

  it('optionally summarizes the final state of progress events', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(sseResponse([
      { type: 'progress', step: 'recall_metric', status: 'running', desc: 'Recall metrics' },
      { type: 'progress', step: 'recall_metric', status: 'success', desc: 'Recall metrics' },
      { type: 'result', data: [], sql: 'SELECT 1', rowCount: 0, truncated: false },
    ]))

    const result = await queryXiwen(
      config({ includeProgressSummary: true }),
      '统计订单',
      new AbortController().signal,
      fetchMock,
    )

    expect(result.message).toBe('Xiwen progress: Recall metrics (success)')
  })

  it('bounds serialized row content as well as the row count', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(sseResponse([
      {
        type: 'result',
        data: [{ value: '123' }, { value: '456' }],
        sql: 'SELECT value FROM metrics',
        rowCount: 2,
        truncated: false,
      },
    ]))

    const result = await queryXiwen(
      config({ maxRows: 10, maxResultChars: 20 }),
      '统计指标',
      new AbortController().signal,
      fetchMock,
    )

    expect(result.rows).toEqual([{ value: '123' }])
    expect(result.rowCount).toBe(1)
    expect(result.truncated).toBe(true)
  })

  it('surfaces Xiwen error events without exposing other response data', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(sseResponse([
      { type: 'error', code: 'QUERY_FAILED', message: '问数执行失败' },
    ]))

    await expect(queryXiwen(
      config(),
      '统计订单',
      new AbortController().signal,
      fetchMock,
    )).rejects.toThrow('Xiwen query failed (QUERY_FAILED): 问数执行失败')
  })

  it('rejects non-successful HTTP responses', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 401 }))

    await expect(queryXiwen(
      config(),
      '统计订单',
      new AbortController().signal,
      fetchMock,
    )).rejects.toThrow('Xiwen authentication failed; check the configured apiToken')
  })

  it('rejects successful non-SSE responses', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response('{}', {
      headers: { 'content-type': 'application/json' },
    }))

    await expect(queryXiwen(
      config(),
      '统计订单',
      new AbortController().signal,
      fetchMock,
    )).rejects.toThrow('Xiwen response was not an SSE stream')
  })

  it('rejects streams without a terminal result', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(sseResponse([
      { type: 'progress', step: 'recall', status: 'success' },
    ]))

    await expect(queryXiwen(
      config(),
      '统计订单',
      new AbortController().signal,
      fetchMock,
    )).rejects.toThrow('Xiwen stream ended without a result')
  })

  it('aborts when the configured timeout expires', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (_url, init) => {
      await new Promise((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => reject(new Error('aborted')), { once: true })
      })
      throw new Error('unreachable')
    })

    await expect(queryXiwen(
      config({ timeoutMs: 5 }),
      '统计订单',
      new AbortController().signal,
      fetchMock,
    )).rejects.toThrow('Xiwen request timed out after 5ms')
  })

  it('propagates an external cancellation reason', async () => {
    const controller = new AbortController()
    const reason = new Error('caller cancelled')
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async (_url, init) => {
      await new Promise((_resolve, reject) => {
        init?.signal?.addEventListener('abort', () => reject(new Error('aborted')), { once: true })
      })
      throw new Error('unreachable')
    })

    const pending = queryXiwen(config(), '统计订单', controller.signal, fetchMock)
    controller.abort(reason)

    await expect(pending).rejects.toBe(reason)
  })

  it('cancels an active response stream when the caller aborts', async () => {
    const controller = new AbortController()
    const reason = new Error('caller cancelled streaming')
    let streamCancelled = false
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(
      new ReadableStream<Uint8Array>({
        start(bodyController) {
          bodyController.enqueue(encoder.encode(
            'data: {"type":"progress","step":"recall","status":"running"}\n\n',
          ))
        },
        cancel() {
          streamCancelled = true
        },
      }),
      { headers: { 'content-type': 'text/event-stream' } },
    ))

    const pending = queryXiwen(config(), '统计订单', controller.signal, fetchMock)
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledOnce())
    controller.abort(reason)

    await expect(pending).rejects.toBe(reason)
    expect(streamCancelled).toBe(true)
  })
})
