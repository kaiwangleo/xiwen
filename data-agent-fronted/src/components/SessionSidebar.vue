<template>
  <aside v-if="!collapsed" class="side">
    <div class="brand">
      <span class="mark">析</span>
      <span>问</span>
    </div>
    <div class="side-top">
      <button type="button" class="new" :disabled="disabled" @click="$emit('new')">+ 新对话</button>
      <button type="button" class="icon" title="收起" @click="$emit('toggle')">‹</button>
    </div>
    <div class="list">
      <div v-if="!groups.length" class="empty">还没有会话</div>
      <section v-for="group in groups" :key="group.id" class="group">
        <button type="button" class="group-title" @click="toggleGroup(group.id)">
          <span>{{ group.open ? "▾" : "▸" }}</span>
          {{ group.title }}
        </button>
        <template v-if="group.open">
          <div
            v-for="item in group.items"
            :key="item.id"
            class="row"
            :class="{ on: item.id === activeId }"
          >
            <button type="button" class="hit" :disabled="disabled" @click="$emit('open', item.id)">
              <template v-if="editingId === item.id">
                <input
                  ref="renameInput"
                  v-model="editingTitle"
                  maxlength="20"
                  @click.stop
                  @keydown.enter.prevent="commitRename(item)"
                  @keydown.esc.prevent="editingId = ''"
                  @blur="commitRename(item)"
                />
              </template>
              <template v-else>
                <span class="title">{{ item.title || "未命名" }}</span>
                <span class="meta">{{ item.turn_count || 0 }} 问</span>
              </template>
            </button>
            <div class="more">
              <button type="button" title="重命名" @click.stop="startRename(item)">改</button>
              <button type="button" class="danger" title="删除" @click.stop="$emit('delete', item.id)">删</button>
            </div>
          </div>
        </template>
      </section>
    </div>
    <nav class="foot">
      <button type="button" @click="$emit('nav', 'settings')">设置</button>
    </nav>
  </aside>
  <div v-else class="rail">
    <span class="mark mini">析</span>
    <button type="button" class="icon" title="展开会话" @click="$emit('toggle')">☰</button>
    <button type="button" class="icon" title="新对话" :disabled="disabled" @click="$emit('new')">+</button>
    <div class="rail-foot">
      <button type="button" class="icon" title="设置" @click="$emit('nav', 'settings')">设</button>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, reactive, ref } from "vue";

const props = defineProps({
  sessions: { type: Array, default: () => [] },
  activeId: { type: String, default: "" },
  collapsed: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["toggle", "new", "open", "delete", "rename", "nav"]);

const collapsedIds = reactive({});
const editingId = ref("");
const editingTitle = ref("");
const renameInput = ref(null);

const groups = computed(() => {
  const startToday = new Date();
  startToday.setHours(0, 0, 0, 0);
  const weekAgo = new Date(startToday);
  weekAgo.setDate(weekAgo.getDate() - 7);
  const buckets = [
    { id: "today", title: "今天", items: [] },
    { id: "week", title: "近 7 天", items: [] },
    { id: "older", title: "更早", items: [] },
  ];
  for (const item of props.sessions) {
    const time = parseTime(item.updated_at);
    if (time >= startToday) buckets[0].items.push(item);
    else if (time >= weekAgo) buckets[1].items.push(item);
    else buckets[2].items.push(item);
  }
  return buckets
    .filter((g) => g.items.length)
    .map((g) => ({ ...g, open: collapsedIds[g.id] !== true }));
});

function parseTime(value) {
  /** 把服务端 "YYYY-MM-DD HH:mm:ss" 转 Date。 */
  if (!value) return new Date(0);
  return new Date(String(value).replace(" ", "T"));
}

function toggleGroup(id) {
  /** 折叠/展开日期分组。 */
  collapsedIds[id] = collapsedIds[id] !== true ? true : false;
}

async function startRename(item) {
  /** 进入行内改名。 */
  editingId.value = item.id;
  editingTitle.value = item.title || "";
  await nextTick();
  const el = Array.isArray(renameInput.value) ? renameInput.value[0] : renameInput.value;
  el?.focus();
  el?.select();
}

function commitRename(item) {
  /** 提交改名；空或未变则取消。 */
  if (editingId.value !== item.id) return;
  const title = editingTitle.value.trim();
  editingId.value = "";
  if (!title || title === item.title) return;
  emit("rename", { id: item.id, title: title.slice(0, 20) });
}
</script>

<style scoped>
.side {
  width: 260px;
  min-width: 260px;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 12px 10px 10px;
  background: #f5f6f7;
  border-right: 1px solid var(--border);
}

.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  margin: 0 4px 12px;
  font-weight: 650;
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

.mark.mini {
  margin: 0 auto 8px;
}

.side-top {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.new {
  flex: 1;
  height: 36px;
  border: 1px dashed #c9cdd4;
  border-radius: 8px;
  background: #fff;
  color: var(--text);
  font-weight: 600;
}

.new:hover {
  border-color: var(--accent);
  color: var(--accent);
}

.icon {
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--muted);
}

.icon:hover {
  background: rgba(31, 35, 41, 0.08);
}

.list {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.empty {
  padding: 16px 8px;
  color: var(--muted);
  font-size: 12px;
}

.group {
  margin-bottom: 12px;
}

.group-title {
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  text-align: left;
  padding: 4px 8px;
}

.row {
  position: relative;
  display: flex;
  align-items: center;
  border-radius: 6px;
}

.row.on {
  background: #fff;
  font-weight: 600;
}

.row:hover {
  background: rgba(31, 35, 41, 0.06);
}

.row.on:hover {
  background: #fff;
}

.hit {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  text-align: left;
  padding: 8px 10px;
  color: inherit;
}

.title {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.meta {
  display: block;
  margin-top: 2px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 400;
}

.hit input {
  width: 100%;
  border: 1px solid var(--accent);
  border-radius: 4px;
  padding: 2px 6px;
}

.more {
  display: none;
  gap: 2px;
  padding-right: 6px;
}

.row:hover .more,
.row.on .more {
  display: flex;
}

.more button {
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  padding: 2px 4px;
  border-radius: 4px;
}

.more button:hover {
  background: rgba(31, 35, 41, 0.08);
}

.more .danger:hover {
  background: #fee2e2;
  color: var(--danger);
}

.foot {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}

.foot button {
  width: 100%;
  height: 36px;
  padding: 0 12px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text);
  text-align: left;
}

.foot button:hover {
  background: rgba(31, 35, 41, 0.06);
}

.foot button.on {
  background: #fff;
  color: var(--accent);
  font-weight: 600;
}

.rail {
  width: 48px;
  min-width: 48px;
  padding: 12px 6px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #f5f6f7;
  border-right: 1px solid var(--border);
}

.rail-foot {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
