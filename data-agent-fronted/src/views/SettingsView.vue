<template>
  <div class="settings">
    <aside>
      <button type="button" class="brand" @click="$emit('nav', 'ask')">
        <span class="mark">析</span>
        <span>问</span>
      </button>
      <button type="button" class="back" @click="$emit('nav', 'ask')">← 返回问数</button>

      <button type="button" class="group-btn" :class="{ on: engineOpen }" @click="toggleEngine">
        <span>模型与检索</span>
        <span class="caret">{{ engineOpen ? "▾" : "▸" }}</span>
      </button>
      <div v-if="engineOpen" class="subs">
        <button
          v-for="item in engineTabs"
          :key="item.id"
          type="button"
          class="sub-btn"
          :class="{ on: tab === item.id }"
          @click="tab = item.id"
        >
          {{ item.label }}
        </button>
      </div>

      <button
        v-for="item in mainTabs"
        :key="item.id"
        type="button"
        class="nav-btn"
        :class="{ on: tab === item.id }"
        @click="openMain(item.id)"
      >
        {{ item.label }}
      </button>
    </aside>

    <section v-if="loading" class="body">加载中…</section>

    <section v-else-if="form" class="body" :class="{ 'body-fill': tab === 'prompts' }">
      <template v-if="currentPage">
        <header class="page-head">
          <h2>{{ currentPage.title }}</h2>
          <p>{{ currentPage.desc }}</p>
        </header>
        <article class="panel">
          <div v-if="tab === 'llm'" class="grid">
            <label>模型名<input v-model="form.llm.model_name" /></label>
            <label>接口地址<input v-model="form.llm.base_url" /></label>
            <label>API Key<input v-model="form.llm.api_key" type="password" /></label>
            <label>温度<input v-model.number="form.llm.temperature" type="number" step="0.1" /></label>
            <label>超时（秒）<input v-model.number="form.llm.timeout" type="number" /></label>
          </div>
          <div v-else-if="tab === 'embedding'" class="grid">
            <label>主机<input v-model="form.embedding.host" /></label>
            <label>端口<input v-model.number="form.embedding.port" type="number" /></label>
            <label>模型<input v-model="form.embedding.model" /></label>
            <label>路径<input v-model="form.embedding.path" /></label>
            <label>批大小<input v-model.number="form.embedding.batch_size" type="number" /></label>
            <label>超时（秒）<input v-model.number="form.embedding.timeout" type="number" /></label>
          </div>
          <div v-else-if="tab === 'qdrant'" class="grid">
            <label>主机<input v-model="form.qdrant.host" /></label>
            <label>端口<input v-model.number="form.qdrant.port" type="number" /></label>
            <label>向量维度<input v-model.number="form.qdrant.embedding_size" type="number" /></label>
            <label>字段集合<input v-model="form.qdrant.collections.column" /></label>
            <label>指标集合<input v-model="form.qdrant.collections.metric" /></label>
            <label>相似度阈值<input v-model.number="form.qdrant.search.score_threshold" type="number" step="0.05" /></label>
            <label>召回条数<input v-model.number="form.qdrant.search.limit" type="number" /></label>
          </div>
          <div v-else-if="tab === 'es'" class="grid">
            <label>主机<input v-model="form.es.host" /></label>
            <label>端口<input v-model.number="form.es.port" type="number" /></label>
            <label>索引名<input v-model="form.es.index_name" /></label>
          </div>
          <div v-else-if="tab === 'meta-db'" class="grid">
            <label>主机<input v-model="form.db_meta.host" /></label>
            <label>端口<input v-model.number="form.db_meta.port" type="number" /></label>
            <label>库名<input v-model="form.db_meta.database" /></label>
            <label>用户<input v-model="form.db_meta.user" /></label>
            <label>密码<input v-model="form.db_meta.password" type="password" /></label>
          </div>
          <div v-else-if="tab === 'ask-ui'" class="grid">
            <label>默认图
              <select v-model="form.chart.default">
                <option value="auto">自动</option>
                <option value="table">仅表格</option>
                <option value="bar">柱状图</option>
                <option value="line">折线图</option>
                <option value="pie">饼图</option>
              </select>
            </label>
            <label class="check"><input v-model="form.chart.thousand_separator" type="checkbox" />千分位</label>
            <label class="check"><input v-model="form.ui.show_sql" type="checkbox" />显示 SQL</label>
            <label class="wide">推荐问（一行一条）
              <textarea v-model="quickAsksText" rows="4" />
            </label>
          </div>
          <div v-else-if="tab === 'datasource'" class="grid">
            <label>主机<input v-model="form.db_dw.host" /></label>
            <label>端口<input v-model.number="form.db_dw.port" type="number" /></label>
            <label>库名<input v-model="form.db_dw.database" /></label>
            <label>用户<input v-model="form.db_dw.user" /></label>
            <label>密码<input v-model="form.db_dw.password" type="password" /></label>
          </div>
        </article>
        <div class="bar">
          <button type="button" class="primary" :disabled="saving" @click="saveAll">保存</button>
          <a :href="exportConfigUrl()" class="ghost">导出 YAML</a>
          <span v-if="message" class="msg">{{ message }}</span>
        </div>
      </template>

      <template v-else-if="tab === 'knowledge'">
        <header class="page-head">
          <h2>语义与检索</h2>
          <p>{{ knowledgeLayer === "semantic" ? "勾选数仓里的表和指标，写描述和别名。只保存语义稿，问数仍用上次构建的快照。" : "按固定 6 步把语义稿写入元数据、Qdrant 和 ES。不改数据源里的业务表。" }}</p>
        </header>
        <nav class="layer-tabs">
          <button type="button" :class="{ on: knowledgeLayer === 'semantic' }" @click="knowledgeLayer = 'semantic'">语义层</button>
          <button type="button" :class="{ on: knowledgeLayer === 'search' }" @click="knowledgeLayer = 'search'">检索层</button>
        </nav>
        <ol class="flow">
          <li>定义语义</li>
          <li>写入元数据</li>
          <li>建向量 / 全文索引</li>
          <li>问数可召回</li>
        </ol>
        <div v-if="warnings.length" class="warn">
          <div v-for="item in warnings" :key="item">{{ item }}</div>
        </div>

        <SemanticEditor v-if="knowledgeLayer === 'semantic' && meta" v-model="meta" />

        <template v-else-if="knowledgeLayer === 'search'">
          <div class="build-toolbar">
            <label class="inline">
              失败策略
              <select v-model="form.knowledge_build.on_error">
                <option value="abort">失败即停</option>
                <option value="continue">继续下一步</option>
              </select>
            </label>
            <button type="button" class="primary" :disabled="building" @click="saveThenBuild">
              {{ building ? "构建中…" : "保存参数并构建" }}
            </button>
            <span v-if="message" class="msg">{{ message }}</span>
          </div>
          <ol class="steps">
            <li
              v-for="(step, idx) in stepMeta"
              :key="step.id"
              :class="{
                open: buildStepOpen[step.id],
                off: !form.knowledge_build.steps[step.id].enabled,
                [buildStatus[step.id] || '']: true,
              }"
            >
              <div class="step-row">
                <button type="button" class="step-main" @click="toggleBuildStep(step.id)">
                  <span class="dot">{{ idx + 1 }}</span>
                  <span class="ttl">{{ step.title }}</span>
                  <span v-if="buildStatus[step.id]" class="st" :class="buildStatus[step.id]">
                    {{ statusText(buildStatus[step.id]) }}
                  </span>
                </button>
                <label v-if="step.param" class="param" @click.stop>
                  {{ step.paramLabel }}
                  <input v-model.number="form.knowledge_build.steps[step.id][step.param]" type="number" />
                </label>
                <label class="switch" @click.stop>
                  <input v-model="form.knowledge_build.steps[step.id].enabled" type="checkbox" />
                  启用
                </label>
              </div>
              <div v-show="buildStepOpen[step.id]" class="step-more">
                <p>{{ step.desc }}</p>
                <div v-if="buildDetail[step.id]" class="detail">{{ buildDetail[step.id] }}</div>
              </div>
            </li>
          </ol>
        </template>
      </template>

      <template v-else>
        <header class="page-head">
          <h2>提示词</h2>
          <p>按问数链路分组。保存后下一问生效，恢复默认从出厂文件拷回。</p>
        </header>
        <div class="prompt-work">
          <nav class="prompt-nav">
            <section v-for="group in promptGroups" :key="group.id">
              <h4>{{ group.title }}</h4>
              <button
                v-for="item in group.items"
                :key="item.id"
                type="button"
                :class="{ on: currentPrompt?.id === item.id }"
                @click="currentPrompt = item"
              >
                <span>{{ item.title }}</span>
              </button>
            </section>
          </nav>
          <div v-if="currentPrompt" class="prompt-main">
            <header class="prompt-meta">
              <div>
                <h3>{{ currentPrompt.title }}</h3>
                <p>{{ currentPrompt.description }}</p>
              </div>
              <div class="bar">
                <button type="button" class="primary" :disabled="saving" @click="saveCurrentPrompt">保存</button>
                <button type="button" class="ghost" @click="resetCurrentPrompt">恢复默认</button>
              </div>
            </header>
            <div class="prompt-vars">
              <span>变量</span>
              <button
                v-for="name in currentPrompt.variables || []"
                :key="name"
                type="button"
                class="chip"
                :title="`插入 {${name}}`"
                @click="insertVariable(name)"
              >
                {{ name }}
              </button>
            </div>
            <textarea
              ref="promptEditor"
              v-model="currentPrompt.content"
              class="prompt-code"
              spellcheck="false"
            />
            <p v-if="message" class="prompt-msg">{{ message }}</p>
          </div>
        </div>
      </template>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref } from "vue";
