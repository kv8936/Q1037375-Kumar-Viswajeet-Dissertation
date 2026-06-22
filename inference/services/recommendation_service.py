"""Hazard-specific and risk-specific recommendation generator for enterprise output."""

from __future__ import annotations

import re
from typing import Optional


BROKEN_STEP_TERMS = ("broken step", "damaged step", "step defect", "broken stair", "broken stairs", "damaged stair")
WET_FLOOR_TERMS = ("wet floor", "spill", "spilled", "spilled liquid", "slippery", "wet surface")
ELECTRICAL_TERMS = ("exposed wiring", "frayed cable", "damaged cable", "overloaded socket", "open electrical panel", "damaged plug", "temporary wiring", "wet electrical area")
FIRE_TERMS = ("fire extinguisher", "fire exit", "emergency exit", "escape route", "evacuation route", "fire equipment")
OBSTRUCTION_TERMS = ("blocked walkway", "blocked corridor", "blocked doorway", "stored items", "boxes", "clutter", "obstruction", "blocking")
ERGONOMIC_TERMS = ("awkward lifting", "manual handling", "poor workstation", "awkward posture", "repetitive movement", "long standing")
VISIBILITY_TERMS = ("poor lighting", "blocked signage", "obscured view", "low visibility", "missing warning sign", "unclear route")

_SUB_HAZARD_DE = {
    "broken step": "defekte Stufe",
    "uneven floor": "unebener Boden",
    "wet floor": "nasser Boden",
    "loose cable": "loses Kabel",
    "loose rug": "lockerer Teppich",
    "icy surface": "vereiste Oberfläche",
    "cluttered walkway": "zugestellter Gehweg",
    "slippery ramp": "rutschige Rampe",
    "exposed wiring": "freiliegende Verkabelung",
    "frayed cable": "ausgefranstes Kabel",
    "overloaded socket": "überlastete Steckdose",
    "wet electrical area": "nasser Elektrobereich",
    "damaged plug": "beschädigter Stecker",
    "temporary wiring": "provisorische Verkabelung",
    "open electrical panel": "offener Schaltschrank",
    "blocked fire extinguisher": "blockierter Feuerlöscher",
    "blocked fire exit": "blockierter Fluchtweg",
    "blocked emergency exit": "blockierter Notausgang",
    "stored items in access route": "gelagerte Gegenstände im Zugangsweg",
    "blocked walkway": "blockierter Gehweg",
    "blocked equipment access": "blockierter Gerätezugang",
    "awkward lifting": "ungünstiges Heben",
    "poor workstation setup": "ungünstige Arbeitsplatzgestaltung",
    "long standing without support": "langes Stehen ohne Entlastung",
    "repetitive movement": "wiederholte Bewegung",
    "manual handling strain": "Belastung beim manuellen Handling",
    "awkward posture": "ungünstige Körperhaltung",
    "poor lighting": "unzureichende Beleuchtung",
    "blocked signage": "verdeckte Beschilderung",
    "obscured view": "eingeschränkte Sicht",
    "low visibility walkway": "Bereich mit geringer Sicht",
    "missing warning sign": "fehlendes Warnschild",
    "unclear route marking": "unklare Wegmarkierung",
    "spill or contamination": "Verschüttung oder Verunreinigung",
}


def _lang_code(language: Optional[str]) -> str:
    return "de" if (language or "").strip().lower().startswith("de") else "en"


def _t(language: Optional[str], en: str, de: str) -> str:
    return de if _lang_code(language) == "de" else en


def _localized_sub_hazard(language: Optional[str], sub_hazard: str) -> str:
    if _lang_code(language) != "de":
        return sub_hazard
    return _SUB_HAZARD_DE.get(sub_hazard, sub_hazard)


def _clean(text: Optional[str]) -> str:
    return (text or "").strip()


