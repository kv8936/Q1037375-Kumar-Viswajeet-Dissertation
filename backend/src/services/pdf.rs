use chrono::Utc;
use printpdf::{
    color::{Color, Rgb},
    font::{BuiltinFont, ParsedFont},
    graphics::{Line, LinePoint, Point, Rect},
    image_types::RawImage,
    ops::{Op, PdfFontHandle, PdfPage},
    serialize::PdfSaveOptions,
    units::{Mm, Pt},
    xobject::XObjectTransform,
    PdfDocument,
};

pub struct PdfReportInput {
    pub app_title: String,
    pub app_version: String,
    pub model_version: String,
    pub report_id: String,
    pub report_locale: String,
    pub exported_at: String,
    pub scenario: String,
    pub location: String,
    pub provider: String,
    pub original_input: String,
    pub detected_language: String,
    pub translated_model_input: String,
    pub predicted_hazard_category: String,
    pub predicted_risk_level: String,
    pub decision_support_recommendation: String,
    pub recommended_follow_up: String,
    pub safety_note: String,
    pub image_caption: String,
    pub image_caption_status: String,
    pub image_caption_model: String,
    pub image_caption_warning: String,
    pub final_model_input: String,
    pub image_bytes: Option<Vec<u8>>,
    pub image_filename: Option<String>,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum ReportLocale {
    En,
    De,
}

impl ReportLocale {
    fn from_str(value: &str) -> Self {
        if value.trim().eq_ignore_ascii_case("de") {
            Self::De
        } else {
            Self::En
        }
    }
}

fn t<'a>(locale: ReportLocale, en: &'a str, de: &'a str) -> &'a str {
    match locale {
        ReportLocale::De => de,
        ReportLocale::En => en,
    }
}

fn provider_label(locale: ReportLocale, provider: &str) -> String {
    match provider.trim().to_lowercase().as_str() {
        "openai" => t(locale, "OpenAI", "OpenAI").to_string(),
        "anthropic" => t(locale, "Anthropic", "Anthropic").to_string(),
        _ => t(locale, "Local inference", "Lokale Inferenz").to_string(),
    }
}

fn risk_badge_color(risk_level: &str) -> &'static str {
    match risk_level.trim().to_lowercase().as_str() {
        "high" => "HIGH RISK",
        "medium" => "MEDIUM RISK",
        "low" => "LOW RISK",
        _ => "RISK UNAVAILABLE",
    }
}

fn wrap_text(value: &str, max_chars: usize) -> Vec<String> {
    let clean = value.trim();
    if clean.is_empty() {
        return vec!["Not available".to_string()];
    }

    let mut lines = Vec::new();
    let mut current = String::new();

    for word in clean.split_whitespace() {
        if current.is_empty() {
            current.push_str(word);
            continue;
        }

        if current.len() + 1 + word.len() <= max_chars {
            current.push(' ');
            current.push_str(word);
        } else {
            lines.push(current);
            current = word.to_string();
        }
    }

    if !current.is_empty() {
        lines.push(current);
    }

    if lines.is_empty() {
        vec![clean.to_string()]
    } else {
        lines
    }
}

fn push_text_line(ops: &mut Vec<Op>, text: impl Into<String>) {
    ops.push(Op::MoveToNextLineShowText { text: text.into() });
}

fn push_wrapped_text(ops: &mut Vec<Op>, value: &str, max_chars: usize) {
    for line in wrap_text(value, max_chars) {
        push_text_line(ops, line);
    }
}

fn push_multiline_wrapped_text(ops: &mut Vec<Op>, value: &str, max_chars: usize) {
    let mut emitted = false;

    for segment in value.lines() {
        let segment = segment.trim();
        if segment.is_empty() {
            continue;
        }

        emitted = true;
        push_wrapped_text(ops, segment, max_chars);
    }

    if !emitted {
        push_text_line(ops, "Not available".to_string());
    }
}

fn draw_page_border(ops: &mut Vec<Op>) {
    let margin_left = 12.0;
    let margin_bottom = 12.0;
    let margin_right = 198.0;
    let margin_top = 285.0;

    let points = vec![
        LinePoint { p: Point { x: Pt(margin_left), y: Pt(margin_bottom) }, bezier: false },
        LinePoint { p: Point { x: Pt(margin_right), y: Pt(margin_bottom) }, bezier: false },
        LinePoint { p: Point { x: Pt(margin_right), y: Pt(margin_top) }, bezier: false },
        LinePoint { p: Point { x: Pt(margin_left), y: Pt(margin_top) }, bezier: false },
    ];

    ops.push(Op::SetOutlineThickness { pt: Pt(0.75) });
    ops.push(Op::DrawLine {
        line: Line {
            points,
            is_closed: true,
        },
    });
}

