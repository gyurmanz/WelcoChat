<template>
  <div v-if="isLoading" class="global-loading-overlay">
    <div class="global-loading-backdrop"></div>
    <div class="global-loading-dialog">
      <div class="global-loading-card">
        <div class="global-loading-spinner"></div>
        <p class="global-loading-text">Please wait…</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { isGlobalLoading } from '@/services/http'

const isLoading = computed(() => isGlobalLoading.value)
</script>