def _join_context(*parts: Optional[str]) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip()).lower()


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _detect_sub_hazard(hazard_category: str, scenario: str, location: Optional[str], image_context: str) -> str:
    text = _join_context(hazard_category, scenario, location, image_context)

    if "slip" in text or "trip" in text:
        if _contains_any(text, BROKEN_STEP_TERMS):
            return "broken step"
        if _contains_any(text, ("uneven floor", "uneven surface", "damaged flooring")):
            return "uneven floor"
        if _contains_any(text, WET_FLOOR_TERMS):
            return "wet floor"
        if _contains_any(text, ("loose cable", "trailing cable", "cable across")):
            return "loose cable"
        if _contains_any(text, ("loose rug", "loose mat")):
            return "loose rug"
        if _contains_any(text, ("icy", "ice", "frozen")):
            return "icy surface"
        if _contains_any(text, ("cluttered walkway", "cluttered route")):
            return "cluttered walkway"
        if _contains_any(text, ("slippery ramp",)):
            return "slippery ramp"
        return ""

    if "electrical" in text:
        if _contains_any(text, ("exposed wiring", "wiring exposed")):
            return "exposed wiring"
        if _contains_any(text, ("frayed cable", "damaged cable")):
            return "frayed cable"
        if _contains_any(text, ("overloaded socket", "socket overloaded")):
            return "overloaded socket"
        if _contains_any(text, ("wet electrical area", "wet area")):
            return "wet electrical area"
        if _contains_any(text, ("damaged plug",)):
            return "damaged plug"
        if _contains_any(text, ("temporary wiring", "temporary cable")):
            return "temporary wiring"
        if _contains_any(text, ("open electrical panel", "open panel")):
            return "open electrical panel"
        return ""

    if "fire" in text or "obstruction" in text or "exit" in text:
        if _contains_any(text, ("blocked fire extinguisher", "fire extinguisher access", "extinguisher access")):
            return "blocked fire extinguisher"
        if _contains_any(text, ("blocked fire exit", "blocked exit", "fire exit")):
            return "blocked fire exit"
        if _contains_any(text, ("blocked emergency exit", "emergency exit")):
            return "blocked emergency exit"
        if _contains_any(text, ("stored items in access route", "stored items", "boxes", "clutter")):
            return "stored items in access route"
        if _contains_any(text, ("blocked walkway", "blocked corridor", "blocked doorway")):
            return "blocked walkway"
        if _contains_any(text, ("blocked equipment access",)):
            return "blocked equipment access"
        return ""

    if "ergonomic" in text or "manual handling" in text:
        if _contains_any(text, ("awkward lifting", "manual handling")):
            return "awkward lifting"
        if _contains_any(text, ("poor workstation setup", "poor workstation")):
            return "poor workstation setup"
        if _contains_any(text, ("long standing", "standing without support")):
            return "long standing without support"
        if _contains_any(text, ("repetitive movement",)):
            return "repetitive movement"
        if _contains_any(text, ("manual handling strain",)):
            return "manual handling strain"
        if _contains_any(text, ("awkward posture",)):
            return "awkward posture"
        return ""

    if "visibility" in text:
        if _contains_any(text, ("poor lighting",)):
            return "poor lighting"
        if _contains_any(text, ("blocked signage",)):
            return "blocked signage"
        if _contains_any(text, ("obscured view",)):
            return "obscured view"
        if _contains_any(text, ("low visibility walkway", "low visibility")):
            return "low visibility walkway"
        if _contains_any(text, ("missing warning sign",)):
            return "missing warning sign"
        if _contains_any(text, ("unclear route marking",)):
            return "unclear route marking"
        return ""

    if "chemical" in text or "spill" in text:
        if _contains_any(text, ("chemical spill", "spill", "contamination")):
            return "spill or contamination"

    return ""


def _risk_timeframe(language: Optional[str], risk_level: str, needs_more_info: bool) -> str:
    if needs_more_info:
        return _t(language, "Hold pending clarification or competent-person review.", "Zurückhalten bis zur Klärung oder Prüfung durch eine fachkundige Person.")

    level = risk_level.strip().lower()
    if level == "high":
        return _t(language, "Same day / before normal work continues.", "Am selben Tag / bevor die normale Arbeit fortgesetzt wird.")
    if level == "medium":
        return _t(language, "Within 24–72 hours where staff exposure is likely.", "Innerhalb von 24–72 Stunden, wenn eine Exposition von Mitarbeitenden wahrscheinlich ist.")
    return _t(language, "Within 7–30 days during the normal maintenance cycle.", "Innerhalb von 7–30 Tagen im regulären Wartungszyklus.")


def _manual_review_note(
    language: Optional[str],
    needs_manual_review: bool,
    needs_more_info: bool,
    image_uploaded: bool,
    image_caption_available: bool,
    hazard_confidence: float,
) -> Optional[str]:
    if not needs_manual_review and not needs_more_info:
        return None

    notes = [
        _t(language, "This output should be reviewed by a competent person before action is taken because the model flagged uncertainty, ambiguity, or incomplete visual interpretation.", "Diese Ausgabe sollte vor Maßnahmen von einer fachkundigen Person geprüft werden, da das Modell Unsicherheit, Mehrdeutigkeit oder eine unvollständige visuelle Interpretation erkannt hat.")
    ]
    if image_uploaded and not image_caption_available:
        notes.append(_t(language, "Image evidence was uploaded, but the local model did not interpret the visual content. Visual confirmation is required during manual review.", "Bildmaterial wurde hochgeladen, aber das lokale Modell hat den visuellen Inhalt nicht interpretiert. Eine visuelle Bestätigung ist im Rahmen der manuellen Prüfung erforderlich."))
    if hazard_confidence < 0.40:
        notes.append(_t(language, "The model confidence is low. Ask the user for more operational detail before relying on the prediction.", "Die Modellkonfidenz ist gering. Bitte den Nutzer um weitere operative Details, bevor die Vorhersage verwendet wird."))
    return " ".join(notes)


