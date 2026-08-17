/** 消费 SSE 文本流，对每条 data: JSON 调用 onEvent。 */
export async function readSSE(response, onEvent) {
  if (!response.body) throw new Error("服务器未返回流");
  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop();
    for (const evt of events) {
      const line = evt.trim();
      if (!line.startsWith("data:")) continue;
      try {
        onEvent(JSON.parse(line.replace(/^data:\s*/, "")));
      } catch {
        /* ignore */
      }
    }
  }
}
