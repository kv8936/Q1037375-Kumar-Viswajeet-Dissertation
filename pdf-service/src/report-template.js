const escapeHtml = (value) => {
  const text = value === null || value === undefined ? '' : String(value);
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
};

const safeText = (value, fallback = '—') => {
  const text = value === null || value === undefined ? '' : String(value).trim();
  return text.length > 0 ? escapeHtml(text) : fallback;
};

const t = (locale, en, de) => (String(locale || '').toLowerCase().startsWith('de') ? de : en);

const localizeCaptionStatus = (locale, value) => {
  const text = String(value || '').trim();
  if (!text) return '—';
  if (!String(locale || '').toLowerCase().startsWith('de')) return text;
  if (text === 'Completed') return 'Abgeschlossen';
  if (text === 'Failed') return 'Fehlgeschlagen';
  if (text === 'Not available') return 'Nicht verfügbar';
  return text;
};

const renderParagraphList = (value) => {
  const text = value === null || value === undefined ? '' : String(value).trim();
  if (!text) {
    return '<p class="empty-state">No text provided.</p>';
  }

  const items = text
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => `<p>${escapeHtml(line)}</p>`)
    .join('');

  return items || '<p class="empty-state">No text provided.</p>';
};

const renderProbabilityList = (items) => {
  if (!Array.isArray(items) || items.length === 0) {
    return '<p class="empty-state">No probability breakdown available.</p>';
  }

  return `<ul class="probability-list">${items
    .slice(0, 3)
    .map((item) => `<li><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.percent || '—')}</strong></li>`)
    .join('')}</ul>`;
};

const buildFindingSentence = (report) => {
  if (isGermanReport(report)) {
    const risk = String(report.predicted_risk_level || '').trim() || 'nicht verfügbar';
    const hazard = String(report.predicted_hazard_category || '').trim() || 'Gefährdung nicht angegeben';
    const location = String(report.location || '').trim() || 'dem gemeldeten Ort';
    return `Die hochgeladene Evidenz aus ${location} wurde als ${risk.toLowerCase()} eingestuft, mit der primären Gefährdungskategorie ${hazard}.`;
  }
  const risk = String(report.predicted_risk_level || '').trim() || 'unavailable risk';
  const hazard = String(report.predicted_hazard_category || '').trim() || 'hazard not specified';
  const location = String(report.location || '').trim() || 'the reported location';
  return `The uploaded evidence from ${location} has been classified as ${risk.toLowerCase()} with a primary hazard category of ${hazard}.`;
};

const buildActionSentence = (report) => {
  const level = String(report.predicted_risk_level || '').trim().toLowerCase();
  const plan = report.corrective_action_plan || {};
  if (plan && typeof plan === 'object' && plan.hazard_specific_finding) {
    return String(plan.hazard_specific_finding);
  }
  if (isGermanReport(report)) {
    if (level === 'high') {
      return 'Sofortige Prüfung, Isolierung der Gefahrenquelle und Eskalation an eine Führungskraft sind erforderlich, bevor die Arbeit fortgesetzt wird.';
    }
    if (level === 'medium') {
      return 'Zeitnahe Korrekturmaßnahmen, Sichtprüfung und eine kurzfristige Nachverfolgung sind erforderlich.';
    }
    if (level === 'low') {
      return 'Regelmäßige Überwachung und Standardkontrollen erscheinen in diesem Stadium ausreichend.';
    }
    return 'Aus der aktuellen Modellausgabe konnte keine klare Folgemaßnahme abgeleitet werden.';
  }
  if (level === 'high') {
    return 'Immediate inspection, isolation of the hazard source, and escalation to a supervisor are recommended before work continues.';
  }
  if (level === 'medium') {
    return 'Prompt corrective action, visual review, and short-interval follow-up are recommended.';
  }
  if (level === 'low') {
    return 'Routine monitoring and standard controls appear sufficient at this stage.';
  }
  return 'A clear follow-up action could not be derived from the current model output.';
};

