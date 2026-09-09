<template>
  <div class="page">
    <div v-if="loading" class="input-hint">{{ t('common.loading') }}</div>

    <div v-else-if="loadError" class="empty-state">
      <p class="empty-text">{{ loadError }}</p>
      <router-link to="/subscriptions" class="btn btn-primary">{{ t('addSub.goToServices') }}</router-link>
    </div>

    <template v-else>
      <h1>{{ isManaging ? t('welcoSetup.manageTitle') : t('welcoSetup.setupTitle') }}</h1>

      <!-- Stepper (only during initial setup, not once the agent is live) -->
      <div v-if="!isManaging" class="stepper" :aria-label="t('welcoSetup.stepperAriaLabel')">
        <div
          v-for="(label, i) in stepLabels"
          :key="i"
          class="stepper-item"
          :class="{ 'is-active': wizardStep === i + 1, 'is-done': wizardStep > i + 1 }"
        >
          <div class="stepper-dot">{{ wizardStep > i + 1 ? '✓' : i + 1 }}</div>
          <span class="stepper-label">{{ label }}</span>
        </div>
      </div>

      <p v-if="error" class="form-error" role="alert">{{ error }}</p>

      <!-- STEP 1: Overview -->
      <section v-if="wizardStep === 1" class="order-section">
        <p class="step-subtitle">{{ t('welcoSetup.step1Subtitle') }}</p>

        <div class="review-block">
          <div class="review-row"><span>{{ t('welcoSetup.product') }}</span><b>WelcoChat</b></div>
          <div class="review-row"><span>{{ t('addSub.plan') }}</span><b>{{ instanceTier }}</b></div>
          <div class="review-row"><span>{{ t('welcoSetup.currentStatus') }}</span><b>{{ statusLabel(setupStatus) }}</b></div>
          <div v-if="subscription?.status === 'trialing'" class="review-row">
            <span>{{ t('welcoSetup.trial') }}</span><b>{{ t('welcoSetup.endsDate', { date: formatDate(subscription.trial_ends_at) }) }}</b>
          </div>
          <div v-if="subscription?.start_date" class="review-row">
            <span>{{ t('welcoSetup.started') }}</span><b>{{ formatDate(subscription.start_date) }}</b>
          </div>
          <div v-if="subscription?.pending_tier" class="review-row">
            <span>{{ t('welcoSetup.downgradesTo') }}</span><b>{{ subscription.pending_tier }} {{ t('welcoSetup.onDate', { date: formatDate(subscription.end_date) }) }}</b>
          </div>
          <div v-else-if="subscription?.end_date" class="review-row">
            <span>{{ t('welcoSetup.renews') }}</span><b>{{ formatDate(subscription.end_date) }}</b>
          </div>
        </div>

        <p class="review-next">
          {{ t('welcoSetup.explainWelco') }}
        </p>

        <div class="form-actions">
          <button class="btn btn-primary" @click="startSetup">{{ t('welcoSetup.startSetup') }}</button>
        </div>
      </section>

      <!-- STEP 2: Connect content -->
      <section v-if="wizardStep === 2" class="order-section">
        <button class="back-btn" @click="wizardStep = 1">{{ t('addSub.back') }}</button>
        <p class="step-subtitle">
          {{ t('welcoSetup.step2Subtitle') }}
          <a href="/guides/prompt-and-content-guide/" target="_blank" rel="noopener">{{ t('welcoSetup.contentGuideLink') }}</a>.
        </p>

        <form class="billing-form" @submit.prevent="wizardStep = 3" novalidate>
          <div class="form-row">
            <label class="form-label">{{ t('welcoSetup.websiteUrl') }} <span class="req">*</span></label>
            <input v-model="form.website_url" class="input" placeholder="https://yourcompany.com" />
            <span class="field-hint">{{ t('welcoSetup.websiteUrlHint') }}</span>
          </div>
          <div class="form-row">
            <label class="form-label">{{ t('welcoSetup.additionalDocsLabel') }}</label>
            <textarea v-model="form.additional_docs_note" class="input textarea textarea-lg" rows="8" :placeholder="t('welcoSetup.additionalDocsPlaceholder')"></textarea>
          </div>
          <div class="form-row">
            <label class="form-label">{{ t('welcoSetup.documentsLabel') }}</label>
            <input
              ref="fileInputEl"
              type="file"
              multiple
              accept=".pdf,.docx,.txt"
              class="file-input"
              @change="onFilesSelected"
            />
            <span class="field-hint">{{ t('welcoSetup.documentsHint') }}</span>

            <p v-if="uploadingDocs" class="input-hint">{{ t('welcoSetup.uploading') }}</p>

            <ul v-if="documents.length" class="doc-list">
              <li v-for="doc in documents" :key="doc.id" class="doc-row">
                <span class="doc-name">{{ doc.file_name }}</span>
                <span class="doc-meta">{{ t('welcoSetup.charsCount', { count: doc.char_count ?? 0 }) }}</span>
                <button type="button" class="btn-remove" @click="removeDocument(doc.id)" :aria-label="t('welcoSetup.removeDocument')">✕</button>
              </li>
            </ul>
            <ul v-if="uploadErrors.length" class="doc-errors">
              <li v-for="(err, i) in uploadErrors" :key="i" class="doc-error">{{ err.file_name }}: {{ err.error }}</li>
            </ul>
          </div>
          <div class="form-actions">
            <button type="submit" class="btn btn-primary">{{ t('welcoSetup.continue') }}</button>
          </div>
        </form>
      </section>

      <!-- STEP 3: Widget customization -->
      <section v-if="wizardStep === 3" class="order-section">
        <button class="back-btn" @click="wizardStep = 2">{{ t('addSub.back') }}</button>
        <p class="step-subtitle">{{ t('welcoSetup.step3Subtitle') }}</p>

        <form class="billing-form" @submit.prevent="wizardStep = 4" novalidate>
          <div class="form-row">
            <label class="form-label">{{ t('welcoSetup.widgetNameLabel') }}</label>
            <input v-model="form.widget_name" class="input" :placeholder="t('welcoSetup.widgetNamePlaceholder')" />
          </div>
          <div class="form-row">
            <label class="form-label">{{ t('welcoSetup.greetingLabel') }}</label>
            <textarea v-model="form.greeting_message" class="input textarea" rows="2" :placeholder="t('welcoSetup.greetingPlaceholder')"></textarea>
          </div>

          <h3 class="section-h3">{{ t('welcoSetup.appearance') }}</h3>
          <div class="form-row">
            <label class="form-label">{{ t('welcoSetup.themeLabel') }}</label>
            <select v-model="form.widget_theme" class="input">
              <option value="light">{{ t('welcoSetup.themeLight') }}</option>
              <option value="dark">{{ t('welcoSetup.themeDark') }}</option>
              <option value="custom">{{ t('welcoSetup.themeCustom') }}</option>
            </select>
          </div>
          <template v-if="form.widget_theme === 'custom'">
            <div class="form-row">
              <label class="form-label">{{ t('welcoSetup.accentColor') }}</label>
              <input v-model="form.widget_color" class="input color-input" type="color" />
            </div>
            <div class="form-row">
              <label class="form-label">{{ t('welcoSetup.backgroundColor') }}</label>
              <input v-model="form.widget_bg_color" class="input color-input" type="color" />
            </div>
          </template>

          <div class="form-actions">
            <button type="submit" class="btn btn-primary">{{ t('welcoSetup.continueToReview') }}</button>
          </div>
        </form>
      </section>

      <!-- STEP 4: Review -->
      <section v-if="wizardStep === 4" class="order-section">
        <button class="back-btn" @click="wizardStep = 3">{{ t('addSub.back') }}</button>
        <h2 class="review-h2">{{ t('welcoSetup.reviewSetup') }}</h2>

        <div class="review-block">
          <div class="review-block-title">{{ t('welcoSetup.content') }}</div>
          <div class="review-row"><span>{{ t('welcoSetup.website') }}</span><b>{{ form.website_url || '-' }}</b></div>
          <div class="review-row" v-if="form.additional_docs_note"><span>{{ t('welcoSetup.additionalDocs') }}</span><b>{{ form.additional_docs_note }}</b></div>
        </div>

        <div class="review-block">
          <div class="review-block-title">{{ t('welcoSetup.widget') }}</div>
          <div class="review-row"><span>{{ t('welcoSetup.name') }}</span><b>{{ form.widget_name || 'Welco Assistant' }}</b></div>
          <div class="review-row" v-if="form.greeting_message"><span>{{ t('welcoSetup.greeting') }}</span><b>{{ form.greeting_message }}</b></div>
        </div>

        <div class="review-block">
          <div class="review-block-title">{{ t('welcoSetup.appearance') }}</div>
          <div class="review-row"><span>{{ t('welcoSetup.theme') }}</span><b>{{ themeLabel(form.widget_theme) }}</b></div>
          <template v-if="form.widget_theme === 'custom'">
            <div class="review-row"><span>{{ t('welcoSetup.accentColor') }}</span><b>{{ form.widget_color }}</b></div>
            <div class="review-row"><span>{{ t('welcoSetup.backgroundColor') }}</span><b>{{ form.widget_bg_color }}</b></div>
          </template>
        </div>

        <div class="review-checks">
          <label class="check-row">
            <input type="checkbox" v-model="confirmCorrect" />
            {{ t('welcoSetup.confirmCorrect') }}
          </label>
        </div>

        <div class="form-actions">
          <button class="btn btn-outline" :disabled="saving" @click="saveDraft">
            {{ saving ? t('welcoSetup.savingEllipsis') : t('welcoSetup.saveAsDraft') }}
          </button>
          <button class="btn btn-primary" :disabled="!confirmCorrect || saving" @click="submitForActivation">
            {{ saving ? t('welcoSetup.submitting') : t('welcoSetup.submitForActivation') }}
          </button>
        </div>
        <p v-if="draftSaved" class="draft-saved">{{ t('welcoSetup.draftSaved') }}</p>
      </section>

      <!-- STEP 5: Activation status -->
      <section v-if="wizardStep === 5" class="order-section">
        <template v-if="welcoStatus === 'ready'">
          <div class="confirm-icon">✓</div>
          <h2 class="confirm-h2">{{ t('welcoSetup.agentLiveTitle') }}</h2>
          <p class="confirm-sub">
            {{ welcoPageCount === 1 ? t('welcoSetup.crawledPagesOne', { count: welcoPageCount }) : t('welcoSetup.crawledPagesMany', { count: welcoPageCount }) }}
            {{ t('welcoSetup.pasteSnippet') }}
          </p>
          <div class="embed-box">
            <code>{{ embedSnippet }}</code>
            <button class="btn btn-outline btn-sm" @click="copyEmbedSnippet">
              {{ copied ? t('welcoSetup.copied') : t('welcoSetup.copy') }}
            </button>
          </div>
          <p class="field-hint">
            {{ t('welcoSetup.installGuideHint') }}
            <a href="/guides/add-to-your-website/" target="_blank" rel="noopener">{{ t('welcoSetup.installGuideLink') }}</a>.
          </p>

          <div class="manage-section">
            <h3 class="manage-h3">{{ t('welcoSetup.subscription') }}</h3>
            <div class="review-block">
              <div class="review-row"><span>{{ t('welcoSetup.product') }}</span><b>WelcoChat</b></div>
              <div class="review-row"><span>{{ t('addSub.plan') }}</span><b>{{ instanceTier }}</b></div>
              <div v-if="subscription?.status === 'trialing'" class="review-row">
                <span>{{ t('welcoSetup.trial') }}</span><b>{{ t('welcoSetup.endsDate', { date: formatDate(subscription.trial_ends_at) }) }}</b>
              </div>
              <div v-if="subscription?.start_date" class="review-row">
                <span>{{ t('welcoSetup.started') }}</span><b>{{ formatDate(subscription.start_date) }}</b>
              </div>
              <div v-if="subscription?.pending_tier" class="review-row">
                <span>{{ t('welcoSetup.downgradesTo') }}</span><b>{{ subscription.pending_tier }} {{ t('welcoSetup.onDate', { date: formatDate(subscription.end_date) }) }}</b>
              </div>
              <div v-else-if="subscription?.end_date" class="review-row">
                <span>{{ t('welcoSetup.renews') }}</span><b>{{ formatDate(subscription.end_date) }}</b>
              </div>
            </div>
            <div class="form-actions">
              <router-link v-if="subscriptionId" :to="`/subscriptions/${subscriptionId}/change-plan`" class="btn btn-outline btn-sm">{{ t('changePlan.title') }}</router-link>
            </div>
          </div>

          <div class="manage-section">
            <h3 class="manage-h3">{{ t('welcoSetup.website') }}</h3>
            <p class="field-hint">{{ t('welcoSetup.websiteChangeHint') }}</p>
            <input v-model="form.website_url" class="input" placeholder="https://yourcompany.com" />
            <div class="form-actions">
              <button class="btn btn-outline btn-sm" :disabled="activating" @click="saveWebsiteAndRecrawl">
                {{ activating ? t('welcoSetup.recrawling') : t('welcoSetup.saveAndRecrawl') }}
              </button>
            </div>
          </div>

          <div class="manage-section">
            <h3 class="manage-h3">{{ t('welcoSetup.widget') }}</h3>
            <p class="field-hint">{{ t('welcoSetup.immediateEffectHint') }}</p>
            <div class="form-row">
              <label class="form-label">{{ t('welcoSetup.widgetNameLabel') }}</label>
              <input v-model="form.widget_name" class="input" :placeholder="t('welcoSetup.widgetNamePlaceholder')" />
            </div>
            <div class="form-row">
              <label class="form-label">{{ t('welcoSetup.greetingLabel') }}</label>
              <textarea v-model="form.greeting_message" class="input textarea" rows="2" :placeholder="t('welcoSetup.greetingPlaceholder')"></textarea>
            </div>
            <div class="form-actions">
              <button class="btn btn-outline btn-sm" :disabled="savingWidget" @click="saveWidgetSettings">
                {{ savingWidget ? t('welcoSetup.savingEllipsis') : t('welcoSetup.saveWidgetSettings') }}
              </button>
              <span v-if="widgetSaved" class="draft-saved">{{ t('welcoSetup.saved') }}</span>
            </div>
          </div>

          <div class="manage-section">
            <h3 class="manage-h3">{{ t('welcoSetup.appearance') }}</h3>
            <p class="field-hint">{{ t('welcoSetup.immediateEffectHint') }}</p>
            <div class="form-row">
              <label class="form-label">{{ t('welcoSetup.themeLabel') }}</label>
              <select v-model="form.widget_theme" class="input">
                <option value="light">{{ t('welcoSetup.themeLight') }}</option>
                <option value="dark">{{ t('welcoSetup.themeDark') }}</option>
                <option value="custom">{{ t('welcoSetup.themeCustom') }}</option>
              </select>
            </div>
            <template v-if="form.widget_theme === 'custom'">
              <div class="form-row">
                <label class="form-label">{{ t('welcoSetup.accentColor') }}</label>
                <input v-model="form.widget_color" class="input color-input" type="color" />
              </div>
              <div class="form-row">
                <label class="form-label">{{ t('welcoSetup.backgroundColor') }}</label>
                <input v-model="form.widget_bg_color" class="input color-input" type="color" />
              </div>
            </template>
            <div class="form-actions">
              <button class="btn btn-outline btn-sm" :disabled="savingAppearance" @click="saveAppearance">
                {{ savingAppearance ? t('welcoSetup.savingEllipsis') : t('welcoSetup.saveAppearance') }}
              </button>
              <span v-if="appearanceSaved" class="draft-saved">{{ t('welcoSetup.saved') }}</span>
            </div>

            <h4 class="manage-h4">{{ t('welcoSetup.logoAndPosition') }}</h4>
            <template v-if="hasBusinessTier">
              <div class="form-row">
                <label class="form-label">{{ t('welcoSetup.logo') }}</label>
                <div class="logo-row">
                  <img v-if="widgetLogoUrl" :src="widgetLogoUrl" :alt="t('welcoSetup.widgetLogoAlt')" class="logo-preview" />
                  <input ref="logoInputEl" type="file" accept="image/png,image/jpeg,image/webp,image/svg+xml" class="file-input" @change="onLogoSelected" />
                  <button v-if="widgetLogoUrl" type="button" class="btn btn-outline btn-sm" :disabled="removingLogo" @click="onRemoveLogo">
                    {{ removingLogo ? t('welcoSetup.removing') : t('welcoSetup.remove') }}
                  </button>
                </div>
                <span class="field-hint">{{ t('welcoSetup.logoHint') }}</span>
                <p v-if="uploadingLogo" class="input-hint">{{ t('welcoSetup.uploading') }}</p>
                <p v-if="logoError" class="doc-error">{{ logoError }}</p>
              </div>
              <div class="form-row">
                <label class="form-label">{{ t('welcoSetup.positionLabel') }}</label>
                <select v-model="form.widget_position" class="input">
                  <option value="bottom-right">{{ t('welcoSetup.positionBottomRight') }}</option>
                  <option value="bottom-left">{{ t('welcoSetup.positionBottomLeft') }}</option>
                </select>
              </div>
              <div class="form-actions">
                <button class="btn btn-outline btn-sm" :disabled="savingAppearance" @click="saveAppearance">
                  {{ savingAppearance ? t('welcoSetup.savingEllipsis') : t('welcoSetup.savePosition') }}
                </button>
              </div>
            </template>
            <div v-else class="locked-feature">
              <p class="field-hint">{{ t('welcoSetup.logoLocked') }}</p>
              <router-link v-if="subscriptionId" :to="`/subscriptions/${subscriptionId}/change-plan`" class="btn btn-outline btn-sm">{{ t('welcoSetup.upgradePlan') }}</router-link>
            </div>

            <h4 class="manage-h4">{{ t('welcoSetup.customCss') }}</h4>
            <template v-if="hasEnterpriseTier">
              <p class="field-hint">
                {{ t('welcoSetup.customCssHint') }}
              </p>
              <textarea v-model="form.widget_custom_css" class="input textarea" rows="5" placeholder=".welcochat-example { font-family: inherit; }"></textarea>
              <div class="form-actions">
                <button class="btn btn-outline btn-sm" :disabled="savingAppearance" @click="saveAppearance">
                  {{ savingAppearance ? t('welcoSetup.savingEllipsis') : t('welcoSetup.saveCustomCss') }}
                </button>
              </div>
            </template>
            <div v-else class="locked-feature">
              <p class="field-hint">{{ t('welcoSetup.customCssLocked') }}</p>
              <router-link v-if="subscriptionId" :to="`/subscriptions/${subscriptionId}/change-plan`" class="btn btn-outline btn-sm">{{ t('welcoSetup.upgradePlan') }}</router-link>
            </div>
          </div>

          <div class="manage-section">
            <h3 class="manage-h3">{{ t('welcoSetup.additionalNotes') }}</h3>
            <p class="field-hint">
              {{ t('welcoSetup.immediateEffectHint') }}
              <a href="/guides/prompt-and-content-guide/" target="_blank" rel="noopener">{{ t('welcoSetup.contentGuideLink') }}</a>.
            </p>
            <textarea v-model="form.additional_docs_note" class="input textarea textarea-lg" rows="6" :placeholder="t('welcoSetup.additionalDocsPlaceholder')"></textarea>
            <div class="form-actions">
              <button class="btn btn-outline btn-sm" :disabled="savingNote" @click="saveNote">
                {{ savingNote ? t('welcoSetup.savingEllipsis') : t('welcoSetup.saveNotes') }}
              </button>
              <span v-if="noteSaved" class="draft-saved">{{ t('welcoSetup.saved') }}</span>
            </div>
          </div>

          <div class="manage-section">
            <h3 class="manage-h3">{{ t('welcoSetup.notifications') }}</h3>

            <div class="form-row">
              <label class="form-label">{{ t('welcoSetup.handoffEmail') }}</label>
              <input v-model="form.notification_email" type="email" class="input" placeholder="team@yourcompany.com" />
              <span class="field-hint">{{ t('welcoSetup.handoffEmailHint') }}</span>
            </div>

            <h4 class="manage-h4">{{ t('welcoSetup.slackTeams') }}</h4>
            <template v-if="hasBusinessTier">
              <p class="field-hint">
                {{ t('welcoSetup.slackTeamsIntro') }}
                <a href="/guides/slack-teams-setup/" target="_blank" rel="noopener">{{ t('welcoSetup.slackTeamsGuideLink') }}</a>.
              </p>
              <div class="form-row">
                <label class="form-label">{{ t('welcoSetup.channelLabel') }}</label>
                <select v-model="form.notification_channel_type" class="input">
                  <option value="">{{ t('welcoSetup.channelNone') }}</option>
                  <option value="slack">Slack</option>
                  <option value="teams">Microsoft Teams</option>
                  <option value="generic">{{ t('welcoSetup.channelWebhook') }}</option>
                </select>
              </div>
              <div class="form-row" v-if="form.notification_channel_type">
                <label class="form-label">{{ t('welcoSetup.webhookUrl') }}</label>
                <input v-model="form.notification_webhook_url" class="input" placeholder="https://hooks.slack.com/services/…" />
              </div>
            </template>
            <div v-else class="locked-feature">
              <p class="field-hint">{{ t('welcoSetup.notificationsLocked') }}</p>
              <router-link v-if="subscriptionId" :to="`/subscriptions/${subscriptionId}/change-plan`" class="btn btn-outline btn-sm">{{ t('welcoSetup.upgradePlan') }}</router-link>
            </div>

            <div class="form-actions">
              <button
                v-if="hasBusinessTier && form.notification_channel_type"
                type="button"
                class="btn btn-outline btn-sm"
                :disabled="testingNotification || !form.notification_webhook_url"
                @click="sendTestNotification"
              >
                {{ testingNotification ? t('welcoSetup.sendingEllipsis') : t('welcoSetup.sendTestMessage') }}
              </button>
              <button class="btn btn-outline btn-sm" :disabled="savingNotification" @click="saveNotificationSettings">
                {{ savingNotification ? t('welcoSetup.savingEllipsis') : t('welcoSetup.saveNotificationSettings') }}
              </button>
              <span v-if="notificationSaved" class="draft-saved">{{ t('welcoSetup.saved') }}</span>
            </div>
            <p v-if="notificationTestResult" class="field-hint">{{ notificationTestResult }}</p>
          </div>

          <div class="manage-section">
            <h3 class="manage-h3">WhatsApp</h3>
            <template v-if="hasBusinessTier">
              <p class="field-hint">
                {{ t('welcoSetup.whatsappIntro') }}
              </p>
              <div class="form-row">
                <label class="form-label">{{ t('welcoSetup.twilioSid') }}</label>
                <input v-model="form.whatsapp_account_sid" class="input" placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" />
              </div>
              <div class="form-row">
                <label class="form-label">{{ t('welcoSetup.twilioToken') }}</label>
                <input v-model="form.whatsapp_auth_token" type="password" class="input" :placeholder="t('welcoSetup.twilioTokenPlaceholder')" />
              </div>
              <div class="form-row">
                <label class="form-label">{{ t('welcoSetup.whatsappNumber') }}</label>
                <input v-model="form.whatsapp_number" class="input" placeholder="+14155238886" />
              </div>
              <div class="form-actions">
                <button class="btn btn-outline btn-sm" :disabled="savingWhatsapp" @click="saveWhatsappSettings">
                  {{ savingWhatsapp ? t('welcoSetup.savingEllipsis') : t('welcoSetup.saveWhatsappSettings') }}
                </button>
                <span v-if="whatsappSaved" class="draft-saved">{{ t('welcoSetup.saved') }}</span>
              </div>
              <template v-if="whatsappWebhookUrl">
                <p class="field-hint" style="margin-top:0.9rem;">
                  {{ t('welcoSetup.whatsappWebhookHint') }}
                </p>
                <div class="embed-box">
                  <code>{{ whatsappWebhookUrl }}</code>
                  <button class="btn btn-outline btn-sm" @click="copyWhatsappWebhookUrl">
                    {{ whatsappUrlCopied ? t('welcoSetup.copied') : t('welcoSetup.copy') }}
                  </button>
                </div>
              </template>
            </template>
            <div v-else class="locked-feature">
              <p class="field-hint">{{ t('welcoSetup.whatsappLocked') }}</p>
              <router-link v-if="subscriptionId" :to="`/subscriptions/${subscriptionId}/change-plan`" class="btn btn-outline btn-sm">{{ t('welcoSetup.upgradePlan') }}</router-link>
            </div>
          </div>

          <div class="manage-section">
            <h3 class="manage-h3">{{ t('welcoSetup.documents') }}</h3>
            <input
              ref="fileInputEl"
              type="file"
              multiple
              accept=".pdf,.docx,.txt"
              class="file-input"
              @change="onFilesSelected"
            />
            <span class="field-hint">{{ t('welcoSetup.documentsHintImmediate') }}</span>

            <p v-if="uploadingDocs" class="input-hint">{{ t('welcoSetup.uploading') }}</p>

            <ul v-if="documents.length" class="doc-list">
              <li v-for="doc in documents" :key="doc.id" class="doc-row">
                <span class="doc-name">{{ doc.file_name }}</span>
                <span class="doc-meta">{{ t('welcoSetup.charsCount', { count: doc.char_count ?? 0 }) }}</span>
                <button type="button" class="btn-remove" @click="removeDocument(doc.id)" :aria-label="t('welcoSetup.removeDocument')">✕</button>
              </li>
            </ul>
            <ul v-if="uploadErrors.length" class="doc-errors">
              <li v-for="(err, i) in uploadErrors" :key="i" class="doc-error">{{ err.file_name }}: {{ err.error }}</li>
            </ul>
          </div>
        </template>

        <template v-else-if="welcoStatus === 'error'">
          <div class="confirm-icon confirm-icon-error">!</div>
          <h2 class="confirm-h2">{{ t('welcoSetup.kbFailedTitle') }}</h2>
          <p class="confirm-sub">{{ welcoError || t('welcoSetup.kbFailedDefault') }}</p>

          <div class="manage-section" style="margin-top: 0; padding-top: 0; border-top: none;">
            <h3 class="manage-h3">{{ t('welcoSetup.website') }}</h3>
            <input v-model="form.website_url" class="input" placeholder="https://yourcompany.com" />
            <div class="form-actions">
              <button class="btn btn-primary" :disabled="activating" @click="saveWebsiteAndRecrawl">
                {{ activating ? t('welcoSetup.retrying') : t('welcoSetup.saveAndRetry') }}
              </button>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="confirm-icon confirm-icon-pending">…</div>
          <h2 class="confirm-h2">{{ t('welcoSetup.buildingKb') }}</h2>
          <p class="confirm-sub">
            {{ t('welcoSetup.buildingKbSub') }}
          </p>
        </template>

        <div v-if="welcoStatus === 'ready' || welcoStatus === 'error'" class="confirm-actions">
          <router-link to="/subscriptions" class="btn btn-primary">{{ t('addSub.goToServices') }}</router-link>
          <router-link to="/dashboard" class="btn btn-outline">{{ t('addSub.goToDashboard') }}</router-link>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { getServiceInstances, getSubscriptions, updateInstanceSetup, type ServiceInstance, type Subscription, type ServiceConfiguration } from '@/services/subscriptions'
