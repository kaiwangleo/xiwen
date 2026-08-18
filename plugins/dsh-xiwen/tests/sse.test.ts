import { describe, expect, it } from 'vitest'

import { parseSseStream } from '../src/sse.js'


function streamOf(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
      controller.close()
    },
  })
}


async function collect(chunks: string[]): Promise<unknown[]> {
  const events: unknown[] = []
  for await (const event of parseSseStream(streamOf(chunks))) events.push(event)
  return events
}


describe('parseSseStream', () => {
  it('parses JSON split across arbitrary network chunks', async () => {
    const events = await collect([
      'data: {"type":"pro',
      'gress","step":"recall"}\n\n',
      'data: {"type":"result","data":[{"value":1}],',
      '"sql":"SELECT 1"}\n\n',
    ])

    expect(events).toEqual([
      { type: 'progress', step: 'recall' },
      { type: 'result', data: [{ value: 1 }], sql: 'SELECT 1' },
    ])
  })

  it('supports CRLF and multi-line data fields', async () => {
    const events = await collect([
      ': heartbeat\r\n',
      'event: message\r\n',
      'data: {\r\n',
      'data: "type":"chat","message":"hello"}\r\n\r\n',
    ])

    expect(events).toEqual([{ type: 'chat', message: 'hello' }])
  })

  it('flushes the final event without a trailing blank line', async () => {
    const events = await collect(['data: {"type":"chat","message":"done"}'])

    expect(events).toEqual([{ type: 'chat', message: 'done' }])
  })

  it('rejects invalid JSON data', async () => {
    await expect(collect(['data: not-json\n\n'])).rejects.toThrow('Invalid Xiwen SSE data')
  })

  it('cancels the source when a consumer stops before the stream ends', async () => {
    const encoder = new TextEncoder()
    let cancelled = false
    const stream = new ReadableStream<Uint8Array>({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"chat","message":"done"}\n\n'))
      },
      cancel() {
        cancelled = true
      },
    })

    for await (const _event of parseSseStream(stream)) break

    expect(cancelled).toBe(true)
  })
})