def _clarification_question(language: Optional[str], hazard_category: str, sub_hazard: str, location_text: str) -> str:
    hazard_label = hazard_category.strip().lower()
    sub_label = sub_hazard.strip().lower()
    location_label = location_text.strip() or "the affected area"

    if sub_label == "broken step" or ("slip" in hazard_label or "trip" in hazard_label):
        return _t(language, f"Can you confirm whether the broken step in {location_label} is on a main walking route, whether it is already marked or blocked off, and how often staff use this corridor?", f"Können Sie bestätigen, ob sich die defekte Stufe in {location_label} auf einem Hauptgehweg befindet, ob sie bereits markiert oder abgesperrt ist und wie häufig Mitarbeitende diesen Flur nutzen?")

    if "fire" in hazard_label or "obstruction" in hazard_label or "exit" in hazard_label:
        return _t(language, "Can you confirm whether the obstruction blocks fire equipment, an emergency exit, or a normal walkway, and whether staff need this route during operations?", "Können Sie bestätigen, ob die Blockade Feuerlöscher, einen Notausgang oder einen normalen Gehweg betrifft und ob Mitarbeitende diese Route im Betrieb benötigen?")

    if "electrical" in hazard_label:
        return _t(language, "Can you confirm whether the cable or equipment is live, damaged, wet, overheating, or within frequent staff reach?", "Können Sie bestätigen, ob das Kabel oder Gerät unter Spannung steht, beschädigt, nass oder überhitzt ist oder sich in häufiger Reichweite von Mitarbeitenden befindet?")

    if "ergonomic" in hazard_label:
        return _t(language, "Can you confirm the load weight, task frequency, posture, and whether the worker has support equipment available?", "Können Sie das Gewicht der Last, die Häufigkeit der Tätigkeit, die Körperhaltung und das Vorhandensein von Hilfsmitteln bestätigen?")

    if "visibility" in hazard_label:
        return _t(language, "Can you confirm whether the visibility issue affects stairs, machinery, vehicle movement, warning signs, or emergency routes?", "Können Sie bestätigen, ob das Sichtproblem Treppen, Maschinen, Fahrzeugbewegungen, Warnschilder oder Fluchtwege betrifft?")

    return _t(language, "Please confirm the exact hazard location, what object or substance is involved, and whether staff are frequently exposed.", "Bitte bestätigen Sie den genauen Gefahrenort, den beteiligten Gegenstand oder Stoff und ob Mitarbeitende regelmäßig exponiert sind.")