import {
  activateWelco, getWelcoStatus, getWelcoDocuments, uploadWelcoDocuments, deleteWelcoDocument,
  testWelcoNotification, uploadWelcoLogo, removeWelcoLogo,
  type WelcoDocument, type WelcoDocumentUploadResult,
} from '@/services/welco'

const { t } = useI18n()
const route = useRoute()
const instanceId = computed(() => Number(route.params.id))

const loading = ref(true)
const loadError = ref('')
const error = ref('')
const saving = ref(false)
const draftSaved = ref(false)
const confirmCorrect = ref(false)

const wizardStep = ref(1)
const stepLabels = computed(() => [
  t('welcoSetup.stepOverview'),
  t('welcoSetup.stepConnectContent'),
  t('welcoSetup.stepWidget'),
  t('welcoSetup.stepReviewSetup'),
  t('welcoSetup.stepActivation'),
])
const isManaging = computed(() => wizardStep.value === 5 && welcoStatus.value === 'ready')

const setupStatus = ref('not_configured')
const instanceLabel = ref<string | null>(null)
const instanceTier = ref('Basic')
const subscriptionId = ref<number | null>(null)
const subscription = ref<Subscription | null>(null)
const hasBusinessTier = computed(() => instanceTier.value !== 'Basic')
const hasEnterpriseTier = computed(() => instanceTier.value === 'Enterprise')