const isGermanReport = (report) => String(report.original_language || '').toLowerCase().startsWith('de');

const hazardLabel = (report, value) => {
  if (!isGermanReport(report)) return safeText(value, '—');
  const text = String(value || '').toLowerCase();
  if (text.includes('electrical')) return 'Elektrische Gefährdung';
  if (text.includes('fire')) return 'Brandgefahr';
  if (text.includes('obstruction')) return 'Blockade';
  if (text.includes('slip') || text.includes('trip')) return 'Rutsch-/Stolpergefahr';
  if (text.includes('ergonomic')) return 'Ergonomische Gefährdung';
  if (text.includes('visibility')) return 'Sichtgefährdung';
  return safeText(value, '—');
};

const riskLabel = (report, value) => {
  if (!isGermanReport(report)) return safeText(value, '—');
  const text = String(value || '').toLowerCase();
  if (text === 'high') return 'Hoch';
  if (text === 'medium') return 'Mittel';
  if (text === 'low') return 'Niedrig';
  return safeText(value, '—');
};

const planField = (plan, key) => {
  if (!plan || typeof plan !== 'object') {
    return '—';
  }

  return safeText(plan[key], '—');
};

/**
 * Returns null when the caption is empty or absent so the template can render a styled placeholder instead.
 */
const safeCaptionText = (value) => {
  const text = String(value ?? '').trim();
  if (!text || text.toLowerCase() === 'none' || text === '—') {
    return null;
  }
  return text;
};

const hasRenderableValue = (value) => {
  const text = String(value ?? '').trim();
  if (!text) return false;
  const lowered = text.toLowerCase();
  return !['—', 'none', 'null', 'undefined', 'n/a', 'na'].includes(lowered) && !lowered.includes('unavailable');
};

const sanitizeSnapshotSegment = (segment) => {
  const text = String(segment ?? '').trim();
  if (!text) return '';

  const separatorIndex = text.indexOf(':');
  if (separatorIndex === -1) {
    return hasRenderableValue(text) ? text : '';
  }

  const label = text.slice(0, separatorIndex + 1).trim();
  const value = text.slice(separatorIndex + 1).trim();
  return hasRenderableValue(value) ? `${label} ${value}` : '';
};

const sanitizeSnapshotText = (value) => {
  const raw = String(value ?? '').trim();
  if (!raw) {
    return '';
  }

  return raw
    .split(/\n+/)
    .map((line) => line.split('|').map((segment) => sanitizeSnapshotSegment(segment)).filter(Boolean).join(' | ').trim())
    .filter(Boolean)
    .join('\n')
    .trim();
};

const normalizedRiskLevel = (value) => {
  const text = String(value ?? '').trim().toLowerCase();
  if (text === 'high' || text === 'hoch') return 'high';
  if (text === 'medium' || text === 'mittel') return 'medium';
  if (text === 'low' || text === 'niedrig') return 'low';
  return 'unknown';
};

const defaultFollowUpSteps = (report) => {
  const level = normalizedRiskLevel(report.predicted_risk_level);

  if (isGermanReport(report)) {
    if (level === 'high') {
      return [
        'Zugang sofort einschränken und die zuständige Sicherheitsverantwortung informieren.',
        'Korrekturmaßnahmen unverzüglich einleiten und den Bereich bis zur Beherrschung der Gefährdung überwachen.',
        'An die verantwortliche Stelle eskalieren, bis eine sichere Freigabe bestätigt ist.',
      ];
    }
    if (level === 'medium') {
      return [
        'Korrekturmaßnahmen innerhalb eines angemessenen betrieblichen Zeitfensters einplanen.',
        'Den Bereich überwachen, bis die Gefährdung wirksam beherrscht ist.',
        'Bei Verschlechterung der Bedingungen an die verantwortliche Stelle eskalieren.',
      ];
    }
    if (level === 'low') {
      return [
        'Die Gefährdung dokumentieren und über das reguläre Sicherheitsverfahren weiterleiten.',
        'Die Korrektur im normalen Wartungs- oder Maßnahmenzyklus einplanen.',
        'Weiter beobachten, bis die Beseitigung bestätigt ist.',
      ];
    }

    return ['Eine fachkundige Prüfung durchführen, bevor Maßnahmen freigegeben werden.'];
  }

  if (level === 'high') {
    return [
      'Restrict access immediately and notify the responsible safety lead.',
      'Start corrective action without delay and monitor the area until the hazard is controlled.',
      'Escalate to the responsible owner until safe release is confirmed.',
    ];
  }
  if (level === 'medium') {
    return [
      'Plan corrective action within a reasonable operational window.',
      'Monitor the area until the hazard is controlled.',
      'Escalate to the responsible owner if conditions worsen.',
    ];
  }
  if (level === 'low') {
    return [
      'Document the hazard and route it through standard safety procedures.',
      'Schedule corrective action during the normal maintenance cycle.',
      'Monitor until the issue is confirmed resolved.',
    ];
  }

  return ['Complete a competent-person review before acting on the result.'];
};

