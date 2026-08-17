<template>
  <article class="card">
    <header>
      <div class="title">
        <strong>{{ title }}</strong>
        <span v-if="rows.length" class="meta">{{ rows.length }} 行</span>
      </div>
      <div v-if="rows.length" class="actions">
        <div class="seg">
          <button type="button" :class="{ on: view === 'table' }" @click="view = 'table'">表</button>
          <button
            v-for="item in chartTypes"
            :key="item.id"
            type="button"
            :disabled="!canChart"
            :class="{ on: view === 'chart' && chartType === item.id }"
            @click="pickChart(item.id)"
          >
            {{ item.label }}
          </button>
        </div>
        <button type="button" @click="copyTable">{{ copied ? "已复制" : "复制" }}</button>
        <button type="button" @click="downloadCsv">导出 CSV</button>
        <button v-if="sql && showSqlEntry" type="button" :class="{ on: openSql }" @click="openSql = !openSql">
          SQL
        </button>
      </div>
    </header>

    <p v-if="conclusion" class="conclusion">{{ conclusion }}</p>
    <p v-else-if="!rows.length" class="empty">还没有结果</p>

    <div v-if="rows.length && view === 'table'" class="table-wrap">
      <table>
        <thead>
          <tr>
            <th v-for="col in columns" :key="col">{{ col }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in rows" :key="idx">
            <td v-for="col in columns" :key="col" :class="{ num: numeric[col] }">
              {{ formatCell(row[col], numeric[col]) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else-if="rows.length && view === 'chart'" class="chart-box">
      <ResultChart :option="chartOption" />
    </div>

    <div v-if="openSql && sql && showSqlEntry" class="sql">
      <button type="button" class="copy-sql" @click="copySql">{{ sqlCopied ? "已复制" : "复制 SQL" }}</button>
      <pre>{{ sql }}</pre>
    </div>
  </article>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import ResultChart from "./ResultChart.vue";
import {
  buildChartOption,
  buildConclusion,
  detectNumeric,
  formatNumber,
  inferChartType,
} from "../utils/chart.js";

const props = defineProps({
  columns: { type: Array, default: () => [] },
  rows: { type: Array, default: () => [] },
  sql: { type: String, default: "" },
  showSqlEntry: { type: Boolean, default: true },
  preferredChart: { type: String, default: "auto" },
  title: { type: String, default: "查询结果" },
});

const view = ref("table");
const chartType = ref("bar");
const openSql = ref(false);
const copied = ref(false);
const sqlCopied = ref(false);

const numeric = computed(() => detectNumeric(props.columns, props.rows));
const inferred = computed(() => inferChartType(props.columns, props.rows, numeric.value));
const canChart = computed(() => inferred.value !== "table");
const conclusion = computed(() =>
  props.rows.length ? buildConclusion(props.columns, props.rows, numeric.value) : "",
);
const chartTypes = [
  { id: "bar", label: "柱状" },
  { id: "line", label: "折线" },
  { id: "pie", label: "饼图" },
];
const chartOption = computed(() =>
  buildChartOption(chartType.value, props.columns, props.rows, numeric.value),
);

watch(
  () => [props.rows, props.preferredChart],
  () => {
    if (!props.rows.length || !canChart.value) {
      view.value = "table";
      return;
    }
    const preferred = props.preferredChart === "auto" ? inferred.value : props.preferredChart;
    if (preferred === "table") {
      view.value = "table";
      return;
    }
    chartType.value = preferred;
    view.value = "chart";
  },
  { immediate: true },
);

function pickChart(id) {
  if (!canChart.value) return;
  chartType.value = id;
  view.value = "chart";
}

function formatCell(value, isNum) {
  if (value == null || value === "") return "—";
  return isNum ? formatNumber(value) : value;
}

function escapeCsv(value) {
  const text = value == null ? "" : String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function downloadCsv() {
  const lines = [
    props.columns.map(escapeCsv).join(","),
    ...props.rows.map((row) => props.columns.map((col) => escapeCsv(row[col])).join(",")),
  ];
  const blob = new Blob(["\uFEFF" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "query-result.csv";
  link.click();
  URL.revokeObjectURL(url);
}

async function copyTable() {
  const text = [
    props.columns.join("\t"),
    ...props.rows.map((row) => props.columns.map((col) => row[col] ?? "").join("\t")),
  ].join("\n");
  await navigator.clipboard.writeText(text);
  copied.value = true;
  setTimeout(() => {
    copied.value = false;
  }, 1500);
}

async function copySql() {
  await navigator.clipboard.writeText(props.sql);
  sqlCopied.value = true;
  setTimeout(() => {
    sqlCopied.value = false;
  }, 1500);
}
</script>

<style scoped>
.card {
  border: 1px solid #dee0e3;
  border-radius: 12px;
  background: #fff;
  padding: 14px 16px 12px;
}

header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.title {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.meta {
  color: var(--muted);
  font-size: 12px;
  font-weight: 400;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}

.seg {
  display: flex;
  gap: 2px;
  padding: 3px;
  border: 1px solid var(--border);
  border-radius: 8px;
}

.actions button {
  padding: 4px 10px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: #fff;
  color: var(--muted);
  font-size: 12px;
}

.seg button {
  border: 0;
}

.actions button.on {
  color: var(--accent);
  background: var(--accent-soft);
}

.actions button:disabled {
  opacity: 0.35;
}

.conclusion {
  margin: 12px 0 0;
  color: var(--text);
  font-size: 14px;
}

.empty {
  margin: 24px 0;
  text-align: center;
  color: var(--muted);
}

.table-wrap {
  overflow: auto;
  margin-top: 12px;
  max-height: 360px;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th,
td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
  text-align: left;
}

th {
  position: sticky;
  top: 0;
  background: #fafbfc;
  font-weight: 600;
}

td.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.chart-box {
  margin-top: 8px;
}

.sql {
  position: relative;
  margin-top: 12px;
}

.copy-sql {
  position: absolute;
  top: 8px;
  right: 8px;
  border: 0;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.12);
  color: #e2e8f0;
  font-size: 12px;
  padding: 4px 8px;
}

pre {
  margin: 0;
  padding: 12px 88px 12px 12px;
  border-radius: 8px;
  background: #1f2329;
  color: #e2e8f0;
  font-size: 12px;
  overflow-x: auto;
  white-space: pre-wrap;
}
</style>