const widgetLogoUrl = ref('')
const uploadingLogo = ref(false)
const removingLogo = ref(false)
const logoError = ref('')
const logoInputEl = ref<HTMLInputElement | null>(null)

const form = ref({
  website_url: '',
  additional_docs_note: '',
  widget_name: '',
  widget_color: '#2563eb',
  widget_bg_color: '#ffffff',
  widget_theme: 'light',
  greeting_message: '',
  notification_email: '',
  notification_channel_type: '',
  notification_webhook_url: '',
  whatsapp_account_sid: '',
  whatsapp_auth_token: '',
  whatsapp_number: '',
  widget_position: 'bottom-right',
  widget_custom_css: '',
})

const documents = ref<WelcoDocument[]>([])
const uploadErrors = ref<WelcoDocumentUploadResult[]>([])
const uploadingDocs = ref(false)
const fileInputEl = ref<HTMLInputElement | null>(null)

async function loadDocuments() {
  try {
    documents.value = await getWelcoDocuments(instanceId.value)
  } catch {
    // non-fatal — the rest of the wizard still works without the list
  }
}

async function onFilesSelected(evt: Event) {
  const input = evt.target as HTMLInputElement
  const files = input.files ? Array.from(input.files) : []
  if (files.length === 0) return

  uploadingDocs.value = true
  uploadErrors.value = []
  try {
    const results = await uploadWelcoDocuments(instanceId.value, files)
    uploadErrors.value = results.filter((r) => r.error)
    await loadDocuments()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('welcoSetup.errorUploadDocuments')
  } finally {
    uploadingDocs.value = false
    if (fileInputEl.value) fileInputEl.value.value = ''
  }
}

