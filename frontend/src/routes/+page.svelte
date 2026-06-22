<script>
  import '../app.css';
  import { onDestroy, onMount } from 'svelte';
  import { base } from '$app/paths';
  import { lang, t } from '$lib/i18n';
  import ResultCard from '$lib/ResultCard.svelte';
  import {
    PROVIDERS,
    clearProviderSettings,
    getActiveProviderKey,
    getProviderLabel,
    loadProviderSettings,
    maskApiKey,
    normalizeProviderSettings,
    saveProviderSettings
  } from '$lib/providerSettings';

  let scenario = '';
  let location = '';
  let imageInput;
  let selectedImages = [];
  let loading = false;
  let exportingPdf = false;
  let result = null;
  let error = '';
  let pdfNotice = '';
  const MAX_IMAGES = 4;

  let provider = PROVIDERS.local;
  let openaiApiKey = '';
  let anthropicApiKey = '';
  let rememberProviderKey = false;
  let providerNotice = '';
  let providerLabel = '';
  let keySummary = '';
  let storageLabel = '';

  function buildRecommendedFollowUp(level) {
    const normalized = String(level ?? '').toLowerCase();

    if (normalized === 'high') {
      return [$t('action_high_1'), $t('action_high_2'), $t('action_high_3')];
    }

    if (normalized === 'medium') {
      return [$t('action_medium_1'), $t('action_medium_2'), $t('action_medium_3')];
    }

    return [$t('action_low_1'), $t('action_low_2'), $t('action_low_3')];
  }

  function appendPdfFields(form, currentResult) {
    form.append('scenario', scenario);
    form.append('location', location);
    form.append('provider', provider);
    form.append('report_locale', $lang);
    form.append('report_title', 'Prototype Health Risk Assessment Report');
    form.append('model_version', currentResult.model_version ?? 'v1_2_multimodal_sbert_svm_candidate');
    form.append('original_input', currentResult.original_input ?? '');
    form.append('detected_language', currentResult.detected_language ?? '');
    form.append('translated_model_input', currentResult.translated_model_input ?? currentResult.final_model_input ?? '');
    form.append('predicted_hazard_category', currentResult.predicted_hazard_category ?? '');
    form.append('predicted_risk_level', currentResult.predicted_risk_level ?? '');
    form.append('sub_hazard', currentResult.sub_hazard ?? '');
    form.append('hazard_confidence', String(currentResult.hazard_confidence ?? ''));
    form.append('hazard_confidence_percent', currentResult.hazard_confidence_percent ?? '');
    form.append('risk_confidence', String(currentResult.risk_confidence ?? ''));
    form.append('risk_confidence_percent', currentResult.risk_confidence_percent ?? '');
    form.append('overall_confidence', String(currentResult.overall_confidence ?? ''));
    form.append('overall_confidence_percent', currentResult.overall_confidence_percent ?? '');
    form.append('overall_confidence_label', currentResult.overall_confidence_label ?? '');
    form.append('hazard_probabilities', JSON.stringify(currentResult.hazard_probabilities ?? []));
    form.append('risk_probabilities', JSON.stringify(currentResult.risk_probabilities ?? []));
    form.append('confidence_note', currentResult.confidence_note ?? '');
    form.append('urgency', currentResult.urgency ?? '');
    form.append('risk_method', currentResult.risk_method ?? '');
    form.append('image_caption_status', currentResult.image_caption_status ?? '');
    form.append('image_caption_model', currentResult.image_caption_model ?? '');
    form.append('image_caption_warning', currentResult.image_caption_warning ?? '');
    form.append('decision_support_recommendation', currentResult.decision_support_recommendation ?? '');
    form.append('recommendation', currentResult.recommendation ?? '');
    form.append('suggested_follow_up_steps', JSON.stringify(currentResult.suggested_follow_up_steps ?? []));
    form.append('corrective_action_plan', JSON.stringify(currentResult.corrective_action_plan ?? {}));
    form.append('recommended_follow_up', buildRecommendedFollowUp(currentResult.predicted_risk_level).join('\n'));
    form.append('safety_note', $t('safety_note'));
    form.append('image_caption', currentResult.image_caption ?? '');
    form.append('final_model_input', currentResult.final_model_input_v1_2 ?? currentResult.final_model_input ?? '');

    if (selectedImages[0]) {
      form.append('image', selectedImages[0].file);
    }
  }

  onMount(() => {
    const saved = loadProviderSettings();
    const normalized = normalizeProviderSettings(saved);

    provider = normalized.provider;
    openaiApiKey = normalized.openaiApiKey;
    anthropicApiKey = normalized.anthropicApiKey;
    rememberProviderKey = normalized.remember;
    providerNotice = $t('provider_settings_loaded');
  });

  function clearSelectedImages() {
    for (const item of selectedImages) {
      URL.revokeObjectURL(item.url);
    }

    selectedImages = [];

    if (imageInput) {
      imageInput.value = '';
    }
  }

  function onFileChange(e) {
    const files = Array.from(e.currentTarget.files ?? []);

    if (files.length > MAX_IMAGES) {
      error = $t('max_images_error');
      if (imageInput) {
        imageInput.value = '';
      }
      return;
    }

    clearSelectedImages();
    selectedImages = files.map((file) => ({
      file,
      name: file.name,
      url: URL.createObjectURL(file)
    }));
    error = '';
  }

  $: providerLabel = getProviderLabel(provider, $t);
  $: keySummary = maskApiKey(getActiveProviderKey({ provider, openaiApiKey, anthropicApiKey }));
  $: storageLabel = rememberProviderKey ? $t('provider_storage_local') : $t('provider_storage_session');

  function removeSelectedImage(index) {
    const item = selectedImages[index];
    if (!item) return;

    URL.revokeObjectURL(item.url);
    selectedImages = selectedImages.filter((_, itemIndex) => itemIndex !== index);

    if (imageInput) {
      imageInput.value = '';
    }
  }

  onDestroy(() => {
    clearSelectedImages();
  });

  function buildProviderSettings() {
    return normalizeProviderSettings({
      provider,
      openaiApiKey,
      anthropicApiKey,
      remember: rememberProviderKey
    });
  }

  function saveKeys() {
    const normalized = buildProviderSettings();
    saveProviderSettings(normalized);
    providerNotice = normalized.remember ? $t('provider_settings_saved_persistent') : $t('provider_settings_saved_session');
  }

  function clearKeys() {
    clearProviderSettings();
    provider = PROVIDERS.local;
    openaiApiKey = '';
    anthropicApiKey = '';
    rememberProviderKey = false;
    providerNotice = $t('provider_settings_cleared');
  }

  async function submit() {
    pdfNotice = '';
    result = null;
    error = '';

    if (!scenario.trim()) {
      error = $t('required_scenario_error');
      return;
    }

    const normalizedScenario = scenario.trim().normalize('NFC');
    const scenarioWords = normalizedScenario.split(/\s+/u).filter(Boolean).length;
    const scenarioChars = Array.from(normalizedScenario).length;

    if (scenarioWords < 3 || scenarioChars < 15) {
      error = $t('scenario_too_short_error');
      return;
    }

    if (selectedImages.length > MAX_IMAGES) {
      error = $t('max_images_error');
      return;
    }

    loading = true;

    try {
      const form = new FormData();
      form.append('scenario', scenario);
      if (location.trim()) form.append('location', location);
      for (const item of selectedImages) {
        form.append('images', item.file);
      }
      form.append('provider', provider);

      const res = await fetch('/api/chat', { method: 'POST', body: form });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      result = data;
    } catch (e) {
      error = String(e?.message || e);
    } finally {
      loading = false;
    }
  }

  async function downloadResultPdf() {
    if (!result) {
      return;
    }

    pdfNotice = '';
    exportingPdf = true;

    try {
      const form = new FormData();
      appendPdfFields(form, result);

      const response = await fetch('/api/result-pdf', {
        method: 'POST',
        body: form
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = 'hazard-chatbot-report.pdf';
      link.rel = 'noopener';
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      pdfNotice = $t('export_pdf_success');
    } catch (e) {
      pdfNotice = String(e?.message || e || $t('export_pdf_error'));
    } finally {
      exportingPdf = false;
    }
  }

  function backToQuestionnaire() {
    // When embedded in the questionnaire's "Try Chatbot" tab (an iframe), ask the parent
    // page to switch to the questionnaire tab instead of navigating the iframe itself —
    // navigating it would load the questionnaire INSIDE the chatbot iframe (nesting).
    if (window.self !== window.top) {
      try {
        window.parent.postMessage({ type: 'open-questionnaire-tab' }, window.location.origin);
        return;
      } catch (e) {
        /* cross-origin or blocked — fall through to a full top-level navigation */
      }
    }
    window.location.assign('/questionnaire/');
  }
</script>

<main id="main" class="page-grid">
  <div class="stack">
    <section class="hero">
      <p class="hero__eyebrow">{$t('hero_eyebrow')}</p>
      <h2 class="hero__title">
        {$t('hero_title_prefix')} <span>{$t('hero_title_emphasis')}</span>
      </h2>
      <p class="hero__body">{$t('hero_body')}</p>

      <div class="hero__signals" aria-label="Platform highlights">
        <span class="chip">{$t('signal_risk')}</span>
        <span class="chip">{$t('signal_caption')}</span>
        <span class="chip">{$t('signal_logging')}</span>
      </div>
    </section>

    <section class="panel">
      <div class="panel__header">
        <div>
          <h3 class="panel__title">{$t('form_title')}</h3>
          <p class="panel__subtitle">{$t('form_subtitle')}</p>
        </div>
        <span class="soft-pill">{$t('form_sla')}</span>
      </div>

      <div class="form-grid">
        <div class="field">
          <label for="scenario">{$t('scenario_label')}</label>
          <textarea
            id="scenario"
            bind:value={scenario}
            rows="6"
            placeholder={$t('scenario_placeholder')}
          ></textarea>
          <p class="hint">{$t('scenario_hint')}</p>
        </div>

        <div class="field">
          <label for="location">{$t('location_label')}</label>
          <input id="location" bind:value={location} placeholder={$t('location_placeholder')} />
          <p class="hint">{$t('location_hint')}</p>
        </div>

        <div class="field">
          <label for="image">{$t('image_label')}</label>
          <input
            id="image"
            bind:this={imageInput}
            class="file-input"
            type="file"
            accept="image/*"
            multiple
            on:change={onFileChange}
          />
          <p class="hint">{$t('image_hint')}</p>

          {#if selectedImages.length}
            <div class="preview-list">
              {#each selectedImages as image, index}
                <figure class="preview-card">
                  <img class="preview-card__image" src={image.url} alt={`${$t('photo_preview_alt')} ${index + 1}`} />
                  <figcaption class="preview-card__body">
                    <div>
                      <p class="preview-card__label">{$t('photo_preview_label')} {index + 1}</p>
                      <p class="preview-card__name">{image.name}</p>
                    </div>
                    <button class="preview-card__remove" type="button" on:click={() => removeSelectedImage(index)}>
                      {$t('remove_photo')}
                    </button>
                  </figcaption>
                </figure>
              {/each}
            </div>
            <p class="hint">{$t('photo_preview_note')}</p>
          {/if}
        </div>

        {#if error}
          <div class="error-banner" aria-live="polite">{error}</div>
        {/if}

        <div class="privacy-notice" aria-label={$t('privacy_notice_title')}>
          <p class="metric__label">{$t('privacy_notice_title')}</p>
          <p class="privacy-notice__intro">{$t('privacy_notice_intro')}</p>
          <ul class="privacy-notice__list">
            <li>{$t('privacy_notice_item_1')}</li>
            <li>{$t('privacy_notice_item_2')}</li>
            <li>{$t('privacy_notice_item_3')}</li>
            <li>{$t('privacy_notice_item_4')}</li>
            <li>{$t('privacy_notice_item_5')}</li>
          </ul>
          <a class="privacy-notice__link" href={base + '/data-privacy'} target="_blank" rel="noopener">{$t('privacy_notice_link')}</a>
        </div>

        <div class="action-row">
          <button class="primary-btn" on:click={submit} disabled={loading}>
            {#if loading}
              <span class="primary-btn__spinner" aria-hidden="true"></span>
              {$t('analyzing_text')}
            {:else}
              {$t('submit_button')}
            {/if}
          </button>
          <p class="support-text">{$t('form_support')}</p>
        </div>

        <p class="footer-note">{$t('safety_note')}</p>
      </div>
    </section>

    {#if result}
      <ResultCard {result} />

      <div class="action-row action-row--pdf">
        <button class="secondary-btn" type="button" on:click={downloadResultPdf} disabled={exportingPdf}>
          {#if exportingPdf}
            <span class="primary-btn__spinner" aria-hidden="true"></span>
            {$t('export_pdf_loading')}
          {:else}
            {$t('export_pdf_button')}
          {/if}
        </button>
        <button class="ghost-btn" type="button" on:click={backToQuestionnaire}>
          {$t('back_to_questionnaire_button')}
        </button>
        <p class="support-text">{$t('export_pdf_note')}</p>
      </div>

      {#if pdfNotice}
        <p class="footer-note" aria-live="polite">{pdfNotice}</p>
      {/if}
    {/if}
  </div>

  <aside class="sidecard">
    <section class="provider-card">
      <div class="provider-card__header">
        <div>
          <p class="metric__label">{$t('provider_settings_label')}</p>
          <h3 class="provider-card__title">{$t('provider_settings_title')}</h3>
          <p class="provider-card__text">{$t('provider_settings_subtitle')}</p>
        </div>
        <span class="soft-pill">{providerLabel}</span>
      </div>

      <div class="field">
        <label for="provider">{$t('provider_select_label')}</label>
        <select id="provider" bind:value={provider}>
          <option value={PROVIDERS.local}>{$t('provider_local')}</option>
          <option value={PROVIDERS.openai}>{$t('provider_openai')}</option>
          <option value={PROVIDERS.anthropic}>{$t('provider_anthropic')}</option>
        </select>
        <p class="hint">{$t('provider_select_hint')}</p>
      </div>

      <div class="field">
        <label for="openai-key">{$t('provider_openai_key_label')}</label>
        <input
          id="openai-key"
          type="password"
          autocomplete="off"
          spellcheck="false"
          bind:value={openaiApiKey}
          placeholder={$t('provider_key_placeholder')}
        />
      </div>

      <div class="field">
        <label for="anthropic-key">{$t('provider_anthropic_key_label')}</label>
        <input
          id="anthropic-key"
          type="password"
          autocomplete="off"
          spellcheck="false"
          bind:value={anthropicApiKey}
          placeholder={$t('provider_key_placeholder')}
        />
      </div>

      <label class="remember-toggle" for="remember-key">
        <input id="remember-key" type="checkbox" bind:checked={rememberProviderKey} />
        <span>
          <strong>{$t('provider_remember_label')}</strong>
          <small>{$t('provider_remember_hint')}</small>
        </span>
      </label>

      <div class="provider-card__summary">
        <div>
          <p class="metric__label">{$t('provider_key_status_label')}</p>
          <p class="metric__value">{keySummary || $t('provider_key_empty')}</p>
          <p class="metric__text">{storageLabel}</p>
        </div>
      </div>

      <div class="provider-card__actions">
        <button class="secondary-btn" type="button" on:click={saveKeys}>{$t('provider_save_button')}</button>
        <button class="ghost-btn" type="button" on:click={clearKeys}>{$t('provider_clear_button')}</button>
      </div>

      {#if providerNotice}
        <p class="provider-card__notice" aria-live="polite">{providerNotice}</p>
      {/if}

      <p class="provider-card__note">{$t('provider_settings_note')}</p>
      <p class="provider-card__note">{$t('privacy_provider_note')}</p>
    </section>

    <div class="sidecard__metric">
      <p class="metric__label">{$t('side_metric_label')}</p>
      <p class="metric__value">{$t('side_metric_value')}</p>
      <p class="metric__text">{$t('side_metric_text')}</p>
    </div>

    <div>
      <p class="metric__label">{$t('workflow_label')}</p>
      <div class="steps">
        <div class="step">
          <div class="step__num">1</div>
          <div>
            <p class="step__title">{$t('workflow_step_1_title')}</p>
            <p class="step__text">{$t('workflow_step_1_text')}</p>
          </div>
        </div>
        <div class="step">
          <div class="step__num">2</div>
          <div>
            <p class="step__title">{$t('workflow_step_2_title')}</p>
            <p class="step__text">{$t('workflow_step_2_text')}</p>
          </div>
        </div>
        <div class="step">
          <div class="step__num">3</div>
          <div>
            <p class="step__title">{$t('workflow_step_3_title')}</p>
            <p class="step__text">{$t('workflow_step_3_text')}</p>
          </div>
        </div>
      </div>
    </div>
  </aside>
</main>
