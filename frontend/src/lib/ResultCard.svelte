<script>
  import { t } from '$lib/i18n';
  export let result;
  export let exportingPdf = false;
  export let onExportPdf = null;

  $: riskLevel = String(result?.predicted_risk_level ?? '').toLowerCase();
  $: riskClass = riskLevel === 'high' ? 'risk-badge--high' : riskLevel === 'medium' ? 'risk-badge--medium' : 'risk-badge--low';
  $: auditLabel = result?.logged ? $t('audit_logged') : $t('audit_not_logged');
  $: manualReview = Boolean(result?.manual_review_flag);
  $: needsMoreInfo = Boolean(result?.needs_more_information);
  $: correctivePlan = result?.corrective_action_plan ?? null;
  $: isGerman = String(result?.detected_language ?? '').toLowerCase().startsWith('de');
  $: followUpItems = Array.isArray(result?.suggested_follow_up_steps) && result.suggested_follow_up_steps.length > 0
    ? result.suggested_follow_up_steps.slice(0, 3)
    : actionItems(riskLevel);

  const actionItems = (level) => {
    if (level === 'high') {
      return [$t('action_high_1'), $t('action_high_2'), $t('action_high_3')];
    }
    if (level === 'medium') {
      return [$t('action_medium_1'), $t('action_medium_2'), $t('action_medium_3')];
    }
    return [$t('action_low_1'), $t('action_low_2'), $t('action_low_3')];
  };

  const planValue = (key) => correctivePlan?.[key] ?? '';

  const hazardLabel = (value) => {
    if (!isGerman) return value;
    const text = String(value ?? '').toLowerCase();
    if (text.includes('electrical')) return 'Elektrische Gefährdung';
    if (text.includes('fire')) return 'Brandgefahr';
    if (text.includes('obstruction')) return 'Blockade';
    if (text.includes('slip') || text.includes('trip')) return 'Rutsch-/Stolpergefahr';
    if (text.includes('ergonomic')) return 'Ergonomische Gefährdung';
    if (text.includes('visibility')) return 'Sichtgefährdung';
    return value;
  };

  const riskLabel = (value) => {
    if (!isGerman) return value;
    const text = String(value ?? '').toLowerCase();
    if (text === 'high') return 'Hoch';
    if (text === 'medium') return 'Mittel';
    if (text === 'low') return 'Niedrig';
    return value;
  };

  const imageIncludedLabel = (status) => (String(status ?? '') === 'Not available' ? $t('no_label') : $t('yes_label'));
</script>

