/** Incremental parsing for Xiwen's JSON-over-SSE response stream. */

function parseEventBlock(block: string): unknown | undefined {
  const dataLines: string[] = []
  for (const line of block.split(/\r?\n/u)) {
    if (!line.startsWith('data:')) continue
    const value = line.slice('data:'.length)
    dataLines.push(value.startsWith(' ') ? value.slice(1) : value)
  }
  if (dataLines.length === 0) return undefined

  const data = dataLines.join('\n')
  try {
    return JSON.parse(data) as unknown
  } catch (error) {
    throw new Error('Invalid Xiwen SSE data', { cause: error })
  }
}

/** Yield each JSON value from an SSE byte stream without assuming chunk boundaries. */
export async function* parseSseStream(
  stream: ReadableStream<Uint8Array>,
  signal?: AbortSignal,
): AsyncGenerator<unknown> {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let streamEnded = false
  const onAbort = () => {
    void reader.cancel(signal?.reason).catch(() => undefined)
  }
  signal?.addEventListener('abort', onAbort, { once: true })
  if (signal?.aborted) onAbort()

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        streamEnded = true
        break
      }
      buffer += decoder.decode(value, { stream: true })

      let separator = /\r?\n\r?\n/u.exec(buffer)
      while (separator !== null) {
        const block = buffer.slice(0, separator.index)
        buffer = buffer.slice(separator.index + separator[0].length)
        const event = parseEventBlock(block)
        if (event !== undefined) yield event
        separator = /\r?\n\r?\n/u.exec(buffer)
      }
    }

    buffer += decoder.decode()
    if (buffer.trim()) {
      const event = parseEventBlock(buffer)
      if (event !== undefined) yield event
    }
  } finally {
    signal?.removeEventListener('abort', onAbort)
    if (!streamEnded) {
      try {
        await reader.cancel()
      } catch {
        // The fetch body may already be errored by an AbortSignal.
      }
    }
    reader.releaseLock()
  }
}
