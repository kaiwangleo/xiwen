import { readSSE } from "./sse.js";

/** 发起问数 SSE，事件交给 onEvent。 */
export async function queryStream(query, onEvent) {
  const res = await fetch("/api/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "问数失败");
  }
  await readSSE(res, onEvent);
}