import {
  buildKnowledge,
  exportConfigUrl,
  getConfig,
  getMetaConfig,
  getPrompts,
  resetPrompt,
  saveConfig,
  savePrompt,
} from "../api/admin.js";
import SemanticEditor from "../components/SemanticEditor.vue";

defineEmits(["nav"]);

const engineTabs = [
  {
    id: "llm",
    label: "大模型",
    title: "大模型",
    desc: "负责把问题扩成关键词、筛表筛指标、生成和校正 SQL。改完下一问生效，不用重建知识库。",
  },
  {
    id: "embedding",
    label: "向量模型",
    title: "向量模型",
    desc: "把字段名、指标名、别名打成向量。知识构建和问数召回都走它。换模型或维度后必须重建知识库。",
  },
  {
    id: "qdrant",
    label: "向量库",
    title: "向量库 Qdrant",
    desc: "存字段和指标的向量，问数时按相似度召回相关列和指标。换地址或集合名后请重建知识库。",
  },
  {
    id: "es",
    label: "全文检索",
    title: "全文检索 Elasticsearch",
    desc: "存「黄金」「华东」这类字段取值，用来把口语对上真实枚举。只对 sync 打开的字段建索引。",
  },
  {
    id: "meta-db",
    label: "元数据库",
    title: "元数据库",
    desc: "存表结构、字段、指标和会话记录，不是业务数据。知识构建写入这里，问数时再读出来拼上下文。",
  },
  {
    id: "ask-ui",
    label: "问数页",
    title: "问数页",
    desc: "只影响问数页展示：默认图、千分位、是否露出 SQL、空状态推荐问。",
  },
];

