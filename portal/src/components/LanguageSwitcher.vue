<template>
  <select
    class="lang-switcher"
    :value="currentLocale"
    :aria-label="t('common.language')"
    @change="onChange"
  >
    <option v-for="l in SUPPORTED_LOCALES" :key="l.code" :value="l.code">
      {{ l.name }}
    </option>
  </select>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { SUPPORTED_LOCALES, setLocale, type LocaleCode } from '@/i18n'

const { t, locale } = useI18n()

const currentLocale = computed(() => locale.value)

function onChange(e: Event) {
  const code = (e.target as HTMLSelectElement).value as LocaleCode
  setLocale(code)
}
</script>

<style scoped>
.lang-switcher {
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(30, 41, 59, 0.6);
  color: inherit;
  font: inherit;
  font-size: 0.82rem;
  cursor: pointer;
}
</style>
