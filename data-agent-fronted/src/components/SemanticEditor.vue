<template>
  <div>
    <div class="sub">
      <button type="button" :class="{ on: pane === 'tables' }" @click="pane = 'tables'">
        表 {{ meta.tables.length }}
      </button>
      <button type="button" :class="{ on: pane === 'metrics' }" @click="pane = 'metrics'">
        指标 {{ meta.metrics.length }}
      </button>
    </div>

    <template v-if="pane === 'tables'">
      <div class="picker">
        <div class="picker-head">
          <div>
            <strong>从数据源选择表</strong>
            <p>{{ catalogHint }}</p>
          </div>
          <button type="button" class="ghost" :disabled="catalogLoading" @click="loadCatalog">
            {{ catalogLoading ? "读取中…" : "刷新表清单" }}
          </button>
        </div>
        <input v-model="filter" class="filter" placeholder="筛选表名 / 注释" />
        <div v-if="catalogError" class="err">{{ catalogError }}</div>
        <div v-else class="picks">
          <label v-for="item in filteredCatalog" :key="item.name" class="pick">
            <input
              type="checkbox"
              :checked="selectedNames.has(item.name)"
              @change="toggleTable(item, $event.target.checked)"
            />
            <span class="pick-name">{{ item.name }}</span>
            <span class="pick-hint">
              {{ item.comment || roleLabel(guessTableRole(item.name)) }} · {{ item.columns.length }} 列
            </span>
          </label>
          <div v-if="catalog.length && !filteredCatalog.length" class="empty">没有匹配的表</div>
          <div v-else-if="!catalog.length && !catalogLoading" class="empty">还没有读到数据源表</div>
        </div>
        <p v-if="prunedTables.length" class="warn">
          已去掉不在数据源里的表：{{ prunedTables.join("、") }}
        </p>
      </div>

      <article v-for="(table, ti) in meta.tables" :key="table.name || ti" class="panel">
        <header>
          <button type="button" class="fold-btn" @click="toggleOpen('t', tableKey(table, ti))">
            <span>{{ isOpen('t', tableKey(table, ti)) ? "▾" : "▸" }}</span>
            <strong>{{ table.name || "未命名表" }}</strong>
            <em>{{ roleLabel(table.role) }}</em>
            <span class="count">{{ (table.columns || []).length }} 字段</span>
          </button>
          <button type="button" class="ghost" @click="removeTable(ti)">移除</button>
        </header>
        <div v-show="isOpen('t', tableKey(table, ti))">
          <div class="grid">
            <label>角色
              <select v-model="table.role">
                <option value="dim">维度表</option>
                <option value="fact">事实表</option>
              </select>
            </label>
            <label class="wide">描述<input v-model="table.description" /></label>
          </div>
          <table class="cols">
            <thead>
              <tr>
                <th>字段</th>
                <th>角色</th>
                <th>描述</th>
                <th>别名</th>
                <th>同步取值</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(col, ci) in table.columns" :key="col.name || ci">
                <td class="name">{{ col.name }}</td>
                <td>
                  <select v-model="col.role">
                    <option value="primary_key">主键</option>
                    <option value="foreign_key">外键</option>
                    <option value="dimension">维度</option>
                    <option value="measure">度量</option>
                  </select>
                </td>
                <td><input v-model="col.description" /></td>
                <td><input :value="joinList(col.alias)" @change="col.alias = splitList($event.target.value)" /></td>
                <td class="center"><input v-model="col.sync" type="checkbox" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </article>
    </template>

    <template v-else>
      <div class="picker">
        <div class="picker-head">
          <div>
            <strong>从已选表里选度量</strong>
            <p>{{ metricHint }}</p>
          </div>
        </div>
        <input v-model="metricFilter" class="filter" placeholder="筛选字段 / 表名" />
        <div class="picks">
          <label v-for="item in filteredMeasures" :key="item.key" class="pick">
            <input
              type="checkbox"
              :checked="selectedMeasureKeys.has(item.key)"
              @change="toggleMetric(item, $event.target.checked)"
            />
            <span class="pick-name">{{ item.key }}</span>
            <span class="pick-hint">{{ item.description || item.alias[0] || "度量" }}</span>
          </label>
          <div v-if="!measureCandidates.length" class="empty">
            {{ meta.tables.length ? "已选表里没有度量字段，先在表里把字段角色改成「度量」" : "先在「表」里勾选数据源表" }}
          </div>
          <div v-else-if="!filteredMeasures.length" class="empty">没有匹配的字段</div>
        </div>
        <p v-if="prunedMetrics.length" class="warn">
          已去掉对不上数仓字段的指标：{{ prunedMetrics.join("、") }}
        </p>
      </div>

      <article v-for="(metric, mi) in meta.metrics" :key="metric.name || mi" class="panel">
        <header>
          <button type="button" class="fold-btn" @click="toggleOpen('m', metricKey(metric, mi))">
            <span>{{ isOpen('m', metricKey(metric, mi)) ? "▾" : "▸" }}</span>
            <strong>{{ metric.name || "未命名指标" }}</strong>
            <span class="count">{{ (metric.relevant_columns || []).join("、") || "未关联字段" }}</span>
          </button>
          <button type="button" class="ghost" @click="removeAt(meta.metrics, mi)">移除</button>
        </header>
        <div v-show="isOpen('m', metricKey(metric, mi))">
          <div class="grid">
            <label>名称<input v-model="metric.name" /></label>
            <label>别名<input :value="joinList(metric.alias)" @change="metric.alias = splitList($event.target.value)" /></label>
            <label class="wide">描述<input v-model="metric.description" /></label>
            <div class="wide refs">
              <span>关联字段（仅已选表的度量）</span>
              <label v-for="item in measureCandidates" :key="item.key" class="pick">
                <input
                  type="checkbox"
                  :checked="(metric.relevant_columns || []).includes(item.key)"
                  @change="toggleMetricColumn(metric, item.key, $event.target.checked)"
                />
                <span class="pick-name">{{ item.key }}</span>
              </label>
              <div v-if="!measureCandidates.length" class="empty">没有可选度量字段</div>
            </div>
          </div>
        </div>
      </article>
    </template>

    <div class="bar">
      <button type="button" class="primary" :disabled="saving" @click="save">保存语义</button>
      <span v-if="message" class="msg">{{ message }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { getDatasourceTables, saveMetaConfig } from "../api/admin.js";

const props = defineProps({
  modelValue: { type: Object, required: true },
});
const emit = defineEmits(["update:modelValue"]);

const pane = ref("tables");
const saving = ref(false);
const message = ref("");
const catalogLoading = ref(false);
const catalogError = ref("");
const catalogDb = ref("");
const catalog = ref([]);
const filter = ref("");
const metricFilter = ref("");
const prunedTables = ref([]);
const prunedMetrics = ref([]);
const openMap = reactive({});
const meta = computed(() => props.modelValue);

const selectedNames = computed(() => new Set((meta.value.tables || []).map((t) => t.name).filter(Boolean)));

const filteredCatalog = computed(() => {
  const q = filter.value.trim().toLowerCase();
  if (!q) return catalog.value;
  return catalog.value.filter(
    (item) => item.name.toLowerCase().includes(q) || String(item.comment || "").toLowerCase().includes(q),
  );
});

const catalogHint = computed(() => {
  if (catalogError.value) return "读不到数据源时，仍可编辑已有语义";
  if (catalogDb.value) return `${catalogDb.value} · ${catalog.value.length} 张表，勾选后在下方补描述和别名`;
  return "勾选要进知识库的表，字段会从库里带过来";
});

const measureCandidates = computed(() => {
  const list = [];
  for (const table of meta.value.tables || []) {
    if (!table.name) continue;
    for (const col of table.columns || []) {
      if (col.role === "measure" && col.name) {
        list.push({
          key: `${table.name}.${col.name}`,
          table: table.name,
          column: col.name,
          description: col.description || "",
          alias: col.alias || [],
        });
      }
    }
  }
  return list;
});

const filteredMeasures = computed(() => {
  const q = metricFilter.value.trim().toLowerCase();
  if (!q) return measureCandidates.value;
  return measureCandidates.value.filter(
    (item) =>
      item.key.toLowerCase().includes(q) ||
      String(item.description || "").toLowerCase().includes(q) ||
      item.alias.some((a) => String(a).toLowerCase().includes(q)),
  );
});

const selectedMeasureKeys = computed(() => {
  const keys = new Set();
  for (const metric of meta.value.metrics || []) {
    for (const col of metric.relevant_columns || []) keys.add(col);
  }
  return keys;
});

const metricHint = computed(() => {
  if (!meta.value.tables.length) return "指标来自已选表的度量字段，先去勾选表";
  if (!measureCandidates.value.length) return "把字段角色改成「度量」后，会出现在下面供勾选";
  return `已选表里有 ${measureCandidates.value.length} 个度量，勾选后可改名称和别名`;
});

onMounted(loadCatalog);

function tableKey(table, index) {
  /** 折叠状态用的表 id。 */
  return table.name || `new-${index}`;
}

function metricKey(metric, index) {
  /** 折叠状态用的指标 id。 */
  return metric.name || `new-${index}`;
}

function isOpen(kind, id) {
  /** 卡片是否展开；单表时默认展开。 */
  const key = `${kind}:${id}`;
  if (openMap[key] === undefined) return kind === "t" && meta.value.tables.length === 1;
  return openMap[key] === true;
}

function toggleOpen(kind, id) {
  /** 切换卡片折叠。 */
  const key = `${kind}:${id}`;
  openMap[key] = !isOpen(kind, id);
}

function roleLabel(role) {
  /** 表角色中文。 */
  return role === "fact" ? "事实表" : "维度表";
}

function guessTableRole(name) {
  /** fact_ 前缀猜事实表，否则维度表。 */
  return String(name || "").toLowerCase().startsWith("fact_") ? "fact" : "dim";
}

function guessColumnRole(col, tableName) {
  /** 按主键/外键/数值类型猜字段角色。 */
  const key = String(col.col_key || "").toUpperCase();
  const name = String(col.name || "").toLowerCase();
  const type = String(col.data_type || "").toLowerCase();
  if (key === "PRI") return "primary_key";
  if (key === "MUL" || (/_id$/.test(name) && name !== "id")) return "foreign_key";
  if (["int", "bigint", "tinyint", "smallint", "mediumint", "decimal", "float", "double", "numeric"].includes(type)) {
    return guessTableRole(tableName) === "fact" ? "measure" : "dimension";
  }
  return "dimension";
}

function toSemanticTable(item) {
  /** 数仓表转语义稿，带默认角色。 */
  return {
    name: item.name,
    role: guessTableRole(item.name),
    description: item.comment || "",
    columns: (item.columns || []).map((col) => ({
      name: col.name,
      role: guessColumnRole(col, item.name),
      description: col.comment || "",
      alias: [],
      sync: false,
    })),
  };
}

function mergeColumns(existing, incoming) {
  /** 保留已有描述/别名，补上数据源新增列。 */
  const byName = new Map((existing.columns || []).map((col) => [col.name, col]));
  const merged = (incoming.columns || []).map((col) => {
    const prev = byName.get(col.name);
    return prev || {
      name: col.name,
      role: guessColumnRole(col, incoming.name || existing.name),
      description: col.comment || "",
      alias: [],
      sync: false,
    };
  });
  for (const col of existing.columns || []) {
    if (col.name && !merged.some((item) => item.name === col.name)) merged.push(col);
  }
  existing.columns = merged;
}

async function loadCatalog() {
  /** 拉数据源表清单并裁掉不存在的语义项。 */
  catalogLoading.value = true;
  catalogError.value = "";
  try {
    const data = await getDatasourceTables();
    catalog.value = data.tables || [];
    catalogDb.value = data.database || "";
    pruneToCatalog();
  } catch (e) {
    catalog.value = [];
    catalogError.value = e.message || "读取数据源表失败";
  } finally {
    catalogLoading.value = false;
  }
}

function pruneToCatalog() {
  /** 原地 splice 掉不在数仓里的表/字段/指标。 */
  const byName = new Map(catalog.value.map((item) => [item.name, item]));
  if (!byName.size) return;
  const droppedTables = [];
  const droppedMetrics = [];
  for (let i = meta.value.tables.length - 1; i >= 0; i -= 1) {
    const table = meta.value.tables[i];
    const src = byName.get(table.name);
    if (!src) {
      droppedTables.push(table.name || "未命名表");
      meta.value.tables.splice(i, 1);
      continue;
    }
    const allowed = new Set((src.columns || []).map((col) => col.name));
    table.columns = (table.columns || []).filter((col) => allowed.has(col.name));
  }
  const known = new Set();
  for (const item of catalog.value) {
    for (const col of item.columns || []) known.add(`${item.name}.${col.name}`);
  }
  for (let i = meta.value.metrics.length - 1; i >= 0; i -= 1) {
    const metric = meta.value.metrics[i];
    metric.relevant_columns = (metric.relevant_columns || []).filter((col) => known.has(col));
    if (!metric.relevant_columns.length) {
      droppedMetrics.push(metric.name || "未命名指标");
      meta.value.metrics.splice(i, 1);
    }
  }
  prunedTables.value = droppedTables;
  prunedMetrics.value = droppedMetrics;
}

function toggleTable(item, checked) {
  /** 勾选加入语义稿，取消则连同相关指标一起删。 */
  if (checked) {
    const found = meta.value.tables.find((t) => t.name === item.name);
    if (found) {
      mergeColumns(found, item);
    } else {
      meta.value.tables.push(toSemanticTable(item));
    }
    openMap[`t:${item.name}`] = true;
    return;
  }
  const idx = meta.value.tables.findIndex((t) => t.name === item.name);
  if (idx >= 0) removeTable(idx);
}

function removeTable(index) {
  /** 移除表并清掉以该表名为前缀的指标关联。 */
  const table = meta.value.tables[index];
  const prefix = table?.name ? `${table.name}.` : "";
  meta.value.tables.splice(index, 1);
  if (!prefix) return;
  for (let i = meta.value.metrics.length - 1; i >= 0; i -= 1) {
    const metric = meta.value.metrics[i];
    metric.relevant_columns = (metric.relevant_columns || []).filter((col) => !col.startsWith(prefix));
    if (!metric.relevant_columns.length) meta.value.metrics.splice(i, 1);
  }
}

function joinList(value) {
  /** 别名数组转输入框文本。 */
  return (value || []).join(", ");
}

function splitList(value) {
  /** 中英文逗号拆别名。 */
  return String(value || "")
    .split(/[,，]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function removeAt(list, index) {
  /** 从数组删一项。 */
  list.splice(index, 1);
}

function guessMetricName(item) {
  /** 用别名或字段名生成不重复的指标名。 */
  const used = new Set((meta.value.metrics || []).map((m) => m.name));
  const raw = (item.alias[0] || item.column || "指标").trim();
  if (!used.has(raw)) return raw;
  const full = item.key;
  if (!used.has(full)) return full;
  let i = 2;
  while (used.has(`${raw}${i}`)) i += 1;
  return `${raw}${i}`;
}

function toggleMetric(item, checked) {
  /** 勾选度量生成指标，取消则拆掉关联。 */
  if (checked) {
    const exists = meta.value.metrics.some((m) => (m.relevant_columns || []).includes(item.key));
    if (!exists) {
      const metric = {
        name: guessMetricName(item),
        description: item.description || "",
        relevant_columns: [item.key],
        alias: [...item.alias],
      };
      meta.value.metrics.push(metric);
      openMap[`m:${metric.name}`] = true;
    }
    return;
  }
  for (let i = meta.value.metrics.length - 1; i >= 0; i -= 1) {
    const metric = meta.value.metrics[i];
    const cols = (metric.relevant_columns || []).filter((col) => col !== item.key);
    if (!cols.length) meta.value.metrics.splice(i, 1);
    else metric.relevant_columns = cols;
  }
}

function toggleMetricColumn(metric, key, checked) {
  /** 改单个指标的关联字段。 */
  const cols = metric.relevant_columns || [];
  if (checked && !cols.includes(key)) cols.push(key);
  if (!checked) metric.relevant_columns = cols.filter((col) => col !== key);
}

async function save() {
  /** 写入 semantic_config，不触发构建。 */
  saving.value = true;
  message.value = "";
  try {
    const result = await saveMetaConfig(meta.value);
    emit("update:modelValue", result.config);
    message.value = "语义已写入元数据库，请向下做第 2 步构建";
  } catch (e) {
    message.value = e.message || "保存失败";
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
.sub {
  display: flex;
  gap: 8px;
  margin: 12px 0;
}

.sub button {
  border: 1px solid #d9dcdf;
  border-radius: 8px;
  background: #fff;
  padding: 6px 12px;
}

.sub button.on {
  background: var(--accent-soft);
  color: var(--accent);
  border-color: transparent;
  font-weight: 600;
}

.picker {
  margin-bottom: 12px;
  padding: 12px;
  border: 1px dashed #d9dcdf;
  border-radius: 12px;
  background: #f8f9fa;
}

.picker-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.picker-head p,
.warn,
.empty,
.err {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 12px;
}

.err {
  color: var(--danger);
}

.warn {
  color: #9a3412;
}

.filter {
  width: 100%;
  margin-bottom: 8px;
}

.picks {
  max-height: 220px;
  overflow: auto;
  display: grid;
  gap: 2px;
}

.pick {
  display: grid;
  grid-template-columns: 18px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--text);
}

.pick:hover {
  background: #fff;
}

.pick-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pick-hint {
  color: var(--muted);
  font-size: 12px;
}

.panel {
  border: 1px solid #dee0e3;
  border-radius: 12px;
  padding: 12px 16px 16px;
  background: #fff;
  margin-bottom: 12px;
}

.panel header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.fold-btn {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  border: 0;
  background: transparent;
  padding: 4px 0;
  text-align: left;
  color: inherit;
}

.fold-btn em,
.count {
  color: var(--muted);
  font-style: normal;
  font-size: 12px;
  font-weight: 400;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

.wide {
  grid-column: 1 / -1;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--muted);
}

input,
select {
  padding: 8px 10px;
  border: 1px solid #d9dcdf;
  border-radius: 8px;
  background: #f8f9fa;
  color: var(--text);
}

input:focus,
select:focus {
  outline: none;
  border-color: var(--accent);
  background: #fff;
}

.cols {
  width: 100%;
  margin: 12px 0 8px;
  border-collapse: collapse;
  font-size: 12px;
}

.cols th,
.cols td {
  padding: 4px;
  text-align: left;
  vertical-align: middle;
}

.cols th {
  color: var(--muted);
  font-weight: 500;
}

.cols .name {
  white-space: nowrap;
  font-family: ui-monospace, Consolas, monospace;
  font-size: 12px;
  padding-right: 10px;
}

.refs {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--muted);
}

.cols input,
.cols select {
  width: 100%;
  min-width: 80px;
}

.center {
  text-align: center;
}

.ghost {
  border: 1px solid #d9dcdf;
  border-radius: 8px;
  background: #fff;
  color: var(--text);
  padding: 6px 10px;
}

.bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 8px;
}

.primary {
  border: 0;
  border-radius: 8px;
  background: var(--accent);
  color: #fff;
  padding: 8px 16px;
}

.msg {
  color: var(--muted);
  font-size: 13px;
}
</style>
