const fs = require('fs');
const path = require('path');
const express = require('express');
const { chromium } = require('playwright');
const { renderReportHtml } = require('./report-template');
const REPORT_CSS_PATH = path.join(__dirname, 'styles', 'report.css');
const reportCss = fs.readFileSync(REPORT_CSS_PATH, 'utf8');

const app = express();
const PORT = process.env.PORT || 3001;
const DEBUG_HTML_PATH = path.join(__dirname, '..', 'debug-report.html');

app.use(express.json({ limit: '20mb' }));

const riskBadgeClass = (badge) => {
  const value = String(badge || '').toUpperCase();
  if (value.includes('HIGH')) return 'badge-high';
  if (value.includes('MEDIUM')) return 'badge-medium';
  if (value.includes('LOW')) return 'badge-low';
  return 'badge-neutral';
};

app.get('/health', (_req, res) => {
  res.json({ ok: true, service: 'pdf-service' });
});

app.post('/render-report', async (req, res) => {
  try {
    const report = req.body || {};
    const payload = {
      ...report,
      risk_badge_class: riskBadgeClass(report.risk_badge),
      inline_css: reportCss,
    };

    const html = renderReportHtml(payload);
    fs.writeFileSync(DEBUG_HTML_PATH, html, 'utf8');

    const browser = await chromium.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });

    try {
      const page = await browser.newPage({
        viewport: { width: 1240, height: 1754 },
        deviceScaleFactor: 1,
      });
      await page.setContent(html, { waitUntil: 'networkidle' });
      await page.emulateMedia({ media: 'print' });
      const pdfBuffer = await page.pdf({
        format: 'A4',
        printBackground: true,
        preferCSSPageSize: false,
        margin: {
          top: '15mm',
          right: '12mm',
          bottom: '15mm',
          left: '12mm',
        },
      });
      res.setHeader('Content-Type', 'application/pdf');
      res.setHeader('Content-Disposition', 'attachment; filename=hazard-chatbot-report.pdf');
      res.send(pdfBuffer);
    } finally {
      await browser.close();
    }
  } catch (error) {
    console.error('render-report failed', error);
    res.status(500).json({
      error: 'Failed to render PDF report',
      details: error.message,
    });
  }
});

app.listen(PORT, () => {
  console.log(`PDF service listening on http://127.0.0.1:${PORT}`);
  console.log(`Debug HTML will be written to ${DEBUG_HTML_PATH}`);
});
