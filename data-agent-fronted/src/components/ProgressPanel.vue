<template>
  <div class="panel" :class="status">
    <button type="button" class="summary" @click="open = !open">
      <span class="pulse" :class="status"></span>
      <span class="label">{{ summary }}</span>
      <span class="toggle">{{ open ? "收起" : "展开" }}</span>
    </button>
    <ol v-if="open" class="steps">
      <li v-for="(step, index) in displaySteps" :key="step.text + index">
        <div class="head">
          <span class="dot" :class="step.status"></span>
          <div class="title">
            <div class="name-row">
              <span class="name">{{ step.text }}</span>
              <span v-for="item in step.stack" :key="item" class="stack">{{ item }}</span>
            </div>
            <p v-if="step.desc" class="desc">{{ step.desc }}</p>
          </div>
        </div>
        <pre v-if="step.detail" class="detail">{{ step.detail }}</pre>
        <p v-else-if="step.status === 'running'" class="wait">处理中…</p>
      </li>
    </ol>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const FALLBACK = {
  抽取关键字: { stack: ["jieba"], desc: "按名词、动词、专名等词性抽关键词，并保留原问句" },
  召回字段: { stack: ["LLM", "Embedding", "Qdrant"], desc: "大模型扩展关键词，Embedding 后检索 Qdrant 字段集合" },
  召回指标: { stack: ["LLM", "Embedding", "Qdrant"], desc: "大模型扩展关键词，Embedding 后检索 Qdrant 指标集合" },
  召回字段取值: { stack: ["LLM", "Elasticsearch"], desc: "大模型抽出取值词，再用 IK 在 Elasticsearch 检索字段枚举" },
  合并召回信息: { stack: ["MySQL meta"], desc: "把字段、取值、指标按表拼起来，并补上主外键" },
  过滤指标: { stack: ["LLM"], desc: "大模型按问题从召回指标里筛出真正要用的" },
  过滤表格: { stack: ["LLM"], desc: "大模型按问题留下相关表和字段，去掉无关列" },
  添加额外上下文信息: { stack: ["MySQL 数仓"], desc: "补上今天的日期/星期/季度和数仓方言版本" },
  生成SQL: { stack: ["LLM"], desc: "结合表、指标、日期和库类型生成查询 SQL" },
  验证SQL: { stack: ["MySQL EXPLAIN"], desc: "对生成的 SQL 做 EXPLAIN，语法或权限错误会走校正" },
  校正SQL: { stack: ["LLM"], desc: "根据 EXPLAIN 报错改写 SQL" },
  执行SQL: { stack: ["MySQL 数仓"], desc: "在数仓执行最终 SQL 并返回结果行" },
};

const props = defineProps({
  steps: { type: Array, default: () => [] },
  status: { type: String, default: "running" },
});

const open = ref(true);

const displaySteps = computed(() =>
  props.steps.map((step) => {
    const fallback = FALLBACK[step.text] || {};
    return {
      ...step,
      stack: step.stack?.length ? step.stack : fallback.stack || [],
      desc: step.desc || fallback.desc || "",
    };
  }),
);

const summary = computed(() => {
  const total = props.steps.length;
  const running = [...props.steps].reverse().find((s) => s.status === "running");
  if (props.status === "running") {
    const name = running?.text || "分析中";
    return total ? `正在${name}（${total} 步）` : "正在分析…";
  }
  if (props.status === "error") return "查询失败 · 执行详情";
  return total ? `已完成 · 执行详情` : "已完成";
});
</script>

<style scoped>
.panel {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.summary {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border: 0;
  background: transparent;
  color: var(--text);
  text-align: left;
}

.label {
  flex: 1;
  font-size: 13px;
  color: var(--muted);
}

.toggle {
  font-size: 12px;
  color: var(--accent);
}

.pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--muted);
}

.pulse.running {
  background: var(--warning);
  box-shadow: 0 0 0 4px rgba(217, 119, 6, 0.15);
}

.pulse.success {
  background: var(--success);
}

.pulse.error {
  background: var(--danger);
}

.steps {
  margin: 0;
  padding: 0 14px 14px;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.title {
  min-width: 0;
  flex: 1;
}

.name-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.name {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.stack {
  padding: 1px 6px;
  border-radius: 4px;
  background: #f2f3f5;
  color: #646a73;
  font-size: 11px;
  line-height: 18px;
}

.desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--muted);
}

.detail {
  margin: 8px 0 0 16px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #f8fafc;
  color: #334155;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
}

.wait {
  margin: 6px 0 0 16px;
  font-size: 12px;
  color: var(--muted);
}

.dot {
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
  background: #d1d5db;
  flex-shrink: 0;
}

.dot.running {
  background: var(--warning);
}

.dot.success {
  background: var(--success);
}

.dot.error {
  background: var(--danger);
}
</style>