def _template_for(
    language: Optional[str],
    hazard_category: str,
    sub_hazard: str,
    location_text: str,
    risk_level: str,
    needs_more_info: bool,
) -> dict:
    hazard_label = hazard_category.strip() or "Hazard"
    sub_label = sub_hazard.strip().lower()
    location_label = location_text.strip() or "the affected area"
    timeframe = _risk_timeframe(language, risk_level, needs_more_info)
    localized_sub_hazard = _localized_sub_hazard(language, sub_hazard)

    if hazard_label.lower().startswith("slip") and sub_label == "broken step":
        return {
            "hazard_specific_finding": _t(language, f"A broken step has been identified in {location_label}, creating a slip/trip hazard during normal staff movement.", f"In {location_label} wurde eine defekte Stufe festgestellt, die während normaler Bewegungen von Mitarbeitenden eine Rutsch-/Stolpergefahr darstellt."),
            "immediate_containment": _t(language, f"Mark the damaged step with visible warning signage or barrier tape. If the defect affects safe footing, restrict use of the route and provide an alternative walkway in {location_label}.", f"Kennzeichnen Sie die defekte Stufe sichtbar mit Warnhinweisen oder Absperrband. Wenn der Mangel die sichere Begehung beeinträchtigt, sperren Sie den Weg und stellen Sie in {location_label} eine alternative Route bereit."),
            "corrective_action": _t(language, "Assign Facilities or Maintenance to repair or replace the damaged step surface.", "Beauftragen Sie den Gebäudedienst / die Instandhaltung mit der Reparatur oder dem Austausch der defekten Stufe."),
            "responsible_owner": _t(language, "Facilities / Maintenance team, with review by the responsible safety lead if the route is frequently used.", "Gebäudedienst / Instandhaltung, mit Prüfung durch die zuständige Sicherheitsverantwortung, wenn der Weg häufig genutzt wird."),
            "target_completion": timeframe,
            "verification": _t(language, "After repair, inspect the step to confirm that it is stable, level, visible, and safe for normal use.", "Nach der Reparatur ist die Stufe auf Stabilität, Ebenheit, Sichtbarkeit und sichere Nutzung zu prüfen."),
            "escalation": _t(language, "Escalate immediately if the corridor is a main walking route, emergency route, or if staff must continue using the damaged step before repair.", "Sofort eskalieren, wenn es sich um einen Hauptgehweg oder Fluchtweg handelt oder Mitarbeitende die defekte Stufe vor der Reparatur weiter nutzen müssen."),
            "closure_condition": _t(language, "Keep the case open until the defect is repaired and the walking route is confirmed safe.", "Der Fall bleibt offen, bis der Mangel behoben und die Begehbarkeit als sicher bestätigt wurde."),
            "manual_review_note": None,
        }

    if hazard_label.lower().startswith("slip") and sub_label in {"wet floor", "spill or contamination"}:
        return {
            "hazard_specific_finding": _t(language, f"A wet or contaminated walking surface has been identified in {location_label}, creating a slip risk for staff.", f"In {location_label} wurde eine nasse oder verunreinigte Gehfläche festgestellt, die eine Rutschgefahr für Mitarbeitende darstellt."),
            "immediate_containment": _t(language, "Place warning signs, restrict access if needed, and prevent staff from walking through the affected area.", "Warnschilder aufstellen, den Zugang bei Bedarf beschränken und verhindern, dass Mitarbeitende den betroffenen Bereich begehen."),
            "corrective_action": _t(language, "Clean and dry the surface, identify the source of the spill, and prevent recurrence.", "Die Fläche reinigen und trocknen, die Ursache der Verschüttung identifizieren und Wiederholungen verhindern."),
            "responsible_owner": _t(language, "Facilities / Cleaning team, with area supervisor follow-up.", "Gebäudedienst / Reinigungsteam mit Nachverfolgung durch die Bereichsleitung."),
            "target_completion": timeframe,
            "verification": _t(language, "Confirm the surface is dry, clear, and safe before removing warning signs.", "Vor dem Entfernen der Warnschilder sicherstellen, dass die Fläche trocken, frei und sicher ist."),
            "escalation": _t(language, "Escalate if the spill source cannot be controlled or if the area is on a main route.", "Eskaliert wird, wenn die Verschüttungsquelle nicht beherrscht werden kann oder der Bereich ein Hauptweg ist."),
            "closure_condition": _t(language, "Close only after the surface is dry and the cause has been addressed.", "Erst schließen, wenn die Fläche trocken ist und die Ursache behoben wurde."),
            "manual_review_note": None,
        }

    if "electrical" in hazard_label.lower() and sub_label in {"exposed wiring", "frayed cable", "damaged cable", "wet electrical area", "temporary wiring", "open electrical panel", "damaged plug", "overloaded socket"}:
        return {
            "hazard_specific_finding": _t(language, f"Damaged or exposed electrical equipment has been identified in {location_label}, creating potential contact, shock, or ignition risk.", f"In {location_label} wurde beschädigte oder freiliegende Elektrotechnik festgestellt, die ein Kontakt-, Stromschlag- oder Zündrisiko darstellt."),
            "immediate_containment": _t(language, "Prevent staff contact with the affected cable or equipment. Isolate the area if needed and stop use until it is controlled.", "Kontakt von Mitarbeitenden mit dem betroffenen Kabel oder Gerät verhindern. Bei Bedarf den Bereich absperren und die Nutzung bis zur Sicherung stoppen."),
            "corrective_action": _t(language, "Arrange inspection and repair by a qualified electrician or competent technical person.", "Eine Inspektion und Reparatur durch eine qualifizierte Elektrofachkraft oder fachkundige Person veranlassen."),
            "responsible_owner": _t(language, "Facilities / Electrical Maintenance / Safety Lead.", "Gebäudedienst / Elektroinstandhaltung / Sicherheitsleitung."),
            "target_completion": timeframe,
            "verification": _t(language, "Confirm the repair has been completed and the equipment is safe before use resumes.", "Vor Wiederaufnahme der Nutzung bestätigen, dass die Reparatur abgeschlossen und das Gerät sicher ist."),
            "escalation": _t(language, "Escalate immediately if the cable is live, wet, sparking, overheating, or within frequent staff reach.", "Sofort eskalieren, wenn das Kabel unter Spannung steht, nass ist, Funken bildet, überhitzt oder häufig von Mitarbeitenden erreichbar ist."),
            "closure_condition": _t(language, "Close only after electrical safety has been verified by a competent person.", "Erst schließen, wenn die elektrische Sicherheit durch eine fachkundige Person bestätigt wurde."),
            "manual_review_note": None,
        }

    if ("fire" in hazard_label.lower() or "obstruction" in hazard_label.lower()) and sub_label in {
        "blocked fire extinguisher",
        "blocked fire exit",
        "blocked emergency exit",
        "stored items in access route",
        "blocked walkway",
        "blocked equipment access",
    }:
        is_fire_equipment = "extinguisher" in sub_label or "fire exit" in sub_label or "emergency exit" in sub_label
        return {
            "hazard_specific_finding": _t(language, f"Access to fire-safety equipment or an emergency route is obstructed in {location_label}.", f"Der Zugang zu Brandschutzausrüstung oder Fluchtweg ist in {location_label} blockiert."),
            "immediate_containment": _t(language, "Remove stored items or obstructions from the fire equipment, emergency exit, or escape route immediately.", "Lagermaterial oder Hindernisse sofort von Brandschutzausrüstung, Notausgang oder Fluchtweg entfernen."),
            "corrective_action": _t(language, "Restore clear access and reinforce housekeeping controls to prevent repeated obstruction.", "Den freien Zugang wiederherstellen und Ordnungskontrollen verstärken, um wiederholte Blockaden zu verhindern."),
            "responsible_owner": _t(language, "Area Supervisor / Fire Safety Lead / Facilities team.", "Bereichsleitung / Brandschutzverantwortliche / Gebäudedienst."),
            "target_completion": "Same day / before normal work continues." if is_fire_equipment or risk_level.strip().lower() == "high" else timeframe,
            "verification": _t(language, "Confirm that the fire equipment, exit, or escape route is fully accessible and visibly marked.", "Bestätigen, dass Brandschutzausrüstung, Ausgang oder Fluchtweg vollständig zugänglich und sichtbar gekennzeichnet sind."),
            "escalation": _t(language, "Escalate immediately if the obstruction affects an emergency exit, fire extinguisher, evacuation route, or occupied work area.", "Sofort eskalieren, wenn die Blockade einen Notausgang, Feuerlöscher, Evakuierungsweg oder einen besetzten Arbeitsbereich betrifft."),
            "closure_condition": _t(language, "Close only after access is clear and the responsible person confirms the route or equipment is usable.", "Erst schließen, wenn der Zugang frei ist und die verantwortliche Person die Nutzbarkeit bestätigt."),
            "manual_review_note": None,
        }

    if "ergonomic" in hazard_label.lower() and sub_label:
        return {
            "hazard_specific_finding": _t(language, f"The task in {location_label} appears to involve {sub_label.replace('_', ' ')}.", f"Die Tätigkeit in {location_label} scheint {localized_sub_hazard or sub_label} zu beinhalten."),
            "immediate_containment": _t(language, "Pause or reduce the task if discomfort, overreaching, twisting, or excessive load handling is observed.", "Tätigkeit pausieren oder reduzieren, wenn Beschwerden, Überstrecken, Verdrehungen oder zu hohe Lasten beobachtet werden."),
            "corrective_action": _t(language, "Adjust the work method, reduce load weight, provide handling aids, or redesign the workstation layout.", "Arbeitsmethode anpassen, Lastgewicht reduzieren, Hilfsmittel bereitstellen oder die Arbeitsplatzgestaltung überarbeiten."),
            "responsible_owner": _t(language, "Line Manager / Safety Lead / Ergonomics or Occupational Health reviewer.", "Vorgesetzte/r / Sicherheitsverantwortliche/r / Ergonomie- oder Arbeitsmedizinprüfung."),
            "target_completion": timeframe,
            "verification": _t(language, "Confirm that the revised task reduces awkward posture, force, repetition, or duration.", "Bestätigen, dass die überarbeitete Tätigkeit ungünstige Haltung, Kraftaufwand, Wiederholung oder Dauer reduziert."),
            "escalation": _t(language, "Escalate if the worker reports pain, the task is repeated frequently, or mechanical support is unavailable.", "Eskaliert wird, wenn Schmerzen gemeldet werden, die Tätigkeit häufig wiederholt wird oder mechanische Unterstützung fehlt."),
            "closure_condition": _t(language, "Close only after the task has been reviewed and the improved working method is confirmed.", "Erst schließen, wenn die Tätigkeit geprüft und die verbesserte Arbeitsweise bestätigt wurde."),
            "manual_review_note": None,
        }

    if "visibility" in hazard_label.lower() and sub_label:
        return {
            "hazard_specific_finding": _t(language, f"Reduced visibility has been identified in {location_label}, which may prevent staff from seeing hazards, routes, signage, or moving equipment.", f"In {location_label} wurde eingeschränkte Sicht festgestellt, wodurch Mitarbeitende Gefahren, Wege, Schilder oder bewegliche Geräte möglicherweise nicht erkennen können."),
            "immediate_containment": _t(language, "Warn staff of the reduced-visibility area and restrict activity if the visibility issue affects safe movement or machinery use.", "Mitarbeitende auf den Bereich mit eingeschränkter Sicht hinweisen und Aktivitäten beschränken, wenn die Sicht das sichere Bewegen oder den Maschineneinsatz beeinträchtigt."),
            "corrective_action": _t(language, "Improve lighting, restore signage visibility, or remove the obstruction affecting line-of-sight.", "Beleuchtung verbessern, Sichtbarkeit von Beschilderung wiederherstellen oder das die Sicht blockierende Hindernis entfernen."),
            "responsible_owner": _t(language, "Facilities / Area Supervisor / Safety Lead.", "Gebäudedienst / Bereichsleitung / Sicherheitsverantwortung."),
            "target_completion": timeframe,
            "verification": _t(language, "Confirm that staff can clearly see the route, hazard, signage, or equipment before normal operation resumes.", "Bestätigen, dass Mitarbeitende den Weg, die Gefahr, die Beschilderung oder das Gerät vor der Wiederaufnahme des Betriebs klar erkennen können."),
            "escalation": _t(language, "Escalate if poor visibility affects stairs, vehicles, machinery, emergency routes, or pedestrian movement.", "Eskaliert wird, wenn die schlechte Sicht Treppen, Fahrzeuge, Maschinen, Fluchtwege oder Fußgängerverkehr betrifft."),
            "closure_condition": _t(language, "Close only after visibility is restored and verified in the affected area.", "Erst schließen, wenn die Sicht im betroffenen Bereich wiederhergestellt und bestätigt wurde."),
            "manual_review_note": None,
        }

    return {
        "hazard_specific_finding": _t(language, f"{hazard_label} identified in {location_label}. Confirm the exact sub-hazard and apply site controls before normal work continues.", f"{hazard_label} in {location_label} identifiziert. Bitte die genaue Untergefahr bestätigen und vor der Wiederaufnahme der Arbeit geeignete Kontrollen anwenden."),
        "immediate_containment": _t(language, "Keep people clear of the area if the condition can cause harm and apply the safest available temporary control.", "Personen vom Bereich fernhalten, wenn die Situation zu Schaden führen kann, und die sicherste verfügbare Sofortmaßnahme anwenden."),
        "corrective_action": _t(language, "Inspect the area and correct the hazard using local procedures, signage, barriers, or housekeeping controls as appropriate.", "Bereich prüfen und die Gefahr je nach Situation mit lokalen Verfahren, Beschilderung, Absperrungen oder Ordnungskontrollen beseitigen."),
        "responsible_owner": _t(language, "Responsible supervisor / site safety lead.", "Verantwortliche Führungskraft / Sicherheitsverantwortung vor Ort."),
        "target_completion": timeframe,
        "verification": _t(language, "Reinspect the area after corrective action and confirm the hazard is controlled.", "Nach der Maßnahme den Bereich erneut prüfen und bestätigen, dass die Gefahr kontrolliert ist."),
        "escalation": _t(language, "Notify the responsible supervisor if the hazard cannot be resolved quickly.", "Die zuständige Führungskraft informieren, wenn die Gefahr nicht kurzfristig behoben werden kann."),
        "closure_condition": _t(language, "Close only after the area is confirmed safe for normal use.", "Erst schließen, wenn der Bereich als sicher für die normale Nutzung bestätigt ist."),
        "manual_review_note": None,
    }


