import { jsonOptions, request } from "./http.js";

/** 列出会话摘要。 */
export async function listSessions() {
  return request("/api/sessions", {}, "读取会话失败");
}

/** 新建空会话。 */
export async function createSession(title = "新会话") {
  return request("/api/sessions", jsonOptions("POST", { title }), "创建会话失败");
}

/** 取会话整包。 */
export async function getSession(id) {
  return request(`/api/sessions/${id}`, {}, "读取会话失败");
}

/** 只改标题。 */
export async function renameSession(id, title) {
  return request(`/api/sessions/${id}`, jsonOptions("PUT", { title }), "重命名失败");
}

/** 整包保存轮次。 */
export async function saveSession(id, payload) {
  return request(`/api/sessions/${id}`, jsonOptions("PUT", payload), "保存会话失败");
}

/** 删除会话。 */
export async function deleteSession(id) {
  return request(`/api/sessions/${id}`, { method: "DELETE" }, "删除会话失败");
}
