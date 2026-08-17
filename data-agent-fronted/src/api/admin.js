import { jsonOptions, request } from "./http.js";
import { readSSE } from "./sse.js";

/** 读取打码后的运行时配置。 */
export async function getConfig() {
  return request("/api/admin/config", {}, "读取配置失败");
}

/** 保存运行时配置并热加载。 */
export async function saveConfig(payload) {
  return request("/api/admin/config", jsonOptions("PUT", payload), "保存配置失败");
}

/** 下载 YAML 的地址。 */
export function exportConfigUrl() {
  return "/api/admin/config.yaml";
}

/** 读取数仓表清单。 */
export async function getDatasourceTables() {
  return request("/api/admin/datasource/tables", {}, "读取数据源表失败");
}

/** 读取语义编辑稿。 */
export async function getMetaConfig() {
  return request("/api/admin/meta-config", {}, "读取表/指标失败");
}

/** 保存语义编辑稿到元库，不自动构建。 */
export async function saveMetaConfig(payload) {
  return request("/api/admin/meta-config", jsonOptions("PUT", payload), "保存表/指标失败");
}

/** 列出提示词。 */
export async function getPrompts() {
  return request("/api/admin/prompts", {}, "读取提示词失败");
}

/** 覆盖保存一条提示词。 */
export async function savePrompt(id, content) {
  return request(`/api/admin/prompts/${id}`, jsonOptions("PUT", { content }), "保存提示词失败");
}

/** 从出厂文件恢复提示词。 */
export async function resetPrompt(id) {
  return request(`/api/admin/prompts/${id}/reset`, { method: "POST" }, "恢复默认失败");
}

/** 跑知识构建 SSE，每条事件回调 onEvent。 */
export async function buildKnowledge(onEvent) {
  const res = await fetch("/api/admin/knowledge/build", { method: "POST" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "构建失败");
  }
  await readSSE(res, onEvent);
}