def _risk_actions(risk_level: str) -> dict:
    level = risk_level.strip().lower()
    if level == "high":
        return {
            "priority": "Immediate",
            "immediate": [
                "Stop work in the affected area if it is safe to do so.",
                "Keep staff and visitors away from the hazard until it is controlled.",
            ],
            "prevention": [
                "Use formal controls before restarting work.",
                "Record the hazard and verify the fix before re-entry.",
            ],
            "escalation": [
                "Escalate to the supervisor, maintenance lead, or site safety lead immediately.",
            ],
            "follow_up": [
                "Confirm the area is safe before normal operations resume.",
            ],
        }
    if level == "medium":
        return {
            "priority": "Near-term",
            "immediate": [
                "Limit access to the area until controls are in place.",
                "Schedule corrective action as soon as possible.",
            ],
            "prevention": [
                "Inspect the area regularly until the hazard is resolved.",
                "Put a simple control or warning in place if exposure continues.",
            ],
            "escalation": [
                "Notify the responsible supervisor or safety contact.",
            ],
            "follow_up": [
                "Recheck the area after corrective action.",
            ],
        }
    return {
        "priority": "Routine",
        "immediate": [
            "Document the issue and correct it during planned work.",
            "Monitor the area for any change in risk.",
        ],
        "prevention": [
            "Add the issue to routine maintenance or housekeeping checks.",
            "Confirm the control remains in place.",
        ],
        "escalation": [
            "Escalate only if the condition worsens or spread is observed.",
        ],
        "follow_up": [
            "Review the item during the next inspection cycle.",
        ],
    }