const containsLikelyEnglish = (value) => /\b(the|and|with|for|to|monitor|document|schedule|notify|restrict|escalate|owner|action|review)\b/i.test(String(value ?? ''));
const containsLikelyGerman = (value) => /[äöüß]|\b(und|mit|für|über|bis|prüfung|maßnahme|bereich|gefährdung|verantwortliche)\b/i.test(String(value ?? ''));

const localizedFollowUpSteps = (report) => {
  const incoming = Array.isArray(report.suggested_follow_up_steps)
    ? report.suggested_follow_up_steps.map((step) => String(step ?? '').trim()).filter(Boolean)
    : [];

  if (incoming.length === 0) {
    return defaultFollowUpSteps(report);
  }

  if (isGermanReport(report)) {
    return incoming.some((step) => containsLikelyEnglish(step) && !containsLikelyGerman(step))
      ? defaultFollowUpSteps(report)
      : incoming;
  }

  return incoming;
};

const defaultRecommendedFollowUp = (report) => {
  const level = normalizedRiskLevel(report.predicted_risk_level);

  if (isGermanReport(report)) {
    if (level === 'high') {
      return 'Zugang sofort einschränken und die zuständige Sicherheitsverantwortung informieren. Korrekturmaßnahmen unverzüglich einleiten. Erst nach bestätigter Sicherung zur normalen Arbeit zurückkehren.';
    }
    if (level === 'medium') {
      return 'Korrekturmaßnahmen kurzfristig planen, den Bereich überwachen und bei Verschlechterung an die verantwortliche Stelle eskalieren.';
    }
    if (level === 'low') {
      return 'Die Gefährdung dokumentieren, im regulären Maßnahmenzyklus bearbeiten und bis zur Bestätigung der Behebung weiter beobachten.';
    }
    return 'Vor Maßnahmen sollte eine fachkundige Prüfung durchgeführt werden.';
  }

  if (level === 'high') {
    return 'Restrict access immediately, notify the responsible safety lead, and complete corrective action before normal work resumes.';
  }
  if (level === 'medium') {
    return 'Plan corrective action promptly, monitor the area, and escalate to the responsible owner if conditions worsen.';
  }
  if (level === 'low') {
    return 'Document the hazard, resolve it through the normal corrective-action cycle, and monitor until closure is confirmed.';
  }
  return 'Complete a competent-person review before acting on the result.';
};

const localizedRecommendedFollowUp = (report) => {
  const incoming = String(report.recommended_follow_up ?? '').trim();
  if (!incoming) {
    return defaultRecommendedFollowUp(report);
  }

  if (isGermanReport(report) && containsLikelyEnglish(incoming) && !containsLikelyGerman(incoming)) {
    return defaultRecommendedFollowUp(report);
  }

  return incoming;
};

