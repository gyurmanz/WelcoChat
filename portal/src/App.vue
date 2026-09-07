<template>
  <component :is="layoutComponent">
    <RouterView />
    <GlobalLoadingOverlay />
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AuthLayout from '@/layouts/AuthLayout.vue'
import DashboardLayout from '@/layouts/DashboardLayout.vue'
import GlobalLoadingOverlay from '@/components/GlobalLoadingOverlay.vue'

const route = useRoute()

const layoutComponent = computed(() => {
  const layout = route.meta.layout
  if (layout === 'dashboard') return DashboardLayout
  // default: auth layout
  return AuthLayout
})
</script>
