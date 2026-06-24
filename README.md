#  Workplace Hazard Assessment Chatbot

**Live Deployment:** _set your own deployment URL after you publish_

## Academic Context

- Dissertation ID: Q1037375
- Author: Kumar Viswajeet
- Email: hazard-chatbot@mailbox.org
- Programme: MSc Artificial Intelligence
- Institution: Berlin School of Business and Innovation

SCARP is a dissertation prototype for workplace hazard identification and early-stage risk assessment. The system analyses workplace hazard scenarios, classifies the likely hazard category, assigns a risk level, and generates structured safety recommendations.

This project was developed as part of an MSc Artificial Intelligence dissertation titled:

**Assessing the Accuracy, Usability, and Decision-Support Capability of an AI-powered Chatbot for Workplace Hazard Identification and Risk Assessment**

## Project Purpose

The purpose of this project is to evaluate whether an AI-powered chatbot can support early-stage workplace safety screening by:

- identifying workplace hazard categories from user-provided scenarios;
- classifying risk levels as Low, Medium, or High;
- generating preliminary corrective-action guidance;
- flagging uncertain or ambiguous cases for manual review;
- producing structured PDF reports for documentation.

This prototype is intended for academic evaluation and early-stage decision support only. It is not a certified workplace safety system and must not replace competent occupational safety assessment.

## Key Features

- Workplace hazard scenario input
- Optional image upload
- Runtime visual-caption support for uploaded images
- Hazard category classification
- Deterministic severity-score risk classification
- Manual-review flag for uncertain or ambiguous outputs
- Corrective-action recommendations
- Escalation and verification guidance
- PDF report export
- English and German interface support
- Local model inference workflow

## Evaluated Model Pipeline

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

## System Architecture

The prototype uses a multi-service architecture:

```text
Frontend:
SvelteKit

Backend:
Rust / Axum

Inference service:
Python / FastAPI

Model layer:
Sentence-BERT + Linear SVM
Legacy TF-IDF/Logistic Regression models for comparison

PDF reporting:
Node.js / Playwright

Optional database:
PostgreSQL

Deployment support:
Docker Compose / Caddy
```

## Repository Structure

```text
.
├── backend/               # Rust/Axum API layer
├── caddy/                 # Reverse proxy configuration
├── database/              # Optional PostgreSQL schema
├── frontend/              # SvelteKit user interface
├── inference/             # Python/FastAPI model inference service
├── models/                # Saved model assets and versions
├── pdf-service/           # PDF report generation service
├── docker-compose.yml     # Local multi-service orchestration
└── README.md
```

## Model Folders

- `models/v1_baseline`
- `models/v1_1_candidate`
- `models/v1_2_multimodal_sbert_svm_candidate`

Active chatbot model:

- `v1_2_multimodal_sbert_svm_candidate`

## Local Setup

Start the local services:

```bash
docker compose up --build
```

## Default URLs

- App: http://localhost:8080
- Backend: http://localhost:8000
- Inference: http://localhost:8001
- PDF service: http://localhost:3001

## Environment Variables

Create a local `.env` file where required.

Example:

```env
INFERENCE_URL=http://inference:8000
PDF_SERVICE_URL=http://pdf-service:3000
PRIVACY_MODE=true
ENABLE_DB_CONTENT_LOGGING=false
```

Do not commit `.env` files, API keys, participant responses, or private dissertation data.

## Service Documentation

- [backend/README.md](backend/README.md)
- [frontend/README.md](frontend/README.md)
- [pdf-service/README.md](pdf-service/README.md)
- [caddy/README.md](caddy/README.md)
- [document/README.md](document/README.md)

## Privacy and Safety Notes

This project is a research prototype. It should be used only for academic demonstration and evaluation.

Do not upload:

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
- PDF report generation;
- frontend and backend prototype implementation.

Pending:

- usability questionnaire response collection;
- final usability analysis;
- final dissertation conclusion.

## Academic Disclaimer

This repository supports an MSc Artificial Intelligence dissertation project. The system is intended for academic research, demonstration, and evaluation only. It must not be used as a substitute for legal compliance, certified workplace risk assessment, occupational safety inspection, or competent professional judgement.

## Licence

This repository is currently intended for academic review. A licence will be added after the dissertation submission date. Please contact the author for any access or usage requests in the meantime.