const mainTabs = [
  { id: "datasource", label: "数据源" },
  { id: "knowledge", label: "语义与检索" },
  { id: "prompts", label: "提示词" },
];

const pages = {
  ...Object.fromEntries(engineTabs.map((item) => [item.id, item])),
  datasource: {
    title: "数据源",
    desc: "业务数仓，真正跑 SQL 的地方。问数结果都从这里查。改连接后立即生效，不必重建知识库。",
  },
};

const stepMeta = [
  { id: "load_config", title: "读取语义配置", desc: "从元数据库读取刚保存的表、字段和指标。", param: "", paramLabel: "" },
  { id: "save_tables", title: "写入表和字段", desc: "从数据源取样例，写入元数据库的表/字段。", param: "example_limit", paramLabel: "样例条数" },
  { id: "index_columns", title: "字段向量化", desc: "把字段名、描述、别名写入 Qdrant，供问数召回列。", param: "batch_size", paramLabel: "批大小" },
  { id: "index_values", title: "取值全文索引", desc: "把打开「同步取值」的字段枚举写入 ES，用来对齐「黄金」这类口语。", param: "value_limit", paramLabel: "取值上限" },
  { id: "save_metrics", title: "写入指标", desc: "把指标定义和关联字段写入元数据库。", param: "", paramLabel: "" },
  { id: "index_metrics", title: "指标向量化", desc: "把指标名、描述、别名写入 Qdrant，供问数召回指标。", param: "batch_size", paramLabel: "批大小" },
];

