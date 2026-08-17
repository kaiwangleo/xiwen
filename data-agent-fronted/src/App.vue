<template>
  <div class="page">
    <AskView v-show="view === 'ask'" @nav="view = $event" />
    <SettingsView v-if="view === 'settings'" @nav="view = $event" />
  </div>
</template>

<script setup>
import { ref } from "vue";
import AskView from "./views/AskView.vue";
import SettingsView from "./views/SettingsView.vue";

const view = ref("ask");
</script>

<style scoped>
.page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}
</style>
