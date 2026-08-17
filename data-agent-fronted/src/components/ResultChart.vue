<template>
  <div ref="el" class="chart"></div>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as echarts from "echarts";

const props = defineProps({
  option: { type: Object, default: null },
});

const el = ref(null);
let chart;

function render() {
  if (!chart || !props.option) return;
  chart.setOption(props.option, true);
}

onMounted(() => {
  chart = echarts.init(el.value);
  render();
  window.addEventListener("resize", resize);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resize);
  chart?.dispose();
});

watch(() => props.option, render, { deep: true });

function resize() {
  chart?.resize();
}
</script>

<style scoped>
.chart {
  width: 100%;
  height: 352px;
}
</style>
