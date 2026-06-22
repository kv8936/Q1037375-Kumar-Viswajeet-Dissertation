from dataclasses import dataclass
from functools import lru_cache
import logging
import re
from typing import Optional

from PIL import Image, ImageOps
import torch
from transformers import (
    Blip2ForConditionalGeneration,
    Blip2Processor,
    BlipForConditionalGeneration,
    BlipProcessor,
)

from config import CAPTION_MODEL_NAME


FALLBACK_IMAGE_CAPTION = "No reliable image caption generated"
_BLIP2_PROMPT = "Question: What is shown in this workplace safety image? Answer:"
_MEANINGLESS_VALUES = {
    "s",
    "image",
    "photo",
    "picture",
    "wall",
    "caption",
    "placeholder",
}


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CaptionMetadata:
    image_caption: str
    image_caption_status: str
    image_caption_model: str
    image_caption_warning: str = ""


def _clean(text: Optional[str]) -> str:
    return " ".join((text or "").strip().split())


def _reject_caption(reason: str) -> CaptionMetadata:
    return CaptionMetadata(
        image_caption=FALLBACK_IMAGE_CAPTION,
        image_caption_status="Failed",
        image_caption_model=CAPTION_MODEL_NAME,
        image_caption_warning=reason,
    )


def validate_generated_caption(text: Optional[str]) -> CaptionMetadata:
    cleaned = _clean(text)
    if not cleaned:
        return _reject_caption("Caption generation failed")
    if len(cleaned) < 8:
        return _reject_caption("Caption too short")

    words = re.findall(r"[a-z0-9]+", cleaned.lower())
    if len(words) <= 1:
        return _reject_caption("Caption must contain more than one meaningful word")
    if cleaned.lower() in _MEANINGLESS_VALUES:
        return _reject_caption("Caption is a meaningless placeholder")
    if words and all(word in _MEANINGLESS_VALUES for word in words):
        return _reject_caption("Caption is a meaningless placeholder")
    if len(set(words)) == 1:
        return _reject_caption("Caption repeats the same placeholder text")
    lowered = cleaned.lower()
    if "caption unavailable" in lowered or "no caption" in lowered:
        return _reject_caption("Caption model reported unavailable output")

    return CaptionMetadata(
        image_caption=cleaned,
        image_caption_status="Completed",
        image_caption_model=CAPTION_MODEL_NAME,
        image_caption_warning="",
    )


@lru_cache(maxsize=1)
def get_captioner():
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = CAPTION_MODEL_NAME.strip()
        model_kwargs = {"low_cpu_mem_usage": True}
        if device == "cuda":
            model_kwargs["torch_dtype"] = torch.float16

        if "blip2" in model_name.lower():
            processor = Blip2Processor.from_pretrained(model_name)
            model = Blip2ForConditionalGeneration.from_pretrained(model_name, **model_kwargs)
            model_kind = "blip2"
        else:
            processor = BlipProcessor.from_pretrained(model_name)
            model = BlipForConditionalGeneration.from_pretrained(model_name, **model_kwargs)
            model_kind = "blip"

        model = model.to(device)
        model.eval()
        logger.info("caption model loaded", extra={"model_name": model_name, "device": device, "model_kind": model_kind})
        return processor, model, device, model_kind
    except Exception as exc:
        logger.warning("caption model load failed: %s", exc)
        return None


def is_captioner_ready() -> bool:
    if get_captioner.cache_info().currsize == 0:
        return False
    return get_captioner() is not None


def generate_caption_metadata(image: Optional[Image.Image]) -> CaptionMetadata:
    if image is None:
        return CaptionMetadata(
            image_caption="",
            image_caption_status="Not available",
            image_caption_model=CAPTION_MODEL_NAME,
            image_caption_warning="No image provided",
        )

    captioner = get_captioner()
    if captioner is None:
        return _reject_caption("BLIP-2 caption model could not be loaded")

    try:
        normalized = ImageOps.exif_transpose(image).convert("RGB")
        processor, model, device, model_kind = captioner
        if model_kind == "blip2":
            inputs = processor(images=normalized, text=_BLIP2_PROMPT, return_tensors="pt")
        else:
            inputs = processor(images=normalized, return_tensors="pt")
        inputs = {
            key: value.to(device) if hasattr(value, "to") else value
            for key, value in inputs.items()
        }
        with torch.inference_mode():
            output_tokens = model.generate(**inputs, max_new_tokens=30)
        text = processor.batch_decode(output_tokens, skip_special_tokens=True)[0].strip()
        if model_kind == "blip2" and text.lower().startswith("answer:"):
            text = text.split(":", 1)[1].strip()
    except Exception as exc:
        return _reject_caption(f"BLIP-2 caption generation failed: {exc}")

    return validate_generated_caption(text)


def generate_caption(image: Image.Image) -> str:
    metadata = generate_caption_metadata(image)
    if metadata.image_caption_status != "Completed":
        return ""
    return metadata.image_caption
