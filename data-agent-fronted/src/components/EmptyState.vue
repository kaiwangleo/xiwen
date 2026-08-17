<template>
  <section class="empty">
    <div class="mark">析</div>
    <h1>你好，我是析问</h1>
    <p>用自然语言查数仓，我会生成 SQL，并把结果做成表和图。</p>
    <div class="examples">
      <button v-for="item in list" :key="item" type="button" @click="$emit('pick', item)">
        <span class="dot">◇</span>
        {{ item }}
      </button>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";
const props = defineProps({
  examples: { type: Array, default: () => [] },
});
defineEmits(["pick"]);

const fallback = [
  "统计去年各地区的销售总额",
  "黄金会员的平均客单价",
  "零食类商品销量排行",
];
const list = computed(() => (props.examples.length ? props.examples : fallback));
</script>

<style scoped>
.empty {
  max-width: 720px;
  margin: 0 auto;
  padding: 80px 16px 24px;
  text-align: center;
}

.mark {
  width: 52px;
  height: 52px;
  margin: 0 auto 16px;
  border-radius: 14px;
  background: var(--accent);
  color: #fff;
  font-weight: 700;
  font-size: 24px;
  line-height: 52px;
}

h1 {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 650;
}

p {
  margin: 0 0 28px;
  color: var(--muted);
}

.examples {
  display: grid;
  gap: 10px;
  max-width: 520px;
  margin: 0 auto;
}

.examples button {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border: 1px dashed #c9cdd4;
  border-radius: 12px;
  background: #fff;
  color: var(--text);
  text-align: left;
}

.examples button:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent);
}

.dot {
  color: var(--accent);
}
</style>