<article class="result-card">
  <div class="result-card__header">
    <div>
      <h2 class="result-card__title">{$t('prediction_heading')}</h2>
      <p class="result-card__subtitle">{$t('result_subtitle')}</p>
    </div>

    <div class="result-card__header-actions">
      <span class={`risk-badge ${riskClass}`}>
        {riskLabel(result.predicted_risk_level) || $t('risk_unknown')}
      </span>

      {#if onExportPdf}
        <button class="secondary-btn secondary-btn--tight" type="button" on:click={onExportPdf} disabled={exportingPdf}>
          {#if exportingPdf}
            <span class="primary-btn__spinner" aria-hidden="true"></span>
            {$t('export_pdf_loading')}
          {:else}
            {$t('export_pdf_button')}
          {/if}
        </button>
      {/if}
    </div>
  </div>

  <div class="result-card__summary">
    <div class="summary-stat">
      <p class="summary-stat__label">{$t('predicted_hazard_category_label')}</p>
      <p class="summary-stat__value">{hazardLabel(result.predicted_hazard_category)}</p>
      <p class="summary-stat__confidence">{$t('confidence_label')} {result.hazard_confidence_percent ?? '—'}</p>
    </div>

    <div class="summary-stat">
      <p class="summary-stat__label">{$t('predicted_risk_level_label')}</p>
      <p class="summary-stat__value">{riskLabel(result.predicted_risk_level)}</p>
      {#if result.risk_method}
        <p class="summary-stat__confidence">{$t('risk_method_short_label')} {result.risk_method}</p>
      {/if}
    </div>

    <div class="summary-stat">
      <p class="summary-stat__label">{$t('audit_status_label')}</p>
      <p class="summary-stat__value">{auditLabel}</p>
      {#if manualReview}
        <p class="review-box__flag">{$t('review_flag_label')}</p>
      {/if}
      {#if needsMoreInfo}
        <p class="review-box__flag review-box__flag--info">{$t('needs_more_info_label')}</p>
      {/if}
    </div>
  </div>

  <div class="result-grid">
    <div class="result-item result-item--full">
      <p class="result-item__label">{$t('decision_support_recommendation_label')}</p>
      <p class="result-item__value">{result.decision_support_recommendation}</p>
    </div>

    {#if result.sub_hazard || result.risk_method}
      <div class="result-item result-item--full review-box">
        <p class="result-item__label">{$t('assessment_details_label')}</p>
        {#if result.sub_hazard}
          <p class="result-item__label">{$t('sub_hazard_label')}</p>
          <p class="result-item__value">{result.sub_hazard}</p>
        {/if}

        {#if result.risk_method}
          <p class="result-item__label">{$t('risk_method_label')}</p>
          <p class="result-item__value">{result.risk_method}</p>
        {/if}
      </div>
    {/if}

    {#if correctivePlan}
      <div class="result-item result-item--full corrective-plan">
        <p class="result-item__label">{$t('corrective_action_plan_heading')}</p>

        <div class="plan-grid">
          <div class="plan-card">
            <span class="plan-card__label">{$t('hazard_specific_finding_label')}</span>
            <p>{planValue('hazard_specific_finding')}</p>
          </div>
          <div class="plan-card">
            <span class="plan-card__label">{$t('immediate_containment_label')}</span>
            <p>{planValue('immediate_containment')}</p>
          </div>
          <div class="plan-card">
            <span class="plan-card__label">{$t('corrective_action_label')}</span>
            <p>{planValue('corrective_action')}</p>
          </div>
          <div class="plan-card">
            <span class="plan-card__label">{$t('responsible_owner_label')}</span>
            <p>{planValue('responsible_owner')}</p>
          </div>
          <div class="plan-card">
            <span class="plan-card__label">{$t('target_completion_label')}</span>
            <p>{planValue('target_completion')}</p>
          </div>
          <div class="plan-card">
            <span class="plan-card__label">{$t('verification_label')}</span>
            <p>{planValue('verification')}</p>
          </div>
          <div class="plan-card">
            <span class="plan-card__label">{$t('escalation_label')}</span>
            <p>{planValue('escalation')}</p>
          </div>
          <div class="plan-card">
            <span class="plan-card__label">{$t('closure_condition_label')}</span>
            <p>{planValue('closure_condition')}</p>
          </div>
        </div>

        {#if planValue('manual_review_note')}
          <div class="plan-note">
            <span>{$t('manual_review_note_label')}</span>
            <p>{planValue('manual_review_note')}</p>
          </div>
        {/if}
      </div>
    {/if}

    <div class="result-item result-item--full review-box">
      <p class="result-item__label">{$t('image_included_label')}</p>
      <p class="result-item__value">{imageIncludedLabel(result.image_caption_status)}</p>

      <p class="result-item__label">{$t('image_caption_label')}</p>
      <p class="result-item__value">{result.image_caption || '—'}</p>
    </div>

    <div class="result-item result-item--full">
      <p class="result-item__label">{$t('recommended_follow_up')}</p>
      <ul class="result-list">
        {#each followUpItems as item}
          <li>{item}</li>
        {/each}
      </ul>
    </div>

    {#if result.confidence_note}
      <div class="result-item result-item--full">
        <p class="result-item__label">{$t('confidence_note_label')}</p>
        <p class="result-item__value">{result.confidence_note}</p>
      </div>
    {/if}

    {#if result.clarification_question || result.model_version}
      <div class="result-item result-item--full review-box">
        <p class="result-item__label">{$t('model_version_label')}</p>
        <p class="result-item__value">{result.model_version ?? '—'}</p>

        {#if result.clarification_question}
          <p class="result-item__label">{$t('clarification_question_label')}</p>
          <p class="result-item__value">{result.clarification_question}</p>
        {/if}
      </div>
    {/if}
  </div>

  <div class="result-note">{$t('safety_note')}</div>
</article>

<style>
  .summary-stat__confidence {
    margin: 0.35rem 0 0;
    font-size: 0.9rem;
    color: #667085;
  }

  .review-box {
    border: 1px solid rgba(245, 158, 11, 0.28);
    background: rgba(255, 251, 235, 0.92);
  }

  .review-box__flag {
    margin: 0.6rem 0 0;
    display: inline-flex;
    align-items: center;
    width: fit-content;
    padding: 0.35rem 0.6rem;
    border-radius: 999px;
    background: rgba(245, 158, 11, 0.16);
    color: #92400e;
    font-weight: 700;
  }

  .review-box__flag--info {
    background: rgba(29, 78, 216, 0.12);
    color: #1e40af;
  }

  .corrective-plan {
    border: 1px solid rgba(37, 99, 235, 0.16);
    background: linear-gradient(180deg, rgba(239, 246, 255, 0.95), rgba(255, 255, 255, 0.98));
  }

  .plan-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 0.75rem;
    margin-top: 0.75rem;
  }

  .plan-card {
    padding: 0.85rem 0.9rem;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.92);
    border: 1px solid rgba(148, 163, 184, 0.18);
  }

  .plan-card__label,
  .plan-note span {
    display: inline-block;
    margin-bottom: 0.35rem;
    font-weight: 700;
    color: #1d4ed8;
  }

  .plan-card p,
  .plan-note p {
    margin: 0;
    color: #1f2937;
    line-height: 1.5;
  }

  .plan-note {
    margin-top: 0.85rem;
    padding: 0.85rem 0.9rem;
    border-radius: 16px;
    background: rgba(254, 249, 195, 0.55);
    border: 1px solid rgba(202, 138, 4, 0.16);
  }
</style>