const tab = ref("llm");
const engineOpen = ref(true);
const knowledgeLayer = ref("semantic");
const buildStepOpen = ref(Object.fromEntries(stepMeta.map((step) => [step.id, false])));
const loading = ref(true);
const saving = ref(false);
const building = ref(false);
const message = ref("");
const warnings = ref([]);
const form = ref(null);
const meta = ref(null);
const prompts = ref([]);
const currentPrompt = ref(null);
const promptEditor = ref(null);
const buildStatus = ref({});
const buildDetail = ref({});

const promptGroupMeta = [
  { id: "recall", title: "召回扩词", ids: ["extend_keywords_for_column_recall", "extend_keywords_for_metric_recall", "extend_keywords_for_value_recall"] },
  { id: "filter", title: "过滤", ids: ["filter_table_info", "filter_metric_info"] },
  { id: "sql", title: "生成与校正", ids: ["generate_sql", "correct_sql"] },
];

const currentPage = computed(() => pages[tab.value] || null);

const promptGroups = computed(() => {
  const byId = new Map(prompts.value.map((item) => [item.id, item]));
  const grouped = promptGroupMeta
    .map((group) => ({
      id: group.id,
      title: group.title,
      items: group.ids.map((id) => byId.get(id)).filter(Boolean),
    }))
    .filter((group) => group.items.length);
  const used = new Set(grouped.flatMap((group) => group.items.map((item) => item.id)));
  const rest = prompts.value.filter((item) => !used.has(item.id));
  if (rest.length) grouped.push({ id: "other", title: "其他", items: rest });
  return grouped;
});

const quickAsksText = computed({
  get() {
    return (form.value?.ui?.quick_asks || []).join("\n");
  },
  set(value) {
    form.value.ui.quick_asks = value.split("\n").map((s) => s.trim()).filter(Boolean);
  },
});

function toggleEngine() {
  /** 折叠模型与检索分组。 */
  engineOpen.value = !engineOpen.value;
  if (engineOpen.value && !pages[tab.value]) tab.value = "llm";
}

function openMain(id) {
  /** 切到数据源/知识库/提示词，并收起引擎分组。 */
  tab.value = id;
  if (id !== "datasource") engineOpen.value = false;
}

function toggleBuildStep(id) {
  /** 展开或收起某构建步骤说明。 */
  buildStepOpen.value = { ...buildStepOpen.value, [id]: !buildStepOpen.value[id] };
}

function statusText(status) {
  /** 构建步骤状态文案。 */
  return { running: "进行中", success: "完成", error: "失败", skipped: "已跳过" }[status] || status;
}

