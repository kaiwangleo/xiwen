import type { Context } from '@deepseek-ai/cordis'
import { describe, expect, it, vi } from 'vitest'

import {
  Config,
  apply,
  createXiwenTool,
  inject,
  name,
  type Config as XiwenPluginConfig,
} from '../src/index.js'

const encoder = new TextEncoder()

function pluginConfig(overrides: Partial<XiwenPluginConfig> = {}): XiwenPluginConfig {
  return {
    baseUrl: 'http://127.0.0.1:8000',
    timeoutMs: 120_000,
    maxRows: 200,
    maxResultChars: 50_000,
    includeProgressSummary: false,
    ...overrides,
  }
}

function resultResponse(): Response {
  return new Response(
    new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            `data: ${JSON.stringify({
              type: 'result',
              data: [{ total: 3 }],
              sql: 'SELECT COUNT(*) AS total FROM orders',
              rowCount: 1,
              truncated: false,
            })}\n\n`,
          ),
        )
        controller.close()
      },
    }),
    { headers: { 'content-type': 'text/event-stream' } },
  )
}

describe('dsh-xiwen plugin', () => {
  it('exports stable plugin metadata and validated defaults', () => {
    expect(name).toBe('dsh-xiwen')
    expect(inject).toEqual(['tools'])
    expect(Config({} as XiwenPluginConfig)).toEqual(pluginConfig())
  })

  it('rejects invalid numeric configuration before plugin loading', () => {
    expect(() => Config({ timeoutMs: 0 } as XiwenPluginConfig)).toThrow()
    expect(() => Config({ maxRows: 0 } as XiwenPluginConfig)).toThrow()
    expect(() => Config({ maxResultChars: 999 } as XiwenPluginConfig)).toThrow()
  })

  it('rejects unsafe or malformed service URLs', () => {
    expect(() => createXiwenTool(pluginConfig({ baseUrl: 'ftp://127.0.0.1' }))).toThrow(
      'baseUrl must use HTTP or HTTPS',
    )
    expect(() =>
      createXiwenTool(pluginConfig({ baseUrl: 'http://user:secret@127.0.0.1' })),
    ).toThrow('baseUrl must not contain credentials')
    expect(() => createXiwenTool(pluginConfig({ baseUrl: 'not a URL' }))).toThrow(
      'baseUrl must be a valid HTTP or HTTPS URL',
    )
  })

  it('registers the xiwen_query tool with the Harness tool service', () => {
    const register = vi.fn()
    const ctx = { tools: { register } } as unknown as Context

    apply(ctx, pluginConfig())

    expect(register).toHaveBeenCalledOnce()
    expect(register.mock.calls[0]?.[0]).toMatchObject({
      name: 'xiwen_query',
      parameters: {
        type: 'object',
        properties: {
          query: { type: 'string', description: expect.any(String) },
        },
        required: ['query'],
      },
    })
  })

  it('executes with the Harness cancellation signal and returns canonical JSON', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(resultResponse())
    const tool = createXiwenTool(pluginConfig(), fetchMock)
    const signal = new AbortController().signal

    const value = await tool.execute({ query: '  统计订单数量  ' }, { signal } as never)

    expect(value).toEqual({
      sql: 'SELECT COUNT(*) AS total FROM orders',
      rows: [{ total: 3 }],
      rowCount: 1,
      truncated: false,
      message: null,
    })
    expect(fetchMock.mock.calls[0]?.[1]?.signal).toBeInstanceOf(AbortSignal)
    expect(fetchMock.mock.calls[0]?.[1]?.body).toBe(JSON.stringify({ query: '统计订单数量' }))
  })

  it('rejects an empty business question without calling the service', async () => {
    const fetchMock = vi.fn<typeof fetch>()
    const tool = createXiwenTool(pluginConfig(), fetchMock)

    await expect(
      tool.execute({ query: '   ' }, { signal: new AbortController().signal } as never),
    ).rejects.toThrow('Xiwen query must not be empty')
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
