from io import BytesIO
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from PIL import Image

from config import MAX_ENTERPRISE_IMAGES, MAX_LOCATION_CHARS, MAX_SCENARIO_CHARS, MIN_SCENARIO_CHARS, MIN_SCENARIO_WORDS, PRELOAD_CAPTION_MODEL, PRELOAD_TRANSLATION_MODEL, SAFETY_NOTE
from schemas import EnterprisePredictionResponse, HealthResponse, PredictionResponse
from services.captioner import get_captioner, is_captioner_ready
from services.models import LoadedModels, load_models
from services.prediction import predict_from_inputs
from services.translation import preload_translator
from services.hazard_model_service import load_hazard_model_v1_1
from services.v1_2_model_service import DEFAULT_MODEL_VERSION, load_v1_2_model

app = FastAPI(title="Hazard Chatbot Inference Service")

MODELS = load_models()
HAZARD_MODEL_V1_1 = load_hazard_model_v1_1()

if PRELOAD_CAPTION_MODEL:
    get_captioner()

if PRELOAD_TRANSLATION_MODEL:
    preload_translator()


def _scenario_has_enough_detail(value: str) -> bool:
    trimmed = value.strip()
    word_count = len([part for part in trimmed.split() if part.strip()])
    char_count = len(trimmed)
    return word_count >= MIN_SCENARIO_WORDS and char_count >= MIN_SCENARIO_CHARS


async def _extract_image_captions(images: list[UploadFile]) -> list[str]:
    captions: list[str] = []
    for index, image in enumerate(images, start=1):
        try:
            contents = await image.read()
            image_obj = Image.open(BytesIO(contents))
            from services.captioner import generate_caption

            caption = generate_caption(image_obj)
        except Exception:
            caption = ""

        if caption.strip():
            captions.append(caption.strip())
        else:
            captions.append(f"Image {index}: caption unavailable")
    return captions


def _normalize_uploaded_images(
    image: Optional[UploadFile],
    images: Optional[list[UploadFile]],
) -> list[UploadFile]:
    selected = []
    if image is not None:
        selected.append(image)
    if images:
        selected.extend(images)
    return selected


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    v1_2_model = load_v1_2_model()
    overall_status = "ok" if v1_2_model.ready else "error"
    return HealthResponse(
        status=overall_status,
        models_loaded=v1_2_model.ready,
        load_error=v1_2_model.load_error,
        caption_model_ready=is_captioner_ready(),
        model_version=str((v1_2_model.model_card or {}).get("model_name") or DEFAULT_MODEL_VERSION),
        v1_1_model_loaded=HAZARD_MODEL_V1_1.ready,
        v1_2_model_loaded=v1_2_model.ready,
    )


@app.post("/predict", response_model=PredictionResponse)
async def predict(
    scenario: str = Form(...),
    location: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    images: Optional[list[UploadFile]] = File(None),
) -> JSONResponse:
    v1_2_model = load_v1_2_model()
    if not v1_2_model.ready:
        raise HTTPException(status_code=500, detail=f"v1.2 model not loaded: {v1_2_model.load_error}")

    if not scenario.strip():
        raise HTTPException(status_code=400, detail="scenario is required")
    if len(scenario) > MAX_SCENARIO_CHARS:
        raise HTTPException(status_code=400, detail=f"scenario must be at most {MAX_SCENARIO_CHARS} characters")
    if not _scenario_has_enough_detail(scenario):
        raise HTTPException(status_code=400, detail="Please enter a workplace hazard description with at least 3 meaningful words and 15 characters.")
    if location is not None and len(location) > MAX_LOCATION_CHARS:
        raise HTTPException(status_code=400, detail=f"location must be at most {MAX_LOCATION_CHARS} characters")

    uploaded_images = _normalize_uploaded_images(image, images)
    if len(uploaded_images) > MAX_ENTERPRISE_IMAGES:
        raise HTTPException(status_code=400, detail=f"Up to {MAX_ENTERPRISE_IMAGES} images are allowed.")

    image_objects: list[Image.Image] = []
    for upload in uploaded_images:
        try:
            contents = await upload.read()
            image_objects.append(Image.open(BytesIO(contents)))
        except Exception:
            continue

    try:
        response = predict_from_inputs(MODELS, scenario, location, None, images=image_objects or None)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return JSONResponse(content=response)


class PredictV1_1Request(BaseModel):
    """Request body for v1.1 model prediction."""
    model_input: str
    severity_score: float


class PredictV1_1Response(BaseModel):
    """Response from v1.1 model prediction."""
    hazard_category: str
    hazard_confidence: float
    hazard_confidence_percent: str
    risk_level: str
    risk_method: str
    severity_score: float
    needs_manual_review: bool
    manual_review_reason: str


class PredictV1_1EnterpriseResponse(EnterprisePredictionResponse):
    pass


@app.post("/predict_v1_1", response_model=PredictV1_1Response)
def predict_v1_1(request: PredictV1_1Request) -> JSONResponse:
    """Predict hazard using v1.1 candidate model."""
    if not HAZARD_MODEL_V1_1.ready:
        raise HTTPException(
            status_code=500,
            detail=f"V1.1 model not loaded: {HAZARD_MODEL_V1_1.load_error}"
        )

    try:
        result = HAZARD_MODEL_V1_1.predict_v1_1_candidate(
            request.model_input,
            request.severity_score
        )
        return JSONResponse(content=result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/predict_v1_1_enterprise", response_model=PredictV1_1EnterpriseResponse)
async def predict_v1_1_enterprise(
    model_input: str = Form(...),
    severity_score: float = Form(...),
    location: Optional[str] = Form(None),
    images: Optional[list[UploadFile]] = File(None),
) -> JSONResponse:
    """Predict hazard using image-supported text inference."""
    if not HAZARD_MODEL_V1_1.ready:
        raise HTTPException(
            status_code=500,
            detail=f"V1.1 model not loaded: {HAZARD_MODEL_V1_1.load_error}"
        )

    enterprise_images = images or []
    if len(enterprise_images) > MAX_ENTERPRISE_IMAGES:
        raise HTTPException(status_code=400, detail="Up to 4 images are allowed.")

    try:
        image_captions = await _extract_image_captions(enterprise_images) if enterprise_images else []
        result = HAZARD_MODEL_V1_1.predict_v1_1_candidate(
            model_input=model_input,
            severity_score=severity_score,
            location=location,
            image_captions=image_captions,
        )
        return JSONResponse(content=result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="127.0.0.1", port=8001)