const savingWidget = ref(false)
const widgetSaved = ref(false)

async function saveWidgetSettings() {
  savingWidget.value = true
  widgetSaved.value = false
  error.value = ''
  try {
    await updateInstanceSetup(instanceId.value, { configuration: buildConfiguration() })
    widgetSaved.value = true
    setTimeout(() => (widgetSaved.value = false), 2000)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('welcoSetup.errorSaveWidgetSettings')
  } finally {
    savingWidget.value = false
  }
}

const savingAppearance = ref(false)
const appearanceSaved = ref(false)

async function saveAppearance() {
  savingAppearance.value = true
  appearanceSaved.value = false
  error.value = ''
  try {
    await updateInstanceSetup(instanceId.value, { configuration: buildConfiguration() })
    appearanceSaved.value = true
    setTimeout(() => (appearanceSaved.value = false), 2000)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('welcoSetup.errorSaveAppearance')
  } finally {
    savingAppearance.value = false
  }
}

async function onLogoSelected(evt: Event) {
  const input = evt.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  uploadingLogo.value = true
  logoError.value = ''
  try {
    widgetLogoUrl.value = await uploadWelcoLogo(instanceId.value, file)
  } catch (err: unknown) {
    logoError.value = err instanceof Error ? err.message : t('welcoSetup.errorUploadLogo')
  } finally {
    uploadingLogo.value = false
    if (logoInputEl.value) logoInputEl.value.value = ''
  }
}

