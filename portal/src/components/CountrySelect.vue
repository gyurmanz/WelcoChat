<template>
  <div class="country-select" ref="rootEl">
    <input
      class="input"
      type="text"
      v-model="query"
      :placeholder="placeholder || t('common.searchCountry')"
      autocomplete="off"
      @focus="open = true"
      @input="open = true"
    />
    <ul v-if="open && filtered.length" class="country-list">
      <li
        v-for="c in filtered"
        :key="c.id"
        :class="{ 'is-selected': c.id === modelValue }"
        @mousedown.prevent="select(c)"
      >
        {{ c.name }}
      </li>
    </ul>
    <ul v-else-if="open && query.trim()" class="country-list">
      <li class="no-match">{{ t('common.noMatchingCountry') }}</li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Country } from '@/services/billing'

const { t } = useI18n()

const props = defineProps<{
  modelValue: number | null
  countries: Country[]
  placeholder?: string
}>()

const emit = defineEmits<{ 'update:modelValue': [number | null] }>()

const query = ref('')
const open = ref(false)
const rootEl = ref<HTMLElement | null>(null)

function syncQueryFromValue() {
  const c = props.countries.find((c) => c.id === props.modelValue)
  query.value = c ? c.name : ''
}

watch(() => props.modelValue, syncQueryFromValue, { immediate: true })
watch(() => props.countries, syncQueryFromValue)

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return props.countries
  return props.countries.filter((c) => c.name.toLowerCase().includes(q))
})

function select(c: Country) {
  query.value = c.name
  open.value = false
  emit('update:modelValue', c.id)
}

function handleClickOutside(e: MouseEvent) {
  if (rootEl.value && !rootEl.value.contains(e.target as Node)) {
    open.value = false
    syncQueryFromValue()
  }
}

onMounted(() => document.addEventListener('mousedown', handleClickOutside))
onBeforeUnmount(() => document.removeEventListener('mousedown', handleClickOutside))
</script>

<style scoped>
.country-select { position: relative; }
.input {
  width: 100%;
  padding: 0.55rem 0.75rem;
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(30, 41, 59, 0.6);
  color: inherit;
  font: inherit;
  font-size: 0.9rem;
  box-sizing: border-box;
}
.country-list {
  position: absolute;
  z-index: 20;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  max-height: 220px;
  overflow-y: auto;
  margin: 0;
  padding: 0.3rem 0;
  list-style: none;
  background: var(--surface, #1e293b);
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}
.country-list li {
  padding: 0.45rem 0.85rem;
  font-size: 0.88rem;
  cursor: pointer;
}
.country-list li:hover,
.country-list li.is-selected {
  background: rgba(59, 130, 246, 0.15);
}
.country-list li.no-match {
  color: rgba(148, 163, 184, 0.7);
  cursor: default;
}
.country-list li.no-match:hover { background: none; }
</style>
