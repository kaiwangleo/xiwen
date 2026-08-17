import { computed, ref } from "vue";
import { queryStream } from "../api/query.js";

function emptyTurn(query) {
  return {
    id: crypto.randomUUID(),
    query,
    kind: "query",
    localText: "",
    steps: [],
    result: null,
    error: null,
    status: "running",
  };
}

export function useQueryStream() {
  const turns = ref([]);
  const loading = ref(false);

  const currentStep = computed(() => {
    const last = turns.value[turns.value.length - 1];
    if (!last || last.status !== "running") return "";
    const running = [...last.steps].reverse().find((s) => s.status === "running");
    return running?.text || last.steps.at(-1)?.text || "分析中";
  });

  /** 清空当前线程，不删服务端会话。 */
  function clear() {
    turns.value = [];
  }

  /** 用已保存的轮次覆盖本地线程。 */
  function setTurns(next) {
    turns.value = Array.isArray(next) ? next : [];
  }

  /** 追加一条本地闲聊回复。 */
  function addLocal(query, text) {
    turns.value.push({
      ...emptyTurn(query),
      kind: "local",
      localText: text,
      status: "success",
    });
  }

  /** 发起问数 SSE 并原地更新最后一轮。 */
  async function send(query) {
    if (!query || loading.value) return;

    loading.value = true;
    turns.value.push(emptyTurn(query));
    const turn = turns.value[turns.value.length - 1];

    try {
      await queryStream(query, (data) => {
        if (data.type === "progress") {
          let step = turn.steps.find((s) => s.text === data.step);
          if (!step) {
            step = {
              text: data.step,
              status: data.status,
              detail: data.detail || "",
              stack: data.stack || [],
              desc: data.desc || "",
            };
            turn.steps.push(step);
          } else {
            step.status = data.status;
            if (data.detail) step.detail = data.detail;
            if (data.stack) step.stack = data.stack;
            if (data.desc) step.desc = data.desc;
          }
        } else if (data.type === "chat") {
          turn.kind = "local";
          turn.localText = data.message || "";
          turn.status = "success";
        } else if (data.type === "result" && Array.isArray(data.data)) {
          const rows = data.data;
          turn.result = {
            columns: Object.keys(rows[0] || {}),
            rows,
            sql: data.sql || "",
          };
          turn.status = "success";
        } else if (data.type === "error") {
          turn.error = data.message || "发生错误";
          turn.status = "error";
        }
      });

      if (turn.status === "running") {
        turn.status = turn.result ? "success" : "error";
        if (!turn.result && !turn.error) turn.error = "未返回查询结果";
      }
    } catch (e) {
      turn.error = e?.message || "请求失败";
      turn.status = "error";
    } finally {
      loading.value = false;
    }
  }

  return { turns, loading, currentStep, send, clear, addLocal, setTurns };
}