const renderReportHtml = (report) => {
  const locale = isGermanReport(report) ? 'de' : 'en';
  const scenario = safeText(report.scenario, 'Unknown scenario');
  const location = safeText(report.location, 'Unknown location');
  const reportTitle = `${scenario} — ${location}`;
  const translatedModelInput = sanitizeSnapshotText(report.translated_model_input);
  const finalModelInput = sanitizeSnapshotText(report.final_model_input);
  const modelInputSnapshot = finalModelInput && finalModelInput !== translatedModelInput ? finalModelInput : '';
  const followUpSteps = localizedFollowUpSteps(report);
  const recommendedFollowUp = localizedRecommendedFollowUp(report);
  const image = report.image_data_url
    ? `
      <div class="evidence-image-frame">
        <img src="${escapeHtml(report.image_data_url)}" alt="Uploaded evidence" class="evidence-image" />
      </div>
    `
    : `
      <div class="evidence-image-placeholder">
        <div class="placeholder-title">No image provided</div>
        <div class="placeholder-body">The report was generated without an uploaded evidence image.</div>
      </div>
    `;

  return `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${escapeHtml(report.report_id || 'Hazard Assessment Report')}</title>
  <style>
${report.inline_css}
  </style>
</head>
<body>
  <div class="page-shell">
    <header class="report-header">
      <div class="header-left">
        <div class="eyebrow">Prototype Health Risk Model by Kumar Viswajeet</div>
        <h1>${reportTitle}</h1>
        <p class="subtitle">${buildFindingSentence(report)}</p>
      </div>
      <div class="header-right">
        <div class="badge ${escapeHtml(String(report.risk_badge_class || 'badge-neutral'))}">${safeText(report.risk_badge, 'RISK UNAVAILABLE')}</div>
        <dl class="meta-grid">
          <div><dt>Report ID</dt><dd>${safeText(report.report_id)}</dd></div>
          <div><dt>Generated At</dt><dd>${safeText(report.generated_at)}</dd></div>
          <div><dt>App Version</dt><dd>${safeText(report.app_version)}</dd></div>
          <div><dt>Model Version</dt><dd>${safeText(report.model_version, 'v1_2_multimodal_sbert_svm_candidate')}</dd></div>
          <div><dt>Provider</dt><dd>${safeText(report.provider)}</dd></div>
        </dl>
      </div>
    </header>

    <main class="content-grid">
      <section class="card span-2">
        <div class="section-title">Assessment Summary</div>
        <div class="summary-grid">
          <div class="summary-item">
            <div class="summary-label">${t(locale, 'Scenario', 'Szenario')}</div>
            <div class="summary-value">${safeText(report.scenario)}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">${t(locale, 'Location', 'Ort')}</div>
            <div class="summary-value">${safeText(report.location)}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">${t(locale, 'Detected Language', 'Erkannte Sprache')}</div>
            <div class="summary-value">${safeText(report.original_language)}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">${t(locale, 'Original Input', 'Ursprüngliche Eingabe')}</div>
            <div class="summary-value text-block">${renderParagraphList(report.original_input)}</div>
          </div>
        </div>
      </section>

      <section class="card span-2">
        <div class="section-title">${t(locale, 'Prediction Summary', 'Vorhersageübersicht')}</div>
        <div class="summary-grid">
          <div class="summary-item">
            <div class="summary-label">${t(locale, 'Model Version', 'Modellversion')}</div>
            <div class="summary-value">${safeText(report.model_version, 'v1_2_multimodal_sbert_svm_candidate')}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">${t(locale, 'Hazard Category', 'Gefährdungskategorie')}</div>
            <div class="summary-value">${hazardLabel(report, report.predicted_hazard_category, 'Unspecified hazard')}</div>
            <div class="summary-confidence">${t(locale, 'Hazard Confidence', 'Gefährdungskonfidenz')}: ${safeText(report.hazard_confidence_percent, '—')}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">${t(locale, 'Risk Level', 'Risikoniveau')}</div>
            <div class="summary-value">${riskLabel(report, report.predicted_risk_level, 'Unspecified risk')}</div>
            <div class="summary-confidence">${t(locale, 'Risk Confidence', 'Risikokonfidenz')}: ${safeText(report.risk_confidence_percent, '—')}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">${t(locale, 'Overall Confidence', 'Gesamtkonfidenz')}</div>
            <div class="summary-value">${safeText(report.overall_confidence_label, t(locale, 'Confidence unavailable', 'Konfidenz nicht verfügbar'))}</div>
            <div class="summary-confidence">${safeText(report.overall_confidence_percent, '—')}</div>
          </div>
          <div class="summary-item">
            <div class="summary-label">${t(locale, 'Confidence Note', 'Hinweis zur Konfidenz')}</div>
            <div class="summary-confidence">${t(locale, 'Confidence values are model probability estimates and do not replace human review.', 'Konfidenzwerte sind modellbasierte Wahrscheinlichkeitsschätzungen und ersetzen keine menschliche Prüfung.')}</div>
            <div class="summary-confidence">${safeText(report.confidence_note, t(locale, 'No additional note provided.', 'Kein zusätzlicher Hinweis vorhanden.'))}</div>
          </div>
        </div>
        <div class="probability-grid">
          <div class="summary-item">
            <div class="summary-label">${t(locale, 'Hazard Probabilities', 'Gefährdungswahrscheinlichkeiten')}</div>
            ${renderProbabilityList(report.hazard_probabilities)}
          </div>
          <div class="summary-item">
            <div class="summary-label">${t(locale, 'Risk Probabilities', 'Risikowahrscheinlichkeiten')}</div>
            ${renderProbabilityList(report.risk_probabilities)}
          </div>
        </div>
      </section>

      <section class="card span-2">
        <div class="section-title">${t(locale, 'Key Findings', 'Wesentliche Erkenntnisse')}</div>
        <div class="finding-grid">
          <div class="finding-item">
            <div class="finding-label">${t(locale, 'Model Summary', 'Modellzusammenfassung')}</div>
            <div class="finding-text">${buildFindingSentence(report)}</div>
          </div>
          <div class="finding-item">
            <div class="finding-label">${t(locale, 'Recommended Action', 'Empfohlene Maßnahme')}</div>
            <div class="finding-text">${buildActionSentence(report)}</div>
          </div>
          <div class="finding-item">
            <div class="finding-label">${t(locale, 'Sub-hazard', 'Untergefahr')}</div>
            <div class="finding-text">${safeText(report.sub_hazard, 'Not identified')}</div>
          </div>
          <div class="finding-item">
            <div class="finding-label">${t(locale, 'Risk Method', 'Risikomethode')}</div>
            <div class="finding-text">${safeText(report.risk_method, 'Deterministic severity-score rule')}</div>
          </div>
          <div class="finding-item">
            <div class="finding-label">${t(locale, 'Translated Model Input', 'Übersetzte Modelleingabe')}</div>
            <div class="finding-text text-block">${renderParagraphList(translatedModelInput || report.original_input)}</div>
          </div>
          <div class="finding-item">
            <div class="finding-label">${t(locale, 'Reason for Review', 'Grund für die Prüfung')}</div>
            <div class="finding-text">${safeText(report.safety_note, 'No safety note available.')}</div>
          </div>
        </div>
      </section>

      <section class="card card--flow">
        <div class="section-title">${t(locale, 'Decision Support', 'Entscheidungsunterstützung')}</div>
        <div class="support-box">
          <h2>${t(locale, 'Recommended Action', 'Empfohlene Maßnahme')}</h2>
          <div class="support-text">${renderParagraphList(report.decision_support_recommendation)}</div>
          <h2>${t(locale, 'Corrective Action Plan', 'Korrekturmaßnahmenplan')}</h2>
          <div class="plan-grid">
            <div class="plan-item"><strong>${t(locale, 'Hazard-specific finding', 'Gefahrenspezifische Feststellung')}</strong><p>${planField(report.corrective_action_plan, 'hazard_specific_finding')}</p></div>
            <div class="plan-item"><strong>${t(locale, 'Immediate containment', 'Sofortige Eindämmung')}</strong><p>${planField(report.corrective_action_plan, 'immediate_containment')}</p></div>
            <div class="plan-item"><strong>${t(locale, 'Corrective action', 'Korrekturmaßnahme')}</strong><p>${planField(report.corrective_action_plan, 'corrective_action')}</p></div>
            <div class="plan-item"><strong>${t(locale, 'Responsible owner', 'Verantwortliche Stelle')}</strong><p>${planField(report.corrective_action_plan, 'responsible_owner')}</p></div>
            <div class="plan-item"><strong>${t(locale, 'Target completion', 'Zieltermin')}</strong><p>${planField(report.corrective_action_plan, 'target_completion')}</p></div>
            <div class="plan-item"><strong>${t(locale, 'Verification', 'Überprüfung')}</strong><p>${planField(report.corrective_action_plan, 'verification')}</p></div>
            <div class="plan-item"><strong>${t(locale, 'Escalation', 'Eskalation')}</strong><p>${planField(report.corrective_action_plan, 'escalation')}</p></div>
            <div class="plan-item"><strong>${t(locale, 'Closure condition', 'Abschlussbedingung')}</strong><p>${planField(report.corrective_action_plan, 'closure_condition')}</p></div>
          </div>
          <h2>${t(locale, 'Manual Review Note', 'Hinweis zur manuellen Prüfung')}</h2>
          <div class="support-text"><p>${planField(report.corrective_action_plan, 'manual_review_note')}</p></div>
          <h2>${t(locale, 'Suggested Follow-up Steps', 'Empfohlene Folgeschritte')}</h2>
          <div class="support-text">${followUpSteps.length > 0
            ? followUpSteps.map((step) => `<p>${escapeHtml(step)}</p>`).join('')
            : '<p class="empty-state">No additional follow-up steps provided.</p>'}</div>
          <h2>${t(locale, 'Follow-up', 'Nachverfolgung')}</h2>
          <div class="support-text">${renderParagraphList(recommendedFollowUp)}</div>
        </div>
      </section>

      <section class="card span-2">
        <div class="section-title">${t(locale, 'Image Evidence', 'Bildnachweis')}</div>
        ${image}
        <div class="caption-row">
          <div><strong>${t(locale, 'Caption', 'Bildbeschreibung')}:</strong> ${(() => {
            const cap = safeCaptionText(report.image_caption);
            return cap
              ? escapeHtml(cap)
              : '<span class="caption-placeholder">' + t(locale, 'No reliable image caption generated', 'Keine verlässliche Bildbeschreibung erzeugt') + '</span>';
          })()}</div>
          <div><strong>${t(locale, 'Caption status', 'Beschriftungsstatus')}:</strong> ${escapeHtml(localizeCaptionStatus(locale, report.image_caption_status))}</div>
          <div><strong>${t(locale, 'Caption model', 'Beschriftungsmodell')}:</strong> ${safeText(report.image_caption_model, '—')}</div>
          <div><strong>${t(locale, 'Caption warning', 'Beschriftungshinweis')}:</strong> ${safeText(report.image_caption_warning, '—')}</div>
          <div><strong>${t(locale, 'Image Included', 'Bild enthalten')}:</strong> ${report.image_included ? t(locale, 'Yes', 'Ja') : t(locale, 'No', 'Nein')}</div>
          <div><strong>${t(locale, 'MIME Type', 'MIME-Typ')}:</strong> ${safeText(report.image_mime_type, '—')}</div>
        </div>
      </section>

      ${modelInputSnapshot
        ? `
      <section class="card span-2">
        <div class="section-title">${t(locale, 'Model Input Snapshot', 'Modelleingabe-Snapshot')}</div>
        <div class="mono-box">${renderParagraphList(modelInputSnapshot)}</div>
      </section>`
        : ''}
    </main>

    <footer class="report-footer">
      <div>
        <strong>Prototype Health Risk Model by Kumar Viswajeet</strong>
      </div>
      <div>Local-only prototype — validation and research use only — ${safeText(report.report_id)}</div>
    </footer>
  </div>
</body>
</html>`;
};

module.exports = {
  renderReportHtml,
};
