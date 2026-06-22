import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
MODELS_ROOT_CANDIDATES = [BASE_DIR / "models", BASE_DIR.parent / "models"]


def _env_int(name: str, default: int) -> int:
	try:
		return int(os.getenv(name, str(default)))
	except ValueError:
		return default


def _env_str(name: str, default: str) -> str:
	value = os.getenv(name)
	if value is None:
		return default
	cleaned = value.strip()
	return cleaned or default


def _env_bool(name: str, default: bool) -> bool:
	value = os.getenv(name)
	if value is None:
		return default
	return value.strip().lower() in {"1", "true", "yes", "on"}


def _first_existing_path(*paths: Path) -> Path:
	for path in paths:
		if path.exists():
			return path
	return paths[0]


MODELS_ROOT = _first_existing_path(*MODELS_ROOT_CANDIDATES)

BASELINE_MODEL_DIR = MODELS_ROOT / "v1_baseline"
HAZARD_MODEL_PATH = BASELINE_MODEL_DIR / "hazard_category_classifier_tfidf_logreg.joblib"
RISK_MODEL_PATH = BASELINE_MODEL_DIR / "risk_level_classifier_tfidf_logreg.joblib"

# v1.1 candidate model paths
ML_MODELS_DIR = MODELS_ROOT / "v1_1_candidate"
HAZARD_V1_1_MODEL_PATH = ML_MODELS_DIR / "hazard_category_model_v1_1_candidate.joblib"
HAZARD_V1_1_CONFIG_PATH = ML_MODELS_DIR / "hybrid_model_config_v1_1_candidate.json"

V1_2_MODEL_DIR_CANDIDATES = [
	MODELS_ROOT / "v1_2_multimodal_sbert_svm_candidate" / "final_export_v1_2_multimodal_sbert_svm_candidate_20260610_180546",
	BASE_DIR / "models" / "v1_2_multimodal_sbert_svm_candidate" / "final_export_v1_2_multimodal_sbert_svm_candidate_20260610_180546",
	BASE_DIR.parent / "models" / "v1_2_multimodal_sbert_svm_candidate" / "final_export_v1_2_multimodal_sbert_svm_candidate_20260610_180546",
]

for candidate in V1_2_MODEL_DIR_CANDIDATES:
	if candidate.exists():
		V1_2_MODEL_DIR = candidate
		break
else:
	V1_2_MODEL_DIR = V1_2_MODEL_DIR_CANDIDATES[0]

V1_2_MODEL_PATH = V1_2_MODEL_DIR / "hazard_classifier_sbert_linear_svm.joblib"
V1_2_LABELS_PATH = V1_2_MODEL_DIR / "hazard_labels.json"
V1_2_RISK_RULE_PATH = V1_2_MODEL_DIR / "risk_rule_severity_score.json"
V1_2_MANUAL_REVIEW_RULE_PATH = V1_2_MODEL_DIR / "manual_review_rule.json"
V1_2_MODEL_CARD_PATH = V1_2_MODEL_DIR / "model_card_v1_2_multimodal_sbert_svm_candidate.json"

CAPTION_MODEL_NAME = _env_str("CAPTION_MODEL_NAME", "Salesforce/blip-image-captioning-base")
PRELOAD_CAPTION_MODEL = _env_bool("PRELOAD_CAPTION_MODEL", True)
TRANSLATION_MODEL_NAME = _env_str("TRANSLATION_MODEL_NAME", "Helsinki-NLP/opus-mt-de-en")
PRELOAD_TRANSLATION_MODEL = _env_bool("PRELOAD_TRANSLATION_MODEL", False)
TRANSLATION_CHUNK_CHARS = _env_int("TRANSLATION_CHUNK_CHARS", 320)
SAFETY_NOTE = "This AI output is intended for decision support only and should be reviewed by a competent person before workplace safety decisions are made."
MAX_ENTERPRISE_IMAGES = _env_int("MAX_ENTERPRISE_IMAGES", 4)
MIN_SCENARIO_WORDS = _env_int("MIN_SCENARIO_WORDS", 3)
MIN_SCENARIO_CHARS = _env_int("MIN_SCENARIO_CHARS", 15)
MAX_SCENARIO_CHARS = _env_int("MAX_SCENARIO_CHARS", 4000)
MAX_LOCATION_CHARS = _env_int("MAX_LOCATION_CHARS", 256)