async function onRemoveLogo() {
  removingLogo.value = true
  logoError.value = ''
  try {
    await removeWelcoLogo(instanceId.value)
    widgetLogoUrl.value = ''
  } catch (err: unknown) {
    logoError.value = err instanceof Error ? err.message : t('welcoSetup.errorRemoveLogo')
  } finally {
    removingLogo.value = false
  }
}

const savingNote = ref(false)
const noteSaved = ref(false)

async function saveNote() {
  savingNote.value = true
  noteSaved.value = false
  error.value = ''
  try {
    await updateInstanceSetup(instanceId.value, { configuration: buildConfiguration() })
    noteSaved.value = true
    setTimeout(() => (noteSaved.value = false), 2000)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('welcoSetup.errorSaveNotes')
  } finally {
    savingNote.value = false
  }
}

const savingNotification = ref(false)
const notificationSaved = ref(false)
const testingNotification = ref(false)
const notificationTestResult = ref('')

async function saveNotificationSettings() {
  savingNotification.value = true
  notificationSaved.value = false
  error.value = ''
  try {
    await updateInstanceSetup(instanceId.value, { configuration: buildConfiguration() })
    notificationSaved.value = true
    setTimeout(() => (notificationSaved.value = false), 2000)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('welcoSetup.errorSaveNotificationSettings')
  } finally {
    savingNotification.value = false
  }
}

async function sendTestNotification() {
  testingNotification.value = true
  notificationTestResult.value = ''
  try {
    await testWelcoNotification(instanceId.value, form.value.notification_channel_type, form.value.notification_webhook_url)
    notificationTestResult.value = form.value.notification_channel_type === 'generic'
      ? t('welcoSetup.testSentWebhook')
      : t('welcoSetup.testSentChannel')
  } catch (err: unknown) {
    notificationTestResult.value = err instanceof Error ? err.message : t('welcoSetup.errorSendTestMessage')
  } finally {
    testingNotification.value = false
  }
}

async function removeDocument(docId: number) {
  try {
    await deleteWelcoDocument(instanceId.value, docId)
    documents.value = documents.value.filter((d) => d.id !== docId)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('welcoSetup.errorRemoveDocument')
  }
}

function themeLabel(theme: string): string {
  const map: Record<string, string> = {
    light: t('welcoSetup.themeLight'),
    dark: t('welcoSetup.themeDark'),
    custom: t('welcoSetup.themeCustom'),
  }
  return map[theme] ?? t('welcoSetup.themeLight')
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    not_configured: t('serviceStatus.notConfigured'),
    setup_in_progress: t('serviceStatus.setupInProgress'),
    pending_review: t('serviceStatus.pendingReview'),
    running: t('serviceStatus.running'),
    paused: t('serviceStatus.paused'),
    error: t('subscriptions.needsAttention'),
    cancelled: t('serviceStatus.cancelled'),
  }
  return map[status] ?? status
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
}

function applyConfiguration(config: ServiceConfiguration | null) {
  if (!config) return
  form.value.website_url = (config.website_url as string) ?? ''
  form.value.additional_docs_note = (config.additional_docs_note as string) ?? ''
  form.value.widget_name = (config.widget_name as string) ?? ''
  form.value.widget_color = (config.widget_color as string) || '#2563eb'
  form.value.widget_bg_color = (config.widget_bg_color as string) || '#ffffff'
  const theme = config.widget_theme as string
  form.value.widget_theme = theme === 'dark' || theme === 'custom' ? theme : 'light'
  form.value.greeting_message = (config.greeting_message as string) ?? ''
  form.value.notification_email = (config.notification_email as string) ?? ''
  form.value.notification_channel_type = (config.notification_channel_type as string) ?? ''
  form.value.notification_webhook_url = (config.notification_webhook_url as string) ?? ''
  form.value.whatsapp_account_sid = (config.whatsapp_account_sid as string) ?? ''
  form.value.whatsapp_auth_token = (config.whatsapp_auth_token as string) ?? ''
  form.value.whatsapp_number = (config.whatsapp_number as string) ?? ''
  form.value.widget_position = (config.widget_position as string) || 'bottom-right'
  form.value.widget_custom_css = (config.widget_custom_css as string) ?? ''
  widgetLogoUrl.value = (config.widget_logo_url as string) ?? ''
}

function buildConfiguration(): ServiceConfiguration {
  return { ...form.value }
}

async function startSetup() {
  error.value = ''
  try {
    await updateInstanceSetup(instanceId.value, { setup_status: 'setup_in_progress' })
    setupStatus.value = 'setup_in_progress'
    wizardStep.value = 2
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('welcoSetup.errorStartSetup')
  }
}

async function saveDraft() {
  saving.value = true
  error.value = ''
  draftSaved.value = false
  try {
    await updateInstanceSetup(instanceId.value, { setup_status: 'setup_in_progress', configuration: buildConfiguration() })
    draftSaved.value = true
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('welcoSetup.errorSaveDraft')
  } finally {
    saving.value = false
  }
}

const welcoStatus = ref('pending')
const welcoPageCount = ref<number | null>(null)
const welcoError = ref('')
const embedSnippet = ref('')
const whatsappWebhookUrl = ref('')
const activating = ref(false)
const copied = ref(false)
const whatsappUrlCopied = ref(false)
let pollTimer: ReturnType<typeof setInterval> | null = null

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const status = await getWelcoStatus(instanceId.value, true)
      welcoStatus.value = status.status
      welcoPageCount.value = status.page_count
      welcoError.value = status.error_message || ''
      embedSnippet.value = status.embed_snippet || ''
      whatsappWebhookUrl.value = status.whatsapp_webhook_url || ''
      if (status.status === 'ready' || status.status === 'error') stopPolling()
    } catch {
      // transient poll failure, keep trying until the interval is stopped
    }
  }, 3000)
}

async function activateAndWatch() {
  activating.value = true
  try {
    const status = await activateWelco(instanceId.value)
    welcoStatus.value = status.status
    welcoError.value = ''
    whatsappWebhookUrl.value = status.whatsapp_webhook_url || ''
    wizardStep.value = 5
    if (status.status !== 'ready' && status.status !== 'error') startPolling()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('welcoSetup.errorActivate')
  } finally {
    activating.value = false
  }
}

async function saveWebsiteAndRecrawl() {
  if (!form.value.website_url.trim()) {
    error.value = t('welcoSetup.errorWebsiteRequired')
    return
  }
  error.value = ''
  try {
    await updateInstanceSetup(instanceId.value, { configuration: buildConfiguration() })
    await activateAndWatch()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('welcoSetup.errorSaveWebsite')
  }
}

function copyEmbedSnippet() {
  navigator.clipboard.writeText(embedSnippet.value).then(() => {
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  })
}

function copyWhatsappWebhookUrl() {
  navigator.clipboard.writeText(whatsappWebhookUrl.value).then(() => {
    whatsappUrlCopied.value = true
    setTimeout(() => (whatsappUrlCopied.value = false), 2000)
  })
}

const savingWhatsapp = ref(false)
const whatsappSaved = ref(false)

async function saveWhatsappSettings() {
  savingWhatsapp.value = true
  whatsappSaved.value = false
  error.value = ''
  try {
    await updateInstanceSetup(instanceId.value, { configuration: buildConfiguration() })
    whatsappSaved.value = true
    setTimeout(() => (whatsappSaved.value = false), 2000)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('welcoSetup.errorSaveWhatsapp')
  } finally {
    savingWhatsapp.value = false
  }
}

async function submitForActivation() {
  saving.value = true
  error.value = ''
  try {
    await updateInstanceSetup(instanceId.value, { setup_status: 'pending_review', configuration: buildConfiguration() })
    setupStatus.value = 'pending_review'
    await activateAndWatch()
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : t('welcoSetup.errorSubmitSetup')
  } finally {
    saving.value = false
  }
}

onUnmounted(stopPolling)

