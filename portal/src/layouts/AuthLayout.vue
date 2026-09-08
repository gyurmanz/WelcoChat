<template>
  <div class="layout layout-auth">
    <div class="layout-auth-lang">
      <LanguageSwitcher />
    </div>
    <main class="layout-auth-main">
      <div class="page page-auth">
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'
</script>

<style scoped>
.layout-auth {
  position: relative;
}
.layout-auth-lang {
  position: absolute;
  top: 1rem;
  right: 1rem;
  z-index: 10;
}
</style>