def _hazard_template(hazard_category: str) -> dict:
    label = hazard_category.strip().lower()
    if "electrical" in label:
        return {
            "summary": "Electrical hazard detected. Treat exposed wiring, damaged cables, wet equipment, and open panels as high-risk conditions.",
            "immediate": [
                "Stop work near the affected area.",
                "Keep people away from exposed wiring, open panels, and wet surfaces near electricity.",
                "If safe, isolate the power supply using the main circuit breaker.",
                "Do not touch cables, panels, or damaged equipment until inspected.",
            ],
            "prevention": [
                "Repair or replace damaged wiring and covers.",
                "Use lockout/tagout where required.",
                "Schedule routine electrical inspections and cable management checks.",
            ],
            "escalation": [
                "Contact a qualified electrician or maintenance supervisor immediately.",
            ],
            "follow_up": [
                "Do not resume work until the area has been inspected and cleared.",
                "Verify the repair and test the equipment before reuse.",
            ],
        }
    if "obstruction" in label or "exit" in label or "fire" in label:
        return {
            "summary": "Fire or exit-route obstruction detected. Emergency routes must remain clear at all times.",
            "immediate": [
                "Keep the exit path clear and do not stack items in the route.",
                "Remove storage, boxes, or clutter if it can be done safely.",
                "Do not allow access to blocked emergency routes until cleared.",
            ],
            "prevention": [
                "Mark emergency exits and routes clearly.",
                "Set a no-storage zone around exits and fire escape paths.",
                "Add routine checks for blocked routes.",
            ],
            "escalation": [
                "Notify the site supervisor or fire safety lead immediately.",
            ],
            "follow_up": [
                "Confirm the route remains unobstructed after removal of items.",
                "Check signage and access visibility during the next inspection.",
            ],
        }
    if "trip" in label or "slip" in label:
        return {
            "summary": "Trip or slip hazard detected. Floor conditions, debris, cables, and spills can cause injury quickly.",
            "immediate": [
                "Remove loose debris, cables, or spill sources if safe.",
                "Cordon off the area if the floor cannot be made safe immediately.",
                "Warn nearby staff until the surface is cleared and dry.",
            ],
            "prevention": [
                "Improve housekeeping and cable routing.",
                "Use mats, anti-slip measures, or wet-floor controls where needed.",
                "Inspect high-traffic areas regularly.",
            ],
            "escalation": [
                "Report the condition to the supervisor or housekeeping lead.",
            ],
            "follow_up": [
                "Verify the surface condition after cleaning or drying.",
            ],
        }
    if "storage" in label:
        return {
            "summary": "Unsafe storage condition detected. Poorly stacked or misplaced materials can block routes and create secondary hazards.",
            "immediate": [
                "Stabilise or remove unsafe stacks if it is safe to do so.",
                "Keep stored materials away from walkways, exits, and equipment access points.",
            ],
            "prevention": [
                "Define storage zones and stacking limits.",
                "Separate frequently used items from emergency routes.",
            ],
            "escalation": [
                "Notify the supervisor if stored items are obstructing access or creating instability.",
            ],
            "follow_up": [
                "Check that storage remains within marked limits.",
            ],
        }
    if "chemical" in label:
        return {
            "summary": "Chemical exposure hazard detected. Spills, fumes, or unsafe storage require immediate control.",
            "immediate": [
                "Move people away from the affected area if exposure is possible.",
                "Do not touch or clean the spill unless the correct controls and PPE are available.",
            ],
            "prevention": [
                "Store chemicals according to the safety data sheet.",
                "Label containers clearly and keep incompatible materials apart.",
            ],
            "escalation": [
                "Contact the safety lead or hazardous materials contact.",
            ],
            "follow_up": [
                "Verify cleanup and ventilation before re-entry.",
            ],
        }
    if "machine" in label or "maintenance" in label:
        return {
            "summary": "Machine or maintenance hazard detected. Moving parts, panels, and repair work require controlled access.",
            "immediate": [
                "Stop work near the machine if guards or safe access are compromised.",
                "Keep hands and tools clear of moving or energised parts.",
            ],
            "prevention": [
                "Use guarding and isolation procedures before maintenance.",
                "Check that only trained staff access the equipment.",
            ],
            "escalation": [
                "Escalate to the maintenance supervisor or engineer.",
            ],
            "follow_up": [
                "Confirm the machine is safe before restarting work.",
            ],
        }
    return {
        "summary": f"{hazard_category} detected. Apply site controls and escalate if the condition could expose staff or visitors to harm.",
        "immediate": [
            "Keep people clear of the area if the condition can cause harm.",
            "Apply the safest available temporary control.",
        ],
        "prevention": [
            "Inspect the area and correct the hazard using local procedures.",
            "Review whether signage, barriers, or housekeeping controls are needed.",
        ],
        "escalation": [
            "Notify the responsible supervisor if the hazard cannot be resolved quickly.",
        ],
        "follow_up": [
            "Reinspect the site after corrective action.",
        ],
    }