onMounted(async () => {
  loading.value = true
  loadError.value = ''
  try {
    const [instances, subs]: [ServiceInstance[], Subscription[]] = await Promise.all([
      getServiceInstances(), getSubscriptions(),
    ])
    const inst = instances.find((i) => i.id === instanceId.value)
    if (!inst) {
      loadError.value = t('welcoSetup.errorInstanceNotFound')
      return
    }
    if (inst.service_key !== 'welco') {
      loadError.value = t('welcoSetup.errorWrongWizard')
      return
    }
    setupStatus.value = inst.setup_status
    applyConfiguration(inst.configuration)
    instanceLabel.value = inst.service_name
    instanceTier.value = inst.tier
    subscriptionId.value = inst.subscription_id
    subscription.value = subs.find((s) => s.id === inst.subscription_id) ?? null
    loadDocuments()
    if (['pending_review', 'running', 'error'].includes(inst.setup_status)) {
      wizardStep.value = 5
      const status = await getWelcoStatus(instanceId.value)
      welcoStatus.value = status.status
      welcoPageCount.value = status.page_count
      welcoError.value = status.error_message || ''
      embedSnippet.value = status.embed_snippet || ''
      whatsappWebhookUrl.value = status.whatsapp_webhook_url || ''
      if (status.status !== 'ready' && status.status !== 'error') startPolling()
    } else if (inst.setup_status !== 'not_configured') {
      wizardStep.value = 2
    }
  } catch (err: unknown) {
    loadError.value = err instanceof Error ? err.message : t('welcoSetup.errorLoadSetup')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stepper { display: flex; gap: 0; margin: 1.25rem 0 2rem; overflow-x: auto; }
.stepper-item { display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 60px; gap: 0.35rem; position: relative; }
.stepper-item + .stepper-item::before {
  content: ''; position: absolute; top: 14px; right: 50%; width: 100%; height: 2px;
  background: rgba(148, 163, 184, 0.25); z-index: 0;
}
.stepper-item.is-done + .stepper-item::before { background: var(--primary, #2563eb); }
.stepper-dot {
  width: 28px; height: 28px; border-radius: 50%; border: 2px solid rgba(148, 163, 184, 0.35);
  display: flex; align-items: center; justify-content: center; font-size: 0.78rem; font-weight: 700;
  background: var(--surface, #1e293b); position: relative; z-index: 1;
}
.stepper-item.is-active .stepper-dot { border-color: var(--primary, #2563eb); color: var(--primary, #2563eb); }
.stepper-item.is-done .stepper-dot { border-color: var(--primary, #2563eb); background: var(--primary, #2563eb); color: #fff; }
.stepper-label { font-size: 0.7rem; color: rgba(148, 163, 184, 0.7); text-align: center; white-space: nowrap; }
.stepper-item.is-active .stepper-label { color: var(--primary, #2563eb); font-weight: 600; }

.order-section { max-width: 760px; }
.step-subtitle { color: rgba(148, 163, 184, 0.85); margin: 0.25rem 0 1.25rem; }
.back-btn { background: none; border: 0; color: var(--blue-2, #60a5fa); cursor: pointer; font: inherit; padding: 0; margin-bottom: 1rem; }

.billing-form { display: flex; flex-direction: column; gap: 0; max-width: 520px; }
.form-row { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 1rem; }
.form-label { font-size: 0.85rem; font-weight: 600; }
.section-h3 { font-size: 0.95rem; margin: 0.5rem 0 0.9rem; padding-top: 1.25rem; border-top: 1px solid rgba(148, 163, 184, 0.2); }
.req { color: #f87171; }
.input {
  width: 100%; box-sizing: border-box;
  padding: 0.55rem 0.75rem; border-radius: 6px; border: 1px solid rgba(148, 163, 184, 0.3);
  background: rgba(30, 41, 59, 0.6); color: inherit; font: inherit; font-size: 0.9rem;
}
.color-input { width: 64px; padding: 0.25rem; height: 38px; cursor: pointer; }
.textarea { resize: vertical; }
.textarea-lg { min-height: 9rem; }
.field-hint { font-size: 0.78rem; color: rgba(148, 163, 184, 0.7); }
.field-hint a { color: var(--blue-2, #60a5fa); text-decoration: underline; }

.file-input { font-size: 0.85rem; }
.doc-list { list-style: none; padding: 0; margin: 0.6rem 0 0; display: flex; flex-direction: column; gap: 0.4rem; }
.doc-row {
  display: flex; align-items: center; gap: 0.6rem; padding: 0.4rem 0.6rem;
  border: 1px solid rgba(148, 163, 184, 0.25); border-radius: 6px; font-size: 0.85rem;
}
.doc-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.doc-meta { color: rgba(148, 163, 184, 0.7); font-size: 0.78rem; flex-shrink: 0; }
.doc-errors { list-style: none; padding: 0; margin: 0.6rem 0 0; display: flex; flex-direction: column; gap: 0.3rem; }
.doc-error { font-size: 0.8rem; color: #f87171; }
.btn-remove {
  background: transparent; border: 1px solid rgba(148, 163, 184, 0.3); color: rgba(148, 163, 184, 0.8);
  border-radius: 6px; width: 26px; height: 26px; flex-shrink: 0; cursor: pointer; font-size: 0.8rem;
}
.btn-remove:hover { color: #f87171; border-color: rgba(239, 68, 68, 0.4); }
.form-actions { margin-top: 0.5rem; display: flex; gap: 0.75rem; flex-wrap: wrap; }
.form-error { color: #f87171; margin-bottom: 1rem; font-size: 0.9rem; }
.draft-saved { color: #4ade80; font-size: 0.85rem; margin-top: 0.75rem; }

.review-h2 { font-size: 1.1rem; margin: 0 0 1rem; }
.review-block { border: 1px solid rgba(148, 163, 184, 0.2); border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
.review-block-title { font-weight: 700; font-size: 0.85rem; color: rgba(148, 163, 184, 0.8); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.6rem; }
.review-row { display: flex; justify-content: space-between; gap: 1rem; font-size: 0.88rem; padding: 0.2rem 0; }
.review-row span { color: rgba(148, 163, 184, 0.8); }
.review-next { font-size: 0.85rem; color: rgba(148, 163, 184, 0.85); margin: 0.4rem 0 1rem; }
.review-checks { display: flex; flex-direction: column; gap: 0.6rem; margin: 1rem 0; }

.confirm-icon { font-size: 2.5rem; color: #4ade80; margin-bottom: 0.5rem; }
.confirm-icon-error { color: #f87171; }
.confirm-icon-pending { color: #60a5fa; }
.confirm-h2 { font-size: 1.3rem; margin: 0 0 0.4rem; }
.confirm-sub { color: rgba(148, 163, 184, 0.85); margin: 0 0 1.25rem; max-width: 560px; }
.confirm-actions { display: flex; flex-wrap: wrap; gap: 0.75rem; margin-top: 1.25rem; }
.embed-box {
  display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;
  background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 8px; padding: 0.75rem 1rem; max-width: 640px; margin-bottom: 1rem;
}
.embed-box code { flex: 1; min-width: 220px; font-size: 0.8rem; word-break: break-all; }
.btn-sm { padding: 0.35rem 0.7rem; font-size: 0.78rem; }
.manage-section { text-align: left; margin-top: 1.75rem; padding-top: 1.5rem; border-top: 1px solid rgba(148, 163, 184, 0.2); }
.manage-h3 { font-size: 0.95rem; margin: 0 0 0.3rem; }
.manage-h4 { font-size: 0.85rem; margin: 1.25rem 0 0.6rem; padding-top: 1rem; border-top: 1px solid rgba(148, 163, 184, 0.15); color: rgba(148, 163, 184, 0.9); }
.locked-feature { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
.locked-feature .field-hint { margin: 0; }
.logo-row { display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap; }
.logo-preview { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 1px solid rgba(148, 163, 184, 0.3); }

.empty-state { margin-top: 1rem; }
.empty-text { color: rgba(148, 163, 184, 0.85); margin-bottom: 1rem; }

.btn { display: inline-flex; align-items: center; justify-content: center; padding: 0.55rem 1.1rem; border-radius: 6px; font: inherit; font-weight: 600; font-size: 0.88rem; cursor: pointer; border: 1px solid transparent; text-decoration: none; transition: opacity 0.15s; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--primary, #2563eb); color: #fff; }
.btn-outline { background: transparent; border-color: rgba(148, 163, 184, 0.4); color: inherit; }

@media (max-width: 600px) {
  .stepper-label { display: none; }
  .confirm-actions, .form-actions { flex-direction: column; }
}
</style>
