<template>
  <div class="page">
    <h1>{{ t('support.title') }}</h1>
    <p class="step-subtitle">{{ t('support.intro') }}</p>

    <div v-if="sent" class="sent-state">
      <div class="sent-icon">✓</div>
      <h2 class="sent-title">{{ t('support.sentTitle') }}</h2>
      <p class="sent-body">{{ t('support.sentBody') }}</p>
      <button class="btn btn-outline btn-sm" @click="resetForm">{{ t('support.sendAnother') }}</button>
    </div>

    <form v-else class="support-form" @submit.prevent="submit" novalidate>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>

      <div class="form-row">
        <label class="form-label">{{ t('support.topicLabel') }}</label>
        <div class="topic-options">
          <label v-for="opt in topics" :key="opt.value" class="topic-option" :class="{ 'is-selected': topic === opt.value }">
            <input type="radio" name="topic" :value="opt.value" v-model="topic" />
            <span class="topic-name">{{ opt.label }}</span>
            <span class="topic-note">{{ opt.note }}</span>
          </label>
        </div>
      </div>

      <div class="form-row">
        <label class="form-label" for="support-subject">{{ t('support.subjectLabel') }}</label>
        <input id="support-subject" v-model="subject" class="input" maxlength="150" :placeholder="t('support.subjectPlaceholder')" />
      </div>

      <div class="form-row">
        <label class="form-label" for="support-message">{{ t('support.messageLabel') }}</label>
        <textarea id="support-message" v-model="message" class="input textarea" rows="8" maxlength="5000" :placeholder="t('support.messagePlaceholder')"></textarea>
        <span class="field-hint">{{ t('support.contextHint') }}</span>
      </div>

      <div class="form-actions">
        <button class="btn btn-primary" type="submit" :disabled="sending || !canSubmit">
          {{ sending ? t('support.sending') : t('support.send') }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { sendSupportRequest, type SupportTopic } from '@/services/support'

const { t } = useI18n()

const topic = ref<SupportTopic>('bug')
const subject = ref('')
const message = ref('')
const sending = ref(false)
const sent = ref(false)
const error = ref('')

const topics = computed(() => [
  { value: 'bug' as const, label: t('support.topicBug'), note: t('support.topicBugNote') },
  { value: 'idea' as const, label: t('support.topicIdea'), note: t('support.topicIdeaNote') },
  { value: 'question' as const, label: t('support.topicQuestion'), note: t('support.topicQuestionNote') },
])

const canSubmit = computed(() => subject.value.trim().length >= 3 && message.value.trim().length >= 10)

function resetForm() {
  sent.value = false
  subject.value = ''
  message.value = ''
  topic.value = 'bug'
  error.value = ''
}

async function submit() {
  if (!canSubmit.value) return
  sending.value = true
  error.value = ''
  try {
    await sendSupportRequest(topic.value, subject.value.trim(), message.value.trim())
    sent.value = true
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('support.errorSend')
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.step-subtitle { color: rgba(148, 163, 184, 0.85); margin: 0.25rem 0 1.5rem; max-width: 60ch; }
.support-form { max-width: 560px; display: flex; flex-direction: column; gap: 1.25rem; }
.form-row { display: flex; flex-direction: column; gap: 0.4rem; }
.form-label { font-size: 0.85rem; font-weight: 600; }
.input {
  width: 100%; box-sizing: border-box;
  padding: 0.55rem 0.75rem; border-radius: 6px; border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(30, 41, 59, 0.6); color: inherit; font: inherit; font-size: 0.9rem;
}
.textarea { resize: vertical; line-height: 1.5; }
.field-hint { font-size: 0.78rem; color: rgba(148, 163, 184, 0.7); }
.form-error { color: #f87171; font-size: 0.88rem; margin: 0; }
.form-actions { margin-top: 0.25rem; }

.topic-options { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.5rem; }
.topic-option {
  display: flex; flex-direction: column; gap: 0.15rem;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 8px; padding: 0.7rem 0.85rem; cursor: pointer;
}
.topic-option.is-selected { border-color: rgba(52, 211, 153, 0.7); background: rgba(34, 197, 94, 0.08); }
.topic-option input { position: absolute; opacity: 0; pointer-events: none; }
.topic-option:focus-within { outline: 2px solid rgba(52, 211, 153, 0.6); outline-offset: 2px; }
.topic-name { font-size: 0.88rem; font-weight: 600; }
.topic-note { font-size: 0.76rem; color: rgba(148, 163, 184, 0.75); }

.sent-state {
  max-width: 460px; border: 1px solid rgba(52, 211, 153, 0.4);
  background: rgba(34, 197, 94, 0.06); border-radius: 10px; padding: 1.75rem;
  display: flex; flex-direction: column; align-items: flex-start; gap: 0.4rem;
}
.sent-icon {
  width: 34px; height: 34px; border-radius: 50%;
  background: rgba(34, 197, 94, 0.18); color: #4ade80;
  display: flex; align-items: center; justify-content: center; font-weight: 700;
}
.sent-title { font-size: 1.05rem; margin: 0.3rem 0 0; }
.sent-body { color: rgba(148, 163, 184, 0.9); font-size: 0.88rem; margin: 0 0 0.6rem; }
</style>