onMounted(async () => {
  try {
    const [cfg, promptData, metaData] = await Promise.all([
      getConfig(),
      getPrompts(),
      getMetaConfig(),
    ]);
    form.value = cfg.config;
    warnings.value = cfg.warnings || [];
    prompts.value = promptData.prompts || [];
    meta.value = metaData.config || { tables: [], metrics: [] };
    const first = promptGroupMeta
      .flatMap((group) => group.ids)
      .map((id) => prompts.value.find((item) => item.id === id))
      .find(Boolean);
    currentPrompt.value = first || prompts.value[0] || null;
  } catch (e) {
    message.value = e.message || "加载失败";
  } finally {
    loading.value = false;
  }
});

async function saveAll() {
  /** 保存运行时配置并热加载。 */
  saving.value = true;
  message.value = "";
  try {
    const result = await saveConfig(form.value);
    form.value = result.config;
    warnings.value = result.warnings || [];
    message.value = result.rebuild_required
      ? "已保存并热加载，请重建知识库"
      : result.reloaded?.length
        ? `已保存并热加载：${result.reloaded.join("、")}`
        : "已保存，已立即生效";
    return true;
  } catch (e) {
    message.value = e.message || "保存失败";
    return false;
  } finally {
    saving.value = false;
  }
}

function insertVariable(name) {
  /** 在光标处插入 {变量}。 */
  const prompt = currentPrompt.value;
  if (!prompt) return;
  const token = `{${name}}`;
  const el = promptEditor.value;
  const text = prompt.content || "";
  if (!el) {
    prompt.content = text + token;
    return;
  }
  const start = el.selectionStart ?? text.length;
  const end = el.selectionEnd ?? text.length;
  prompt.content = text.slice(0, start) + token + text.slice(end);
  nextTick(() => {
    el.focus();
    const pos = start + token.length;
    el.setSelectionRange(pos, pos);
  });
}

async function saveCurrentPrompt() {
  /** 覆盖保存当前提示词。 */
  if (!currentPrompt.value) return;
  saving.value = true;
  message.value = "";
  try {
    const saved = await savePrompt(currentPrompt.value.id, currentPrompt.value.content);
    currentPrompt.value = saved;
    const idx = prompts.value.findIndex((p) => p.id === saved.id);
    if (idx >= 0) prompts.value[idx] = saved;
    message.value = "提示词已保存，下一问生效";
  } catch (e) {
    message.value = e.message || "保存失败";
  } finally {
    saving.value = false;
  }
}

async function resetCurrentPrompt() {
  /** 从出厂文件恢复当前提示词。 */
  if (!currentPrompt.value) return;
  const saved = await resetPrompt(currentPrompt.value.id);
  currentPrompt.value = saved;
  const idx = prompts.value.findIndex((p) => p.id === saved.id);
  if (idx >= 0) prompts.value[idx] = saved;
  message.value = "已恢复默认";
}

async function saveThenBuild() {
  /** 先保存构建参数，再跑 6 步 SSE。 */
  knowledgeLayer.value = "search";
  const ok = await saveAll();
  if (ok) await runBuild();
}

async function runBuild() {
  /** 消费构建 SSE，更新步骤状态。 */
  building.value = true;
  message.value = "";
  buildStatus.value = {};
  buildDetail.value = {};
  try {
    await buildKnowledge((event) => {
      if (event.type === "error") {
        message.value = event.message || "构建失败";
        return;
      }
      if (event.type === "done") {
        message.value = "知识库构建完成";
        return;
      }
      if (event.step) {
        buildStatus.value = { ...buildStatus.value, [event.step]: event.status };
        if (event.status === "running" || event.status === "error") {
          buildStepOpen.value = { ...buildStepOpen.value, [event.step]: true };
        }
        if (event.detail) {
          buildDetail.value = { ...buildDetail.value, [event.step]: event.detail };
        }
      }
    });
  } catch (e) {
    message.value = e.message || "构建失败";
  } finally {
    building.value = false;
  }
}
</script>

