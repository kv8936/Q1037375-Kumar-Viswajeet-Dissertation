# PDF Service

Local Node.js + Playwright service that renders the hazard report HTML to PDF.

## Endpoints

- `GET /health`
- `POST /render-report`

## Input

The backend sends JSON with:

- report metadata
- scenario and location
- original and translated model input
- hazard and risk predictions
- optional `image_data_url`
- recommendation and safety note text

## Behavior

- Saves `debug-report.html` before rendering the PDF
- Uses Chromium via Playwright
- Generates an A4 report with print backgrounds enabled
- Keeps the flow local-only

## Run

1. Install dependencies
2. Install Playwright browsers
3. Start the service on port 3001

Set `PDF_SERVICE_URL` in the Rust backend to point here.
