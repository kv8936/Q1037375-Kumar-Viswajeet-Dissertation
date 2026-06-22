# Hazard Chatbot: Workplace Hazard Assessment Questionnaire

**Try the chatbot:** [https://kv8936.github.io/kv-chatbot/](https://kv8936.github.io/kv-chatbot/)

## Academic Context

- Dissertation ID: Q1037375
- Author: Kumar Viswajeet
- Email: kumarviswajeet6@gmail.com
- Programme: MSc Artificial Intelligence
- Institution: Berlin School of Business and Innovation

This repository contains the usability evaluation questionnaire for the **hazard chatbot**, a dissertation prototype for workplace hazard identification and early-stage risk assessment. The questionnaire is used to collect participant feedback on the chatbot prototype's usability, clarity, and decision-support capability.

The questionnaire supports the MSc Artificial Intelligence dissertation titled:

**Assessing the Accuracy, Usability, and Decision-Support Capability of an AI-powered Chatbot for Workplace Hazard Identification and Risk Assessment**

## Questionnaire Purpose

The purpose of this questionnaire is to evaluate whether the hazard chatbot prototype can support early-stage workplace safety screening by collecting structured user feedback on:

- ease of use;
- clarity of chatbot instructions and outputs;
- relevance of hazard classification;
- usefulness of risk-level recommendations;
- practical value of corrective-action guidance;
- overall trust and perceived usefulness.

This questionnaire is intended for academic evaluation only. Responses are anonymised and used solely for dissertation analysis.

## About the Hazard Chatbot

The hazard chatbot is a dissertation prototype for workplace hazard identification and early-stage risk assessment. The system analyses workplace hazard scenarios, classifies the likely hazard category, assigns a risk level, and generates structured safety recommendations.



## Key Features of the Questionnaire

- Single-file HTML questionnaire
- English and German language support
- Progress bar for completion tracking
- Likert-scale evaluation section
- Open-ended feedback fields
- Overall usefulness rating
- Mobile-friendly responsive interface
- Anonymised submission workflow

## Evaluated Chatbot Pipeline

The final evaluated dissertation model is **Model 3: v1.2 multimodal candidate**.

The evaluated pipeline used:

```text
BLIP-2-prepared visual captions
+ Sentence-BERT all-mpnet-base-v2 embeddings
+ Linear SVM hazard classifier
+ deterministic severity-score risk rule
+ manual-review flagging
```

Important distinction:

```text
Evaluated dissertation pipeline:
BLIP-2-prepared captions + Sentence-BERT + Linear SVM

Live prototype/reporting layer:
runtime visual-caption stage + Sentence-BERT/Linear SVM inference workflow
```

The live prototype should only be described as running BLIP-2 at runtime if the runtime captioning configuration has been explicitly verified.

## Model Development Stages

Three model stages were evaluated during the dissertation.

| Model | Role | Pipeline |
| --- | --- | --- |
| Model 1 | Baseline benchmark | TF-IDF + Logistic Regression |
| Model 2 | Hybrid safety-control refinement | TF-IDF + Logistic Regression + deterministic risk rule + manual-review flag |
| Model 3 | Final selected model | BLIP-2-prepared captions + Sentence-BERT + Linear SVM + deterministic risk rule + manual-review flag |

Model 1 and Model 2 were used for comparative evaluation and were not the final chatbot model.

## Final Test Results

| Metric | Model 1 | Model 2 | Model 3 |
| --- | ---: | ---: | ---: |
| Hazard accuracy | 82.22% | 88.89% | 97.78% |
| Risk accuracy | 71.11% | 100.00% | 100.00% |
| Combined exact-match accuracy | 53.33% | Not reported | 97.78% |
| Manual-review cases | Not applicable | 29 | 7 |
| High-to-Low risk errors | 1 | 0 | 0 |

Model 3 achieved the strongest overall performance on the held-out test set. The single hazard classification error involved an ambiguous case where blocked access to fire-safety equipment overlapped between Fire Hazard and Obstruction Hazard. That case was flagged for manual review.

## Hazard Categories

The prototype classifies workplace scenarios into six hazard categories:

- Slip/Trip Hazard
- Electrical Hazard
- Fire Hazard
- Ergonomic Hazard
- Obstruction Hazard
- Visibility Hazard

## Risk Classification

Risk level is assigned using a deterministic severity-score rule:

```text
Low risk     = lower severity score
Medium risk  = intermediate severity score
High risk    = higher severity score
```

The risk rule was used to improve transparency and reduce safety-critical underestimation. The 100% risk accuracy in the final model should therefore be interpreted as rule-derived consistency, not as autonomous AI risk reasoning.

## Dataset Summary

The evaluation dataset contained 300 synthetic workplace hazard scenarios.

| Dataset characteristic | Value |
| --- | ---: |
| Total cases | 300 |
| Hazard categories | 6 |
| Cases per hazard category | 50 |
| Text-only cases | 180 |
| Text-plus-image cases | 120 |
| Training cases | 210 |
| Validation cases | 45 |
| Held-out test cases | 45 |
| Risk levels | Low, Medium, High |

The dataset was synthetic but designed to reflect realistic workplace hazard scenarios. It included scenario text, workplace location, hazard category, risk level, severity score, recommended action fields, and visual-caption fields for image-supported cases.

## Prototype Output Examples

| Example | Input type | Predicted hazard | Risk level | Purpose |
| --- | --- | --- | --- | --- |
| Wet floor near stairs | Text-only | Slip/Trip Hazard | Medium | Demonstrates text-only hazard classification |
| Combustible waste in storage area | Text + image | Fire Hazard | High | Demonstrates image-supported workflow |
| Blocked fire extinguisher access | Text + image | Obstruction Hazard | Medium | Demonstrates ambiguity handling and manual review |

## Repository Structure

```text
.
├── index.html         # Complete questionnaire interface
├── favicon.svg        # Site favicon (HC — Hazard Chatbot)
├── netlify.toml       # Optional deployment config
└── README.md          # Project documentation
```

## Local Usage

Open the questionnaire locally by opening [index.html](index.html) in a browser.

## Deployment

This questionnaire can be deployed as a static site using GitHub Pages or Netlify.

For GitHub Pages:

1. Push the repository to GitHub.
2. Open repository settings.
3. Go to **Pages**.
4. Set **Source** to `Deploy from a branch`.
5. Select the `main` branch and `/ (root)` folder.

## Privacy and Safety Notes

This project is a research questionnaire supporting an MSc Artificial Intelligence dissertation prototype. It should be used only for academic demonstration and evaluation.

Do not upload or collect:

- real personal data;
- confidential workplace incident reports;
- identifiable employee information;
- sensitive company information;
- private images without permission.

The chatbot output is decision support only. All safety decisions should be reviewed by a competent person before workplace action is taken.

## Limitations

- The evaluation dataset is synthetic.
- The held-out test set contains 45 cases.
- The runtime visual-caption stage may produce generic or incomplete captions.
- Risk classification depends on the predefined severity-score rule.
- The prototype is not a certified safety product.
- Manual review remains necessary for ambiguous or safety-critical cases.
- Usability findings will be added after questionnaire data collection.

## Dissertation Status

Completed:

- dataset creation and structuring;
- baseline model evaluation;
- hybrid safety-control model evaluation;
- final v1.2 model evaluation;
- prototype output testing;
- questionnaire implementation.

Pending:

- usability questionnaire response collection;
- final usability analysis;
- final dissertation conclusion.

## Academic Disclaimer

This repository supports an MSc Artificial Intelligence dissertation project. The system and associated questionnaire are intended for academic research, demonstration, and evaluation only. They must not be used as a substitute for legal compliance, certified workplace risk assessment, occupational safety inspection, or competent professional judgement.

## Licence

This repository is currently intended for academic review. Please contact the author for any reuse or adaptation requests.