<style scoped>
.settings {
  flex: 1;
  min-height: 0;
  display: flex;
  background: #fff;
}

aside {
  width: 220px;
  min-width: 220px;
  padding: 12px 10px 10px;
  background: #f5f6f7;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  margin: 0 0 8px;
  padding: 0 4px;
  border: 0;
  background: transparent;
  font-weight: 650;
  color: var(--text);
}

.back {
  margin-bottom: 12px;
  padding: 6px 12px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  text-align: left;
  font-size: 13px;
}

.back:hover {
  background: rgba(31, 35, 41, 0.06);
  color: var(--text);
}

.mark {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--accent);
  color: #fff;
  font-size: 14px;
  line-height: 28px;
  text-align: center;
}

.group-btn,
.nav-btn,
.sub-btn {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  margin-bottom: 4px;
  padding: 9px 12px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  text-align: left;
  color: var(--text);
}

.sub-btn {
  padding-left: 24px;
  color: var(--muted);
}

.group-btn:hover,
.nav-btn:hover,
.sub-btn:hover {
  background: rgba(31, 35, 41, 0.06);
}

.nav-btn.on,
.sub-btn.on {
  background: #fff;
  color: var(--text);
  font-weight: 600;
}

.caret {
  color: var(--muted);
  font-size: 12px;
}

.subs {
  margin-bottom: 4px;
}

.body {
  flex: 1;
  overflow: auto;
  padding: 24px 28px 48px;
  background: #f5f6f7;
}

.body-fill {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-bottom: 20px;
}

.page-head {
  margin-bottom: 16px;
}

.layer-tabs {
  display: flex;
  gap: 6px;
  margin: 0 0 16px;
  padding: 4px;
  width: fit-content;
  border: 1px solid #dee0e3;
  border-radius: 10px;
  background: #fff;
}

.layer-tabs button {
  padding: 7px 16px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
  font-size: 13px;
}

.layer-tabs button:hover {
  color: var(--text);
}

.layer-tabs button.on {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.flow {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  margin: 0 0 20px;
  padding: 0;
  list-style: none;
}

.flow li {
  position: relative;
  padding: 8px 28px 8px 12px;
  background: #fff;
  border: 1px solid #dee0e3;
  font-size: 13px;
  color: var(--muted);
}

.flow li:first-child {
  border-radius: 8px 0 0 8px;
}

.flow li:last-child {
  padding-right: 12px;
  border-radius: 0 8px 8px 0;
  color: var(--accent);
  font-weight: 600;
}

.flow li:not(:last-child)::after {
  content: "→";
  position: absolute;
  right: 8px;
  color: #c9cdd4;
}

h2 {
  margin: 0 0 6px;
  font-size: 20px;
}

.page-head p,
.desc {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  max-width: 720px;
  line-height: 1.6;
}

.panel {
  border: 1px solid #dee0e3;
  border-radius: 12px;
  padding: 16px;
  background: #fff;
  margin-bottom: 12px;
}

h3 {
  margin: 0 0 14px;
  font-size: 14px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--muted);
}

input,
select,
textarea {
  padding: 8px 10px;
  border: 1px solid #d9dcdf;
  border-radius: 8px;
  background: #f8f9fa;
  color: var(--text);
}

input:focus,
select:focus,
textarea:focus {
  outline: none;
  border-color: var(--accent);
  background: #fff;
}

.check {
  flex-direction: row;
  align-items: center;
  gap: 8px;
  margin-top: 22px;
}