fn header_block(ops: &mut Vec<Op>, locale: ReportLocale, app_title: &str, body_font: &PdfFontHandle, bold_font: &PdfFontHandle) {
    ops.push(Op::SetFont {
        font: bold_font.clone(),
        size: Pt(20.0),
    });
    push_text_line(ops, app_title.to_string());
    ops.push(Op::SetFont {
        font: body_font.clone(),
        size: Pt(10.5),
    });
    push_text_line(
        ops,
        t(
            locale,
            "Workplace Hazard and Risk Decision-Support Output",
            "Arbeitsplatzgefahren- und Risikobericht zur Entscheidungsunterstützung",
        )
        .to_string(),
    );
    push_text_line(
        ops,
        t(
            locale,
            "Generated by the prototype health risk model developed by Kumar Viswajeet",
            "Erstellt durch das Prototyp-Gesundheitsrisikomodell von Kumar Viswajeet",
        )
        .to_string(),
    );
    push_text_line(ops, String::new());
}

fn section_card_header(ops: &mut Vec<Op>, title: &str, font: &PdfFontHandle) {
    ops.push(Op::SetFont {
        font: font.clone(),
        size: Pt(13.0),
    });
    push_text_line(ops, title.to_string());
    ops.push(Op::SetFont {
        font: PdfFontHandle::Builtin(BuiltinFont::Helvetica),
        size: Pt(10.0),
    });
}

fn begin_text_section(ops: &mut Vec<Op>, font_size: f32, x: f32, y: f32, line_height: f32, font: PdfFontHandle) {
    ops.push(Op::StartTextSection);
    ops.push(Op::SetFont {
        font,
        size: Pt(font_size),
    });
    ops.push(Op::SetTextCursor {
        pos: Point { x: Pt(x), y: Pt(y) },
    });
    ops.push(Op::SetLineHeight { lh: Pt(line_height) });
}

fn section_title(ops: &mut Vec<Op>, title: &str, font: &PdfFontHandle) {
    ops.push(Op::SetFont {
        font: font.clone(),
        size: Pt(14.0),
    });
    push_text_line(ops, title.to_string());
    ops.push(Op::SetFont {
        font: font.clone(),
        size: Pt(10.5),
    });
}

fn field_block(ops: &mut Vec<Op>, label: &str, value: &str, wrap: usize, blank_after: bool) {
    push_text_line(ops, label.to_string());
    push_wrapped_text(ops, value, wrap);
    if blank_after {
        push_text_line(ops, String::new());
    }
}

fn add_footer(ops: &mut Vec<Op>, report_id: &str, page_label: &str, locale: ReportLocale, font: &PdfFontHandle) {
    push_text_line(ops, String::new());
    ops.push(Op::SetFont {
        font: font.clone(),
        size: Pt(8.0),
    });
    push_text_line(
        ops,
        format!("{}: {}", t(locale, "Report ID", "Berichts-ID"), report_id),
    );
    push_text_line(
        ops,
        format!(
            "{} - {}",
            page_label,
            t(locale, "Decision-support output only", "Nur zur Entscheidungsunterstützung")
        ),
    );
    push_text_line(
        ops,
        t(locale, "This report was generated by a dissertation prototype and is intended for decision-support evaluation only. It does not replace review by a competent occupational safety professional.", "Dieser Bericht wurde von einem Dissertation-Prototypen erzeugt und dient nur der Entscheidungsunterstützung. Er ersetzt nicht die Prüfung durch eine fachkundige Arbeitsschutzfachkraft.").to_string(),
    );
}

fn load_font_bytes(candidates: &[&str]) -> Result<Vec<u8>, String> {
    for candidate in candidates {
        if let Ok(bytes) = std::fs::read(candidate) {
            return Ok(bytes);
        }
    }

    Err(format!(
        "could not find a suitable Unicode font in any of these paths: {}",
        candidates.join(", ")
    ))
}

