from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import logging
import re
from typing import Optional, Protocol

from langdetect import DetectorFactory, detect_langs

from config import TRANSLATION_CHUNK_CHARS, TRANSLATION_MODEL_NAME

DetectorFactory.seed = 0

logger = logging.getLogger(__name__)


class TranslationError(RuntimeError):
    pass


class TextTranslator(Protocol):
    def translate_to_english(self, text: str) -> str:
        ...


@dataclass(frozen=True)
class NormalizedChatInput:
    original_input: str
    detected_language: str
    translated_model_input: str
    scenario_for_model: str
    location_for_model: str
    translation_strategy: str = "identity"
    translation_candidates: tuple["TranslationCandidate", ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TranslationCandidate:
    scenario_for_model: str
    location_for_model: str
    translated_model_input: str
    strategy: str


_GERMAN_HINTS = (
    " der ",
    " die ",
    " das ",
    " und ",
    " ist ",
    " nicht ",
    " mit ",
    " auf ",
    " für ",
    " bei ",
    " nasser ",
    " boden ",
    " nähe ",
    " büro",
    " eingang",
    " notausgang",
    " labor",
    " ladebereich",
    " kabel",
    " karton",
    " feuerlöscher",
    " feuerloescher",
    " gabelstapler",
    " chemikal",
)

_ENGLISH_NORMALIZATION_RULES = (
    (r"\bnasser ground\b", "wet floor"),
    (r"\bwet ground\b", "wet floor"),
    (r"\bslipping danger\b", "slip hazard"),
    (r"\bslip danger\b", "slip hazard"),
    (r"\boffice entry\b", "office entrance"),
    (r"\bcharging range\b", "loading bay"),
    (r"\bloading area\b", "loading bay"),
    (r"\blaboratory floor\b", "lab floor"),
    (r"\bcartons\b", "boxes"),
    (r"\bemergency output\b", "emergency exit"),
)


def _clean_text(text: Optional[str]) -> str:
    return (text or "").strip()


def detect_language(text: Optional[str]) -> str:
    value = _clean_text(text)
    if not value:
        return "unknown"

    lowered = f" {value.lower()} "
    if any(hint in lowered for hint in _GERMAN_HINTS) or any(ch in value for ch in "äöüßÄÖÜ"):
        return "de"

    try:
        languages = detect_langs(value)
        if languages:
            top = languages[0]
            if top.lang in {"de", "en"} and top.prob >= 0.6:
                return top.lang
    except Exception:
        pass

    return "en"


def _split_translation_chunks(text: str, max_chars: int) -> list[str]:
    value = _clean_text(text)
    if not value:
        return []

    if len(value) <= max_chars:
        return [value]

    segments = re.split(r"(?<=[.!?])\s+", value)
    chunks: list[str] = []
    current = ""

    for segment in segments:
        part = segment.strip()
        if not part:
            continue

        if len(part) > max_chars:
            words = part.split()
            buffer = ""
            for word in words:
                candidate = f"{buffer} {word}".strip()
                if buffer and len(candidate) > max_chars:
                    chunks.append(buffer)
                    buffer = word
                else:
                    buffer = candidate
            if buffer:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(buffer)
            continue

        candidate = f"{current} {part}".strip()
        if current and len(candidate) > max_chars:
            chunks.append(current)
            current = part
        else:
            current = candidate

    if current:
        chunks.append(current)

    return chunks or [value]


def _normalize_english_translation(text: str) -> str:
    value = _clean_text(text)
    if not value:
        return ""

    normalized = value
    for pattern, replacement in _ENGLISH_NORMALIZATION_RULES:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)

    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized or value


class HuggingFaceGermanToEnglishTranslator:
    def __init__(self, model_name: str = TRANSLATION_MODEL_NAME, max_chunk_chars: int = TRANSLATION_CHUNK_CHARS) -> None:
        self.model_name = model_name
        self.max_chunk_chars = max(64, max_chunk_chars)
        self._tokenizer = None
        self._model = None

    def _load(self):
        if self._tokenizer is None or self._model is None:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
        return self._tokenizer, self._model

    def preload(self) -> None:
        self._load()

    def _translate_chunk(self, text: str) -> str:
        import torch

        tokenizer, model = self._load()
        inputs = tokenizer(text, return_tensors="pt", truncation=True)
        with torch.inference_mode():
            output_tokens = model.generate(**inputs, max_new_tokens=160)
        translated = tokenizer.decode(output_tokens[0], skip_special_tokens=True).strip()
        if not translated:
            raise TranslationError("German-to-English translation returned an empty chunk")
        return translated

    def translate_to_english(self, text: str) -> str:
        value = _clean_text(text)
        if not value:
            return ""

        try:
            translated_parts = [
                self._translate_chunk(chunk)
                for chunk in _split_translation_chunks(value, self.max_chunk_chars)
            ]
        except Exception as exc:
            raise TranslationError(f"German-to-English translation failed: {exc}") from exc

        translated = " ".join(part.strip() for part in translated_parts if part.strip()).strip()
        if not translated:
            raise TranslationError("German-to-English translation returned an empty result")

        return _normalize_english_translation(translated)