.wide {
  grid-column: 1 / -1;
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

.ghost,
.bar button:not(.primary) {
  border: 1px solid #d9dcdf;
  border-radius: 8px;
  background: #fff;
  color: var(--text);
  padding: 8px 14px;
  text-decoration: none;
}

.msg {
  color: var(--muted);
  font-size: 13px;
}

.warn {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fff7ed;
  color: #9a3412;
  font-size: 13px;
}

.inline {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.build-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin: 0 0 12px;
}

.steps {
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid #dee0e3;
  border-radius: 10px;
  overflow: hidden;
  background: #fff;
}

.steps li {
  position: relative;
  padding: 0 12px 0 16px;
  border-top: 1px solid #f0f1f2;
}

.steps li:first-child {
  border-top: 0;
}

.steps li::before {
  content: "";
  position: absolute;
  left: 27px;
  top: 36px;
  bottom: -1px;
  width: 1px;
  background: #e5e6eb;
}

.steps li:last-child::before {
  display: none;
}

.step-row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 48px;
}

.step-main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 0;
  background: transparent;
  padding: 8px 0;
  text-align: left;
  color: inherit;
}

.dot {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  border-radius: 50%;
  background: #f2f3f5;
  color: var(--muted);
  text-align: center;
  line-height: 22px;
  font-size: 12px;
  font-weight: 600;
}

.steps li.open .dot,
.steps li.running .dot {
  background: var(--accent-soft);
  color: var(--accent);
}

.steps li.success .dot {
  background: #e8f7ee;
  color: var(--success);
}

.steps li.error .dot {
  background: #fee2e2;
  color: var(--danger);
}

.steps li.off .ttl {
  color: var(--muted);
}

.ttl {
  font-size: 14px;
  font-weight: 600;
}

.param {
  flex-direction: row;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}

.param input {
  width: 88px;
  padding: 4px 8px;
}

.switch {
  flex-direction: row;
  align-items: center;
  gap: 6px;
  color: var(--muted);
}

.step-more {
  padding: 0 0 12px 32px;
}

.step-more p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.6;
}

.detail {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  background: #f8f9fa;
  color: var(--text);
  font-size: 12px;
  white-space: pre-wrap;
}

.st {
  font-size: 12px;
  font-weight: 500;
}

.st.success { color: var(--success); }
.st.skipped { color: var(--muted); }
.st.error { color: var(--danger); }
.st.running { color: var(--warning); }

.prompt-work {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 196px minmax(0, 1fr);
  gap: 12px;
}

.prompt-nav {
  align-self: start;
  padding: 8px;
  border: 1px solid #dee0e3;
  border-radius: 12px;
  background: #fff;
}

.prompt-nav section + section {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #f0f1f2;
}

.prompt-nav h4 {
  margin: 0 8px 4px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.prompt-nav button {
  width: 100%;
  text-align: left;
  padding: 8px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text);
  font-size: 13px;
}

.prompt-nav button:hover {
  background: #f5f6f7;
}

.prompt-nav button.on {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.prompt-main {
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: 1px solid #dee0e3;
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
}

.prompt-meta {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px 10px;
  border-bottom: 1px solid #f0f1f2;
}

.prompt-meta h3 {
  margin: 0 0 4px;
  font-size: 15px;
}

.prompt-meta p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}

.prompt-meta .bar {
  margin: 0;
  flex-shrink: 0;
}

.prompt-vars {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #f0f1f2;
}

.prompt-vars > span {
  margin-right: 4px;
  color: var(--muted);
  font-size: 12px;
}

.chip {
  border: 1px solid #d9dcdf;
  border-radius: 999px;
  background: #fff;
  color: var(--text);
  padding: 2px 8px;
  font-family: ui-monospace, Consolas, monospace;
  font-size: 12px;
}

.chip:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.prompt-code {
  flex: 1;
  min-height: 320px;
  width: 100%;
  margin: 0;
  padding: 14px 16px;
  border: 0;
  border-radius: 0;
  background: #fff;
  font-family: ui-monospace, Consolas, monospace;
  font-size: 13px;
  line-height: 1.65;
  resize: none;
}

.prompt-code:focus {
  background: #fff;
}

.prompt-msg {
  margin: 0;
  padding: 8px 16px 12px;
  color: var(--muted);
  font-size: 12px;
}
</style>
