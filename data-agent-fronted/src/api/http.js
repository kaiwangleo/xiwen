/** 解析 JSON 响应；非 2xx 抛出 detail。 */
export async function request(url, options = {}, fallback = "请求失败") {
  const res = await fetch(url, options);
  if (!res.ok) {
    let detail = fallback;
    try {
      const data = await res.json();
      detail = data.detail || fallback;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

/** 组装 JSON PUT/POST。 */
export function jsonOptions(method, body) {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}