def build_recommendations(
    hazard_category: str,
    risk_level: str,
    severity_score: float,
    scenario: str,
    location: Optional[str],
    needs_manual_review: bool,
    needs_more_info: bool,
    hazard_confidence: float = 0.0,
    image_caption: str = "",
    language: Optional[str] = None,
    image_caption_status: Optional[str] = None,
) -> dict:
    """Return structured, practical recommendations."""
    lang = _lang_code(language)
    hazard = _hazard_template(hazard_category)
    risk = _risk_actions(risk_level)

    location_text = _clean(location) or "the affected area"
    scenario_text = _clean(scenario) or "the reported workplace condition"
    normalized_caption_status = (image_caption_status or ("Completed" if _clean(image_caption) else "Not available")).strip() or "Not available"
    effective_image_caption = _clean(image_caption) if normalized_caption_status == "Completed" else ""
    has_image_context = bool(effective_image_caption)
    image_uploaded = normalized_caption_status in {"Completed", "Failed"}

    sub_hazard = _detect_sub_hazard(hazard_category, scenario_text, location_text, effective_image_caption)
    corrective_action_plan = _template_for(
        language=lang,
        hazard_category=hazard_category,
        sub_hazard=sub_hazard,
        location_text=location_text,
        risk_level=risk_level,
        needs_more_info=needs_more_info,
    )
    sub_hazard_localized = _localized_sub_hazard(lang, sub_hazard)

    immediate_actions = list(dict.fromkeys([
        corrective_action_plan["immediate_containment"],
        *hazard["immediate"],
        *risk["immediate"],
    ]))
    prevention_actions = list(dict.fromkeys([
        corrective_action_plan["corrective_action"],
        *hazard["prevention"],
        *risk["prevention"],
    ]))
    escalation_steps = list(dict.fromkeys([
        corrective_action_plan["escalation"],
        *hazard["escalation"],
        *risk["escalation"],
    ]))
    follow_up_checks = list(dict.fromkeys([
        corrective_action_plan["verification"],
        corrective_action_plan["closure_condition"],
        *hazard["follow_up"],
        *risk["follow_up"],
    ]))

    if needs_more_info:
        immediate_actions.insert(0, _t(lang, "Request clearer images and more detail before making a final decision.", "Bitte um klarere Bilder und weitere Details, bevor eine endgültige Entscheidung getroffen wird."))
        escalation_steps.append(_t(lang, "Hold the case for review until enough context is available.", "Fall bis zur ausreichenden Klärung zur Prüfung zurückhalten."))

    if needs_manual_review and not needs_more_info:
        escalation_steps.insert(0, _t(lang, "Route the case to a competent person or supervisor for manual review.", "Fall zur manuellen Prüfung an eine fachkundige Person oder Führungskraft weiterleiten."))

    if location:
        prevention_actions.append(_t(lang, f"Apply controls specifically around {location_text}.", f"Kontrollen gezielt in {location_text} anwenden."))
        follow_up_checks.append(_t(lang, f"Confirm the hazard is resolved in {location_text}.", f"Bestätigen, dass die Gefahr in {location_text} behoben ist."))

    recommendation_priority = "Immediate" if risk_level.strip().lower() == "high" else risk["priority"]
    if needs_more_info:
        recommendation_priority = _t(lang, "Information required", "Weitere Informationen erforderlich")
    elif needs_manual_review and recommendation_priority == "Routine":
        recommendation_priority = _t(lang, "Review required", "Prüfung erforderlich")

    manual_review_note = _manual_review_note(
        lang,
        needs_manual_review,
        needs_more_info,
        image_uploaded,
        has_image_context,
        hazard_confidence,
    )
    if manual_review_note:
        corrective_action_plan["manual_review_note"] = manual_review_note

    summary_parts = [
        corrective_action_plan["hazard_specific_finding"],
        corrective_action_plan["immediate_containment"],
        corrective_action_plan["corrective_action"],
        corrective_action_plan["verification"],
        corrective_action_plan["closure_condition"],
        f"Target completion: {corrective_action_plan['target_completion']}",
    ]
    if sub_hazard:
        summary_parts.insert(1, _t(lang, f"Sub-hazard: {sub_hazard_localized}.", f"Untergefahr: {sub_hazard_localized}."))
    if manual_review_note:
        summary_parts.append(manual_review_note)

    return {
        "hazard_summary": hazard["summary"],
        "sub_hazard": sub_hazard_localized,
        "hazard_confidence": float(hazard_confidence),
        "risk_method": _t(lang, "Deterministic severity-score rule", "Deterministische Schweregrad-Score-Regel"),
        "image_caption_status": normalized_caption_status,
        "immediate_actions": immediate_actions,
        "prevention_actions": prevention_actions,
        "escalation_steps": escalation_steps,
        "follow_up_checks": follow_up_checks,
        "location_notes": f"Focus on {location_text}. Scenario context: {scenario_text}.",
        "recommendation_priority": recommendation_priority,
        "recommendation_summary": " ".join(part for part in summary_parts if part).strip(),
        "decision_support_recommendation": " ".join(part for part in summary_parts if part).strip(),
        "corrective_action_plan": corrective_action_plan,
        "manual_review_flag": needs_manual_review,
        "needs_more_information": needs_more_info,
        "clarification_question": _clarification_question(lang, hazard_category, sub_hazard, location_text) if needs_more_info else None,
        "response_locale": lang,
    }
