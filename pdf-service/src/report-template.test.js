const assert = require('node:assert/strict');
const { renderReportHtml } = require('./report-template');

const baseReport = {
  report_id: 'TEST-001',
  generated_at: '2026-06-11T12:00:00Z',
  app_version: '0.1.0',
  model_version: 'v1_2_multimodal_sbert_svm_candidate',
  provider: 'local',
  scenario: 'Boxes are blocking the fire exit in the corridor',
  location: 'Main hallway',
  original_language: 'en',
  original_input: 'Workplace scenario: Boxes are blocking the fire exit in the corridor',
  translated_model_input: 'Workplace scenario: Boxes are blocking the fire exit in the corridor | Visual context: No reliable image caption generated',
  final_model_input: 'Workplace scenario: Boxes are blocking the fire exit in the corridor | Visual context: No reliable image caption generated',
  image_included: true,
  image_file_name: 'hazard_test_image.png',
  image_mime_type: 'image/png',
  image_data_url: null,
  image_caption: 'No reliable image caption generated',
  image_caption_status: 'Failed',
  image_caption_model: 'Salesforce/blip2-opt-2.7b',
  image_caption_warning: 'Caption too short',
  predicted_hazard_category: 'Obstruction Hazard',
  predicted_risk_level: 'Medium',
  hazard_confidence: 0.75,
  hazard_confidence_percent: '75.00%',
  risk_confidence: null,
  risk_confidence_percent: null,
  overall_confidence: 0.75,
  overall_confidence_percent: '75.00%',
  overall_confidence_label: 'Medium confidence',
  hazard_probabilities: [],
  risk_probabilities: [],
  confidence_note: 'Medium confidence',
  risk_badge: 'MEDIUM RISK',
  urgency: 'Medium',
  sub_hazard: 'blocked fire exit',
  risk_method: 'deterministic severity_score rule',
  decision_support_recommendation: 'Prompt corrective action is recommended.',
  recommendation: 'Prompt corrective action is recommended.',
  suggested_follow_up_steps: ['Inspect the area', 'Remove the obstruction'],
  corrective_action_plan: {
    hazard_specific_finding: 'Boxes are blocking emergency equipment.',
    immediate_containment: 'Remove the obstruction.',
    corrective_action: 'Keep the route clear.',
    responsible_owner: 'Site supervisor',
    target_completion: 'Immediate',
    verification: 'Reinspect the route.',
    escalation: 'Escalate if unresolved.',
    closure_condition: 'Route verified clear.',
    manual_review_note: 'Manual review required.'
  },
  recommended_follow_up: 'Inspect the area and verify the route is clear.',
  safety_note: 'Decision support only.'
};

const html = renderReportHtml(baseReport);
assert.match(html, /Caption status/i);
assert.match(html, /Salesforce\/blip2-opt-2\.7b/);
assert.match(html, /No reliable image caption generated/);
assert.match(html, /Image Included/i);

console.log('report-template caption metadata test passed');