fn register_font(
    doc: &mut PdfDocument,
    label: &str,
    candidates: &[&str],
) -> Result<PdfFontHandle, String> {
    let font_bytes = load_font_bytes(candidates)?;
    let mut font_warnings = Vec::new();
    let parsed_font = ParsedFont::from_bytes(&font_bytes, 0, &mut font_warnings)
        .ok_or_else(|| format!("failed to parse {} font bytes", label))?;
    let font_id = doc.add_font(&parsed_font);
    Ok(PdfFontHandle::External(font_id))
}

pub fn build_report_pdf(input: PdfReportInput) -> Result<Vec<u8>, String> {
    let mut doc = PdfDocument::new(&input.app_title);
    let locale = ReportLocale::from_str(&input.report_locale);
    let body_font = register_font(
        &mut doc,
        "body",
        &[
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
        ],
    )?;
    let bold_font = register_font(
        &mut doc,
        "bold",
        &[
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/Library/Fonts/Arial Bold.ttf",
        ],
    )?;

    let mut page1_ops = Vec::new();
    draw_page_border(&mut page1_ops);
    begin_text_section(&mut page1_ops, 22.0, 24.0, 804.0, 15.0, bold_font.clone());
    header_block(&mut page1_ops, locale, &input.app_title, &body_font, &bold_font);
    page1_ops.push(Op::SetFont { font: PdfFontHandle::Builtin(BuiltinFont::Helvetica), size: Pt(10.0) });
    push_text_line(
        &mut page1_ops,
        format!("{}: {}", t(locale, "Version", "Version"), input.app_version),
    );
    push_text_line(
        &mut page1_ops,
        format!("{}: {}", t(locale, "Model version", "Modellversion"), input.model_version),
    );
    push_text_line(
        &mut page1_ops,
        format!("{}: {}", t(locale, "Report ID", "Berichts-ID"), input.report_id),
    );
    push_text_line(
        &mut page1_ops,
        format!(
            "{}: {}",
            t(locale, "Generated at", "Erstellt am"),
            input.exported_at
        ),
    );
    push_text_line(
        &mut page1_ops,
        format!("{}: {}", t(locale, "Provider", "Anbieter"), provider_label(locale, &input.provider)),
    );
    push_text_line(&mut page1_ops, String::new());

    section_title(&mut page1_ops, t(locale, "Operational input", "Betriebseingaben"), &bold_font);
    field_block(&mut page1_ops, t(locale, "Scenario:", "Szenario:"), &input.scenario, 88, false);
    field_block(&mut page1_ops, t(locale, "Location:", "Ort:"), &input.location, 88, false);
    field_block(
        &mut page1_ops,
        t(locale, "Original language:", "Originalsprache:"),
        if input.detected_language.trim().is_empty() { t(locale, "Unknown", "Unbekannt") } else { &input.detected_language },
        88,
        false,
    );
    section_title(&mut page1_ops, t(locale, "Evidence Image", "Nachweisbild"), &bold_font);

    page1_ops.push(Op::EndTextSection);

    if let Some(image_bytes) = input.image_bytes.as_ref() {
        let mut warnings = Vec::new();
        let raw_image = RawImage::decode_from_bytes(image_bytes, &mut warnings)
            .map_err(|e| format!("failed to decode uploaded image: {}", e))?;

        let image_box_x = 24.0;
        let image_box_y = 483.0;
        let image_box_w = 547.0;
        let image_box_h = 164.0;
        let padding = 10.0;
        let inner_w = image_box_w - (padding * 2.0);
        let inner_h = image_box_h - (padding * 2.0);
        let base_w = (raw_image.width as f32) * 72.0 / 300.0;
        let base_h = (raw_image.height as f32) * 72.0 / 300.0;
        let scale = (inner_w / base_w).min(inner_h / base_h).min(1.0);
        let rendered_w = base_w * scale;
        let rendered_h = base_h * scale;
        let image_translate_x = image_box_x + padding + ((inner_w - rendered_w) / 2.0);
        let image_translate_y = image_box_y + padding + ((inner_h - rendered_h) / 2.0);

        page1_ops.push(Op::SaveGraphicsState);
        page1_ops.push(Op::SetFillColor { col: Color::Rgb(Rgb::new(0.97, 0.98, 0.99, None)) });
        page1_ops.push(Op::DrawPolygon {
            polygon: Rect::from_xywh(Pt(image_box_x), Pt(image_box_y), Pt(image_box_w), Pt(image_box_h)).to_polygon(),
        });
        page1_ops.push(Op::SetOutlineColor { col: Color::Rgb(Rgb::new(0.72, 0.77, 0.82, None)) });
        page1_ops.push(Op::SetOutlineThickness { pt: Pt(0.8) });
        page1_ops.push(Op::DrawLine {
            line: Rect::from_xywh(Pt(image_box_x), Pt(image_box_y), Pt(image_box_w), Pt(image_box_h)).to_line(),
        });
        page1_ops.push(Op::RestoreGraphicsState);

        let image_id = doc.add_image(&raw_image);
        page1_ops.push(Op::UseXobject {
            id: image_id,
            transform: XObjectTransform {
                translate_x: Some(Pt(image_translate_x)),
                translate_y: Some(Pt(image_translate_y)),
                rotate: None,
                scale_x: Some(scale),
                scale_y: Some(scale),
                dpi: Some(300.0),
            },
        });
    } else {
        begin_text_section(&mut page1_ops, 10.5, 24.0, 465.0, 13.0, body_font.clone());
        push_text_line(
            &mut page1_ops,
            t(locale, "No image was uploaded for this assessment.", "Für diese Bewertung wurde kein Bild hochgeladen.").to_string(),
        );
        push_text_line(&mut page1_ops, String::new());
        page1_ops.push(Op::EndTextSection);
    }

    begin_text_section(&mut page1_ops, 10.5, 24.0, 470.0, 13.0, body_font.clone());
    field_block(
        &mut page1_ops,
        t(locale, "Generated image caption:", "Generierte Bildbeschreibung:"),
        if input.image_caption.trim().is_empty() { "Not available" } else { &input.image_caption },
        88,
        true,
    );
    field_block(
        &mut page1_ops,
        t(locale, "Caption status:", "Beschriftungsstatus:"),
        if input.image_caption_status.trim().is_empty() { "—" } else { &input.image_caption_status },
        88,
        false,
    );
    field_block(
        &mut page1_ops,
        t(locale, "Caption model:", "Beschriftungsmodell:"),
        if input.image_caption_model.trim().is_empty() { "—" } else { &input.image_caption_model },
        88,
        false,
    );
    field_block(
        &mut page1_ops,
        t(locale, "Caption warning:", "Beschriftungshinweis:"),
        if input.image_caption_warning.trim().is_empty() { "—" } else { &input.image_caption_warning },
        88,
        true,
    );

    section_title(&mut page1_ops, t(locale, "Prediction Summary", "Vorhersagezusammenfassung"), &bold_font);
    section_card_header(
        &mut page1_ops,
        t(locale, "Report metadata", "Berichtsmetadaten"),
        &bold_font,
    );
    field_block(
        &mut page1_ops,
        t(locale, "Hazard category:", "Gefahrenkategorie:"),
        &input.predicted_hazard_category,
        88,
        false,
    );
    field_block(
        &mut page1_ops,
        t(locale, "Risk level:", "Risikostufe:"),
        &input.predicted_risk_level,
        88,
        false,
    );
    field_block(
        &mut page1_ops,
        t(locale, "Risk badge:", "Risikokennzeichnung:"),
        risk_badge_color(&input.predicted_risk_level),
        88,
        false,
    );
    field_block(
        &mut page1_ops,
        t(locale, "Operating provider:", "Verwendeter Anbieter:"),
        &input.provider,
        88,
        false,
    );
    field_block(
        &mut page1_ops,
        t(locale, "Report status:", "Berichtsstatus:"),
        t(locale, "Generated successfully", "Erfolgreich erstellt"),
        88,
        true,
    );

    field_block(
        &mut page1_ops,
        t(locale, "Original input:", "Ursprüngliche Eingabe:"),
        &input.original_input,
        88,
        false,
    );
    field_block(
        &mut page1_ops,
        t(locale, "Translated model input:", "Übersetzte Modelleingabe:"),
        if input.translated_model_input.trim().is_empty() { &input.final_model_input } else { &input.translated_model_input },
        88,
        true,
    );
    field_block(
        &mut page1_ops,
        t(locale, "Image caption:", "Bildbeschreibung:"),
        &input.image_caption,
        88,
        false,
    );

    section_title(&mut page1_ops, t(locale, "Model output", "Modellausgabe"), &bold_font);
    field_block(
        &mut page1_ops,
        t(locale, "Decision-support recommendation:", "Entscheidungsunterstützende Empfehlung:"),
        &input.decision_support_recommendation,
        88,
        false,
    );
    push_text_line(
        &mut page1_ops,
        format!(
            "{}: {}",
            t(locale, "Safety note", "Sicherheitshinweis"),
            input.safety_note
        ),
    );
    section_title(&mut page1_ops, t(locale, "Recommended follow-up", "Empfohlene Folgemaßnahmen"), &bold_font);
    push_multiline_wrapped_text(&mut page1_ops, &input.recommended_follow_up, 88);
    push_text_line(&mut page1_ops, String::new());
    push_text_line(
        &mut page1_ops,
        t(
            locale,
            "Review the recommendation with site supervisors before acting.",
            "Prüfe die Empfehlung vor Maßnahmen gemeinsam mit der zuständigen Aufsicht.",
        )
        .to_string(),
    );
    add_footer(&mut page1_ops, &input.report_id, t(locale, "Page 1", "Seite 1"), locale, &body_font);
    page1_ops.push(Op::EndTextSection);

    doc.with_pages(vec![PdfPage::new(Mm(210.0), Mm(297.0), page1_ops)]);

    let mut page2_ops = Vec::new();
    draw_page_border(&mut page2_ops);
    begin_text_section(&mut page2_ops, 20.0, 24.0, 804.0, 15.0, bold_font.clone());
    push_text_line(
        &mut page2_ops,
        t(locale, "Evidence appendix and audit trail", "Anhang mit Nachweisen und Prüffestigkeit").to_string(),
    );
    page2_ops.push(Op::SetFont {
        font: PdfFontHandle::Builtin(BuiltinFont::Helvetica),
        size: Pt(10.0),
    });
    push_text_line(
        &mut page2_ops,
        format!("{}: {}", t(locale, "Report ID", "Berichts-ID"), input.report_id),
    );
    push_text_line(
        &mut page2_ops,
        format!(
            "{}: {}",
            t(locale, "Generated at", "Erstellt am"),
            input.exported_at
        ),
    );
    push_text_line(
        &mut page2_ops,
        format!(
            "{}: {}",
            t(locale, "Provider", "Anbieter"),
            provider_label(locale, &input.provider)
        ),
    );
    push_text_line(
        &mut page2_ops,
        format!(
            "{}: {}",
            t(locale, "Original language", "Originalsprache"),
            if input.detected_language.trim().is_empty() { t(locale, "Unknown", "Unbekannt") } else { &input.detected_language }
        ),
    );
    push_text_line(
        &mut page2_ops,
        format!(
            "{}: {}",
            t(locale, "Image included", "Bild enthalten"),
            if input.image_bytes.is_some() { t(locale, "yes", "ja") } else { t(locale, "no", "nein") }
        ),
    );
    if let Some(name) = input.image_filename.as_deref() {
        push_text_line(
            &mut page2_ops,
            format!("{}: {}", t(locale, "Image file", "Bilddatei"), name),
        );
    }
    push_text_line(&mut page2_ops, String::new());
    section_title(&mut page2_ops, t(locale, "Governance note", "Hinweis zur Governance"), &bold_font);
    push_wrapped_text(
        &mut page2_ops,
        t(
            locale,
            "This report is intended for operational decision support and review. It does not replace site inspection, safety policy, or qualified human judgment.",
            "Dieser Bericht dient nur der operativen Entscheidungsunterstützung und Prüfung. Er ersetzt keine Ortsbegehung, Sicherheitsrichtlinie oder fachkundige menschliche Beurteilung.",
        ),
        88,
    );
    push_text_line(&mut page2_ops, String::new());

    if input.image_bytes.is_none() {
        section_title(&mut page2_ops, t(locale, "Evidence appendix", "Nachweisanhang"), &bold_font);
        push_wrapped_text(
            &mut page2_ops,
            t(
                locale,
                "No image was attached to this run. The report still preserves the structured scenario, prediction output, and audit metadata for downstream review.",
                "Zu diesem Lauf wurde kein Bild angehängt. Der Bericht bewahrt dennoch das strukturierte Szenario, die Vorhersageausgabe und die Prüfdaten für die weitere Bewertung auf.",
            ),
            88,
        );
    }

    add_footer(&mut page2_ops, &input.report_id, t(locale, "Page 2", "Seite 2"), locale, &body_font);
    page2_ops.push(Op::EndTextSection);

    doc.pages.push(PdfPage::new(Mm(210.0), Mm(297.0), page2_ops));

    let mut warnings = Vec::new();
    Ok(doc.save(&PdfSaveOptions::default(), &mut warnings))
}

pub fn exported_timestamp() -> String {
    Utc::now().to_rfc3339()
}
