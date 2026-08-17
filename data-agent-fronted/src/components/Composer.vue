<template>
  <div class="dock">
    <div v-if="chips.length" class="chips">
      <span class="guess">{{ chipLabel }}</span>
      <button v-for="item in chips" :key="item" type="button" :disabled="loading" @click="$emit('pick', item)">
        {{ item }}
      </button>
    </div>
    <div class="box">
      <textarea
        ref="area"
        :value="modelValue"
        rows="1"
        :placeholder="placeholder"
        :disabled="loading"
        @input="onInput"
        @keydown="onKeydown"
      />
      <div class="bar">
        <span class="tip">Enter 发送 · Shift+Enter 换行</span>
        <button type="button" :disabled="loading || !modelValue.trim()" @click="$emit('send')">
          {{ loading ? `${currentStep || "执行中"}…` : "发送" }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: String, default: "" },
  loading: { type: Boolean, default: false },
  currentStep: { type: String, default: "" },
  placeholder: { type: String, default: "输入你的问题，例如：统计去年各地区的销售总额" },
  chips: { type: Array, default: () => [] },
  chipLabel: { type: String, default: "猜你想问" },
});

const emit = defineEmits(["update:modelValue", "send", "pick"]);
const area = ref(null);

watch(
  () => props.modelValue,
  () => nextTick(fit),
);

function fit() {
  const el = area.value;
  if (!el) return;
  el.style.height = "auto";
  el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
}

function onInput(event) {
  emit("update:modelValue", event.target.value);
  fit();
}

function onKeydown(event) {
  if (event.isComposing || event.keyCode === 229) return;
  if (event.key === "Enter" && !event.shiftKey && !event.ctrlKey) {
    event.preventDefault();
    if (!props.modelValue.trim() || props.loading) return;
    emit("send");
  }
}
</script>

<style scoped>
.dock {
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
  padding: 8px 20px 20px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.guess {
  color: var(--muted);
  font-size: 12px;
}

.chips button {
  padding: 5px 10px;
  border: 0;
  border-radius: 999px;
  background: #eef0f2;
  color: #1f2329;
  font-size: 12px;
}

.chips button:hover:not(:disabled) {
  background: var(--accent-soft);
  color: var(--accent);
}

.box {
  padding: 12px 14px 10px;
  border: 1px solid #d9dcdf;
  border-radius: 16px;
  background: #f8f9fa;
}

textarea {
  width: 100%;
  min-height: 44px;
  max-height: 140px;
  resize: none;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--text);
  line-height: 1.5;
}

.bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 6px;
}

.tip {
  color: #9aa0a6;
  font-size: 12px;
}

.bar button {
  padding: 6px 16px;
  border: 0;
  border-radius: 8px;
  background: var(--accent);
  color: #fff;
}

.bar button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