class RuleBasedGermanToEnglishTranslator:
    _PHRASES = (
        (r"\bNasser Boden\b", "wet floor"),
        (r"\bNasse[rnms]? Boden\b", "wet floor"),
        (r"\bBoden\b", "floor"),
        (r"\bRutschgefahr\b", "slip hazard"),
        (r"\bin der Nähe des\b", "near the"),
        (r"\bin der Nähe von\b", "near"),
        (r"\bNähe des\b", "near the"),
        (r"\bBüroeingangs\b", "office entrance"),
        (r"\bBüroeingang\b", "office entrance"),
        (r"\bBuroeingangs\b", "office entrance"),
        (r"\bBuroeingang\b", "office entrance"),
        (r"\bNotausgang Flur\b", "emergency exit corridor"),
        (r"\bNotausgang\b", "emergency exit"),
        (r"\bEingangsbereich\b", "entrance area"),
        (r"\bEingang\b", "entrance"),
        (r"\bLadebereich\b", "loading bay"),
        (r"\bLaborboden\b", "lab floor"),
        (r"\bnahe dem\b", "near the"),
        (r"\bnahe\b", "near"),
        (r"\bneben\b", "next to"),
        (r"\bSzenario\b", "Scenario"),
        (r"\bKartons\b", "boxes"),
        (r"\bFeuerlöscher\b", "fire extinguisher"),
        (r"\bFeuerloescher\b", "fire extinguisher"),
        (r"\bGabelstapler\b", "forklift"),
        (r"\bFußgängern\b", "pedestrians"),
        (r"\bFussgängern\b", "pedestrians"),
        (r"\bFussgaengern\b", "pedestrians"),
        (r"\bFußgänger\b", "pedestrian"),
        (r"\bFussgänger\b", "pedestrian"),
        (r"\bFussgaenger\b", "pedestrian"),
        (r"\bChemikalie\b", "chemical"),
        (r"\bDämpfen\b", "fumes"),
        (r"\bDaempfen\b", "fumes"),
        (r"\bverschüttet\b", "spilled"),
        (r"\bverschuettet\b", "spilled"),
        (r"\bLose Kabel\b", "Loose cables"),
        (r"\bLose Kabeln\b", "Loose cables"),
        (r"\bGang\b", "corridor"),
        (r"\bBüroflur\b", "office corridor"),
        (r"\bBuroflur\b", "office corridor"),
        (r"\bLager\b", "storage area"),
        (r"\bFlur\b", "corridor"),
        (r"\bblockiert\b", "blocked"),
        (r"\bblockieren\b", "block"),
        (r"\bverkabelung\b", "cabling"),
        (r"\bKabel\b", "cable"),
        (r"\bKabeln\b", "cables"),
        (r"\bdem\b", "the"),
        (r"\bden\b", "the"),
        (r"\bim\b", "in the"),
        (r"\bder\b", "the"),
        (r"\bdie\b", "the"),
        (r"\bdas\b", "the"),
        (r"\bund\b", "and"),
        (r"\bist\b", "is"),
        (r"\bsind\b", "are"),
        (r"\bmit\b", "with"),
        (r"\bnear\b", "near"),
        (r"\bzu\b", "to"),
        (r"\bauf\b", "on"),
        (r"\bin\b", "in"),
        (r"\bBüro\b", "office"),
        (r"\bBuro\b", "office"),
    )

    def translate_to_english(self, text: str) -> str:
        value = _clean_text(text)
        if not value:
            return ""

        translated = value
        for pattern, replacement in self._PHRASES:
            translated = re.sub(pattern, replacement, translated, flags=re.IGNORECASE)

        translated = re.sub(r"\s+", " ", translated).strip()
        return translated or value


