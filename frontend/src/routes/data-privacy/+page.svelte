<script>
  import { t } from '$lib/i18n';
  import '../../app.css';
</script>

<svelte:head>
  <title>{$t('data_privacy_nav')} · {$t('title')}</title>
  <meta name="description" content={$t('privacy_page_intro')} />
</svelte:head>

<main id="main" class="stack">
  <section class="hero hero--dashboard">
    <p class="hero__eyebrow">{$t('privacy_page_eyebrow')}</p>
    <h2 class="hero__title">{$t('privacy_page_title')}</h2>
    <p class="hero__body privacy-page__intro">{$t('privacy_page_intro')}</p>

    <div class="hero__quick-strip" aria-label={$t('privacy_page_title')}>
      <span class="soft-pill">{$t('privacy_badge_no_login')}</span>
      <span class="soft-pill">{$t('privacy_badge_prototype')}</span>
      <span class="soft-pill">{$t('privacy_badge_no_permanent_storage')}</span>
    </div>
  </section>

  <section class="panel privacy-page">
    <div class="privacy-section">
      <p class="metric__label">{$t('privacy_no_login_title')}</p>
      <p class="privacy-section__text">{$t('privacy_no_login_body')}</p>
    </div>

    <div class="privacy-section">
      <p class="metric__label">{$t('privacy_prototype_title')}</p>
      <p class="privacy-section__text">{$t('privacy_prototype_body')}</p>
    </div>

    <div class="privacy-section">
      <p class="metric__label">{$t('privacy_browser_title')}</p>
      <ul class="privacy-section__list">
        <li>{$t('privacy_browser_item_1')}</li>
        <li>{$t('privacy_browser_item_2')}</li>
        <li>{$t('privacy_browser_item_3')}</li>
      </ul>
    </div>

    <div class="privacy-section">
      <p class="metric__label">{$t('privacy_request_title')}</p>
      <ul class="privacy-section__list">
        <li>{$t('privacy_request_item_1')}</li>
        <li>{$t('privacy_request_item_2')}</li>
        <li>{$t('privacy_request_item_3')}</li>
      </ul>
    </div>

    <div class="privacy-section">
      <p class="metric__label">{$t('privacy_storage_title')}</p>
      <ul class="privacy-section__list">
        <li>{$t('privacy_storage_item_1')}</li>
        <li>{$t('privacy_storage_item_2')}</li>
        <li>{$t('privacy_storage_item_3')}</li>
        <li>{$t('privacy_storage_item_4')}</li>
      </ul>
    </div>

    <div class="privacy-section">
      <p class="metric__label">{$t('privacy_pdf_title')}</p>
      <ul class="privacy-section__list">
        <li>{$t('privacy_pdf_item_1')}</li>
        <li>{$t('privacy_pdf_item_2')}</li>
      </ul>
    </div>

    <div class="privacy-section">
      <p class="metric__label">{$t('privacy_provider_title')}</p>
      <ul class="privacy-section__list">
        <li>{$t('privacy_provider_item_1')}</li>
        <li>{$t('privacy_provider_item_2')}</li>
      </ul>
    </div>

    <div class="privacy-section">
      <p class="metric__label">{$t('privacy_guidance_title')}</p>
      <ul class="privacy-section__list">
        <li>{$t('privacy_guidance_item_1')}</li>
        <li>{$t('privacy_guidance_item_2')}</li>
      </ul>
    </div>

  </section>
</main>