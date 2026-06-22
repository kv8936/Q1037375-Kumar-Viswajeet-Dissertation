<script>
  import { base } from '$app/paths';
  import { lang, t } from '$lib/i18n';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';

  // The questionnaire route is fully self-contained (its own styles + chrome),
  // so it must not inherit the chatbot shell or the global app.css.
  $: isQuestionnaire = ($page.route?.id ?? '') === '/questionnaire';

  // Highlight the "Chatbot" nav link (yellow) while on the Data privacy page, so the
  // way back to the chatbot is obvious (best-practice back-affordance).
  $: onDataPrivacy = $page.url.pathname.includes('data-privacy');

  // True when this chatbot runs inside the questionnaire's "Try Chatbot" tab (an iframe).
  const isEmbedded = () => typeof window !== 'undefined' && window.self !== window.top;

  // Set the language. When the user triggers it (not the parent), mirror the EN/DE choice
  // to the parent questionnaire so both sides stay in sync across the iframe boundary.
  function setLang(l, fromParent = false) {
    lang.set(l);
    if (!fromParent && isEmbedded()) {
      try {
        window.parent.postMessage({ type: 'set-lang', lang: l }, window.location.origin);
      } catch (e) {
        /* cross-origin or blocked — ignore */
      }
    }
  }

  onMount(() => {
    function onMessage(event) {
      // Same-origin only (the questionnaire is served from the same site).
      if (event.origin !== window.location.origin) return;
      const data = event.data;
      if (!data || typeof data !== 'object') return;
      if (data.type === 'set-lang' && (data.lang === 'en' || data.lang === 'de')) {
        setLang(data.lang, true); // apply without echoing back — keeps it loop-safe
      }
    }
    window.addEventListener('message', onMessage);
    // On load inside the questionnaire, adopt its current language.
    if (isEmbedded()) {
      try {
        window.parent.postMessage({ type: 'request-lang' }, window.location.origin);
      } catch (e) {
        /* ignore */
      }
    }
    return () => window.removeEventListener('message', onMessage);
  });
</script>

<svelte:head>
  {#if !isQuestionnaire}
    <link rel="icon" href="{base}/favicon.svg" type="image/svg+xml" />
    <title>{$t('title')}</title>
    <meta name="description" content={$t('subtitle')} />
  {/if}
</svelte:head>

{#if isQuestionnaire}
  <slot />
{:else}
<div class="app-shell">
  <a class="skip-link" href="#main">{$t('skip_to_content')}</a>

  <div class="app-shell__inner">
    <header class="topbar">
      <div class="brand">
        <div class="brand__mark">SC</div>
        <div class="brand__copy">
          <p class="brand__eyebrow">{$t('brand_eyebrow')}</p>
          <h1 class="brand__title">{$t('title')}</h1>
          <p class="brand__subtitle">{$t('subtitle')}</p>
        </div>
      </div>

      <div class="topbar__meta">
        <div class="topbar__status-group">
          <a class="soft-pill topbar__nav-link" class:is-back-highlight={onDataPrivacy} href={base + '/'}>{$t('home_button_label')}</a>
          <span class="status-pill">{$t('status_ready')}</span>
          <span class="soft-pill">{$t('dashboard_pdf_status')}</span>
          <a class="soft-pill topbar__nav-link" href={base + '/data-privacy'}>{$t('data_privacy_nav')}</a>
        </div>

        <div class="segmented topbar__language" role="group" aria-label="Language selector">
          <button on:click={() => setLang('en')} aria-pressed={$lang === 'en'}>{$t('language_en')}</button>
          <button on:click={() => setLang('de')} aria-pressed={$lang === 'de'}>{$t('language_de')}</button>
        </div>
      </div>
    </header>

    <slot />
  </div>
</div>
{/if}