class HybridGermanToEnglishTranslator:
    def __init__(
        self,
        primary: Optional[HuggingFaceGermanToEnglishTranslator] = None,
        fallback: Optional[TextTranslator] = None,
    ) -> None:
        self.primary = primary or HuggingFaceGermanToEnglishTranslator()
        self.fallback = fallback or RuleBasedGermanToEnglishTranslator()

    def preload(self) -> None:
        try:
            self.primary.preload()
        except Exception as exc:
            logger.warning("Translation model preload failed: %s", exc)

    def translate_to_english(self, text: str) -> str:
        value = _clean_text(text)
        if not value:
            return ""

        try:
            translated = self.primary.translate_to_english(value)
            if translated.strip():
                return translated.strip()
        except TranslationError as exc:
            logger.warning("Falling back to rule-based German translation: %s", exc)

        return self.fallback.translate_to_english(value)


@lru_cache(maxsize=1)
def get_translator() -> TextTranslator:
    return HybridGermanToEnglishTranslator()


def preload_translator() -> None:
    translator = get_translator()
    preload = getattr(translator, "preload", None)
    if callable(preload):
        preload()


def build_original_input(scenario: str, location: Optional[str], image_caption: str) -> str:
    parts = [f"Workplace scenario: {_clean_text(scenario)}"]
    location_text = _clean_text(location)
    if location_text:
        parts.append(f"Location: {location_text}")
    caption_text = _clean_text(image_caption)
    if caption_text:
        parts.append(f"Visual context from image caption: {caption_text}")
    return " | ".join(parts)


def build_model_input(scenario: str, location: Optional[str], image_caption: str) -> str:
    return build_original_input(scenario, location, image_caption)


def _candidate_key(scenario: str, location: str) -> tuple[str, str]:
    return (scenario.strip().lower(), location.strip().lower())


def _build_candidate(scenario: str, location: str, image_caption: str, strategy: str) -> TranslationCandidate:
    scenario_value = _clean_text(scenario)
    location_value = _clean_text(location)
    return TranslationCandidate(
        scenario_for_model=scenario_value,
        location_for_model=location_value,
        translated_model_input=build_model_input(scenario_value, location_value, image_caption),
        strategy=strategy,
    )


def build_translation_candidates(
    scenario: str,
    location: Optional[str],
    image_caption: str,
    translator: Optional[TextTranslator] = None,
) -> list[TranslationCandidate]:
    scenario_lang = detect_language(scenario)
    location_lang = detect_language(location)
    scenario_text = _clean_text(scenario)
    location_text = _clean_text(location)

    if scenario_lang == "en" and (not location_text or location_lang == "en"):
        return [_build_candidate(scenario_text, location_text, image_caption, "identity")]

    translator = translator or get_translator()
    candidates: list[TranslationCandidate] = []
    seen: set[tuple[str, str]] = set()

    def append_candidate(candidate: TranslationCandidate) -> None:
        key = _candidate_key(candidate.scenario_for_model, candidate.location_for_model)
        if key in seen:
            return
        seen.add(key)
        candidates.append(candidate)

    engines: list[tuple[str, TextTranslator]] = []
    if isinstance(translator, HybridGermanToEnglishTranslator):
        engines.append(("hf", translator.primary))
        engines.append(("fallback", translator.fallback))
    else:
        engines.append(("translated", translator))

    for strategy, engine in engines:
        try:
            translated_scenario = scenario_text
            translated_location = location_text
            if translated_scenario and scenario_lang != "en":
                translated_scenario = engine.translate_to_english(translated_scenario)
            if translated_location and location_lang != "en":
                translated_location = engine.translate_to_english(translated_location)
            append_candidate(_build_candidate(translated_scenario, translated_location, image_caption, strategy))
        except TranslationError:
            continue

    if not candidates:
        append_candidate(_build_candidate(scenario_text, location_text, image_caption, "identity"))

    return candidates


def normalize_chat_input(
    scenario: str,
    location: Optional[str],
    image_caption: str,
    translator: Optional[TextTranslator] = None,
) -> NormalizedChatInput:
    scenario_lang = detect_language(scenario)
    location_lang = detect_language(location)
    detected_language = "de" if "de" in {scenario_lang, location_lang} else "en"

    original_input = build_original_input(scenario, location, image_caption)

    candidates = tuple(build_translation_candidates(scenario, location, image_caption, translator=translator))
    primary = candidates[0]

    return NormalizedChatInput(
        original_input=original_input,
        detected_language=detected_language,
        translated_model_input=primary.translated_model_input,
        scenario_for_model=primary.scenario_for_model,
        location_for_model=primary.location_for_model,
        translation_strategy=primary.strategy,
        translation_candidates=candidates,
    )