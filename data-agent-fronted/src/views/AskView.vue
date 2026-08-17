<template>
  <div class="ask">
    <SessionSidebar
      :sessions="sessions"
      :active-id="sessionId"
      :collapsed="sidebarCollapsed"
      :disabled="loading"
      @toggle="toggleSidebar"
      @new="startNew"
      @open="openSession"
      @delete="removeSession"
      @rename="onRename"
      @nav="$emit('nav', $event)"
    />

    <section class="workspace">
      <main ref="scroller" class="main" @scroll="onScroll">
        <EmptyState v-if="!turns.length" :examples="quickAsks" @pick="ask" />

        <div v-else class="thread">
          <article v-for="turn in turns" :key="turn.id" class="turn">
            <div class="user">{{ turn.query }}</div>
            <p v-if="turn.kind === 'local'" class="local">{{ turn.localText }}</p>
            <template v-else>
              <ProgressPanel
                v-if="turn.steps.length || turn.status === 'running'"
                :steps="turn.steps"
                :status="turn.status"
              />
              <ResultPane
                v-if="turn.result"
                :columns="turn.result.columns"
                :rows="turn.result.rows"
                :sql="turn.result.sql"
                :show-sql-entry="showSql"
                :preferred-chart="chartDefault"
              />
              <div v-if="turn.error" class="error">{{ turn.error }}</div>
            </template>
          </article>
        </div>
      </main>
      <Composer
        v-model="draft"
        :loading="loading"
        :current-step="currentStep"
        :chips="composerChips"
        :chip-label="turns.length ? '继续问' : '猜你想问'"
        @send="submit"
        @pick="ask"
      />
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import Composer from "../components/Composer.vue";
import EmptyState from "../components/EmptyState.vue";
import ProgressPanel from "../components/ProgressPanel.vue";
import ResultPane from "../components/ResultPane.vue";
import SessionSidebar from "../components/SessionSidebar.vue";
import { getConfig } from "../api/admin.js";
import {
  createSession,
  deleteSession,
  getSession,
  listSessions,
  renameSession,
  saveSession,
} from "../api/sessions.js";
import { useQueryStream } from "../composables/useQueryStream.js";
import { CHAT_REPLY, isDataQuery } from "../utils/intent.js";

defineEmits(["nav"]);

const STORAGE_KEY = "xiwen.activeSession";
const SIDEBAR_KEY = "xiwen.sidebarCollapsed";
const LEGACY_STORAGE_KEY = "zhanggui.activeSession";
const LEGACY_SIDEBAR_KEY = "zhanggui.sidebarCollapsed";
const followUps = ["按时间对比一下？", "再按品类拆开看？"];

/** 读新键；若只有旧键则迁到 xiwen.* 并删旧键。 */
function readPref(key, legacyKey) {
  const current = localStorage.getItem(key);
  if (current != null) return current;
  const legacy = localStorage.getItem(legacyKey);
  if (legacy == null) return null;
  localStorage.setItem(key, legacy);
  localStorage.removeItem(legacyKey);
  return legacy;
}

const draft = ref("");
const scroller = ref(null);
const sessionId = ref("");
const sessions = ref([]);
const sidebarCollapsed = ref(readPref(SIDEBAR_KEY, LEGACY_SIDEBAR_KEY) === "1");
const quickAsks = ref([]);
const showSql = ref(true);
const chartDefault = ref("auto");
const stickToBottom = ref(true);
const { turns, loading, currentStep, send, clear, addLocal, setTurns } = useQueryStream();

const composerChips = computed(() => {
  const last = turns.value.at(-1);
  return last?.result ? followUps : [];
});

watch(
  turns,
  async () => {
    if (!stickToBottom.value) return;
    await nextTick();
    const el = scroller.value;
    if (el) el.scrollTop = el.scrollHeight;
  },
  { deep: true },
);

onMounted(async () => {
  try {
    const data = await getConfig();
    const ui = data.config?.ui || {};
    quickAsks.value = ui.quick_asks || [];
    showSql.value = ui.show_sql !== false;
    chartDefault.value = data.config?.chart?.default || "auto";
  } catch {
    /* keep defaults */
  }
  await refreshSessions();
  const remembered = readPref(STORAGE_KEY, LEGACY_STORAGE_KEY);
  if (remembered && sessions.value.some((s) => s.id === remembered)) {
    await openSession(remembered);
  }
});

function onScroll() {
  /** 离开底部则暂停自动滚。 */
  const el = scroller.value;
  if (!el) return;
  stickToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
}

function toggleSidebar() {
  /** 折叠侧栏并写入 xiwen.sidebarCollapsed。 */
  sidebarCollapsed.value = !sidebarCollapsed.value;
  localStorage.setItem(SIDEBAR_KEY, sidebarCollapsed.value ? "1" : "0");
}

function remember(id) {
  /** 记住当前会话 id；空则清掉。 */
  sessionId.value = id;
  if (id) localStorage.setItem(STORAGE_KEY, id);
  else localStorage.removeItem(STORAGE_KEY);
}

async function refreshSessions() {
  /** 刷新侧栏会话列表。 */
  try {
    const data = await listSessions();
    sessions.value = data.sessions || [];
  } catch {
    sessions.value = [];
  }
}

function startNew() {
  /** 离开当前会话，本地开新线程。 */
  if (loading.value) return;
  remember("");
  clear();
  stickToBottom.value = true;
}

async function openSession(id) {
  /** 加载会话整包到线程。 */
  if (loading.value || id === sessionId.value) return;
  const data = await getSession(id);
  remember(data.id);
  setTurns(data.turns || []);
  stickToBottom.value = true;
  await nextTick();
  const el = scroller.value;
  if (el) el.scrollTop = el.scrollHeight;
}

async function removeSession(id) {
  /** 删会话；若正在看则回到空白。 */
  await deleteSession(id);
  sessions.value = sessions.value.filter((s) => s.id !== id);
  if (sessionId.value === id) startNew();
}

async function onRename({ id, title }) {
  /** 侧栏重命名回写。 */
  const saved = await renameSession(id, title);
  const idx = sessions.value.findIndex((s) => s.id === id);
  if (idx >= 0) sessions.value[idx] = { ...sessions.value[idx], title: saved.title };
}

async function persist() {
  /** 把当前线程整包写入元库。 */
  if (!turns.value.length) return;
  const title = (turns.value[0]?.query || "新会话").slice(0, 40);
  if (!sessionId.value) {
    const created = await createSession(title);
    remember(created.id);
    sessions.value = [created, ...sessions.value.filter((s) => s.id !== created.id)];
  }
  const saved = await saveSession(sessionId.value, {
    title,
    turns: turns.value.map((turn) => ({
      id: turn.id,
      query: turn.query,
      kind: turn.kind,
      localText: turn.localText,
      steps: turn.steps,
      result: turn.result,
      error: turn.error,
      status: turn.status,
    })),
  });
  const summary = {
    id: saved.id,
    title: saved.title,
    updated_at: saved.updated_at,
    turn_count: saved.turn_count,
  };
  const idx = sessions.value.findIndex((s) => s.id === saved.id);
  if (idx >= 0) sessions.value.splice(idx, 1, summary);
  else sessions.value.unshift(summary);
  sessions.value.sort((a, b) => String(b.updated_at).localeCompare(String(a.updated_at)));
}

async function ask(text) {
  /** 闲聊本地回复，问数走 SSE，最后落库。 */
  draft.value = "";
  const query = text.trim();
  if (!query || loading.value) return;
  stickToBottom.value = true;
  if (!isDataQuery(query)) {
    addLocal(query, CHAT_REPLY);
  } else {
    await send(query);
  }
  try {
    await persist();
  } catch (e) {
    const last = turns.value.at(-1);
    if (last && !last.error) last.error = e.message || "会话保存失败";
  }
}

function submit() {
  ask(draft.value);
}
</script>

<style scoped>
.ask {
  flex: 1;
  min-height: 0;
  display: flex;
  background: #fff;
}

.workspace {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.main {
  flex: 1;
  overflow-y: auto;
}

.thread {
  max-width: 800px;
  margin: 0 auto;
  padding: 24px 20px 8px;
}

.turn {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 28px;
}

.user {
  align-self: flex-end;
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 12px 12px 4px 12px;
  background: #f5f6f7;
  color: #1f2329;
}

.local {
  margin: 0;
  padding: 12px 16px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid var(--border);
  white-space: pre-wrap;
}

.error {
  padding: 12px 16px;
  border-radius: 12px;
  background: #fef2f2;
  color: var(--danger);
  border: 1px solid #fecaca;
}

@media (max-width: 800px) {
  .thread {
    padding: 16px 12px;
  }
}
</style>
