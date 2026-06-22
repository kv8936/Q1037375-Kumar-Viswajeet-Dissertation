from dataclasses import dataclass
from typing import Any

import joblib

from config import HAZARD_MODEL_PATH, RISK_MODEL_PATH


@dataclass(frozen=True)
class LoadedModels:
    hazard_model: Any | None
    risk_model: Any | None
    load_error: str

    @property
    def ready(self) -> bool:
        return self.hazard_model is not None and self.risk_model is not None



def load_models() -> LoadedModels:
    try:
        hazard_model = joblib.load(HAZARD_MODEL_PATH)
        risk_model = joblib.load(RISK_MODEL_PATH)
        return LoadedModels(hazard_model=hazard_model, risk_model=risk_model, load_error="")
    except Exception as exc:  # pragma: no cover - startup failure path
        return LoadedModels(hazard_model=None, risk_model=None, load_error=str(exc))
