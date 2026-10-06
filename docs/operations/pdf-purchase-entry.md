# PDF Purchase Entry

The purchase-entry flow previews a PDF locally, lets the owner correct the suggested values, then saves the corrected metadata and original document together. Preview does not create a purchase or retain the PDF. The API stores generated document references beneath the configured private profile root; it never uses the submitted filename as a path.

## Prerequisites

- Python 3.11 or later and `uv`.
- Node.js 22.12 or later and npm for the Astro 7 frontend.
- Tesseract OCR with Polish language data for scanned PDFs. Text-based PDFs do not need Tesseract.
- An existing, owner-controlled directory outside the source checkout for `WARRANTIES_DATA_DIR`.

On Windows, install a Tesseract distribution that includes `pol.traineddata`. For example, the UB Mannheim installer supports selecting additional language data. On Debian or Ubuntu, install the executable and Polish language package:

```sh
sudo apt-get install tesseract-ocr tesseract-ocr-pol
```

Verify that Polish data is available:

```sh
tesseract --list-langs
```

The output must include `pol`. Configure `TESSERACT_CMD` if the executable is not on `PATH`, and set `TESSDATA_PREFIX` to the directory containing `pol.traineddata` when it is not in Tesseract's default data directory.

PowerShell example:

```powershell
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
$env:TESSDATA_PREFIX = 'C:\Program Files\Tesseract-OCR\tessdata'
$env:WARRANTIES_DATA_DIR = "$env:LOCALAPPDATA\PamiętajGwarancje"
New-Item -ItemType Directory -Force $env:WARRANTIES_DATA_DIR
```

## Run Locally

Use two terminals from the repository root. The API and UI bind to loopback for local use.

PowerShell, API terminal:

```powershell
$env:WARRANTIES_DATA_DIR = "$env:LOCALAPPDATA\PamiętajGwarancje"
$env:TESSERACT_CMD = 'C:\Program Files\Tesseract-OCR\tesseract.exe'
$env:TESSDATA_PREFIX = 'C:\Program Files\Tesseract-OCR\tessdata'
uv run uvicorn warranties_10xdev.api:app --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
$env:API_ORIGIN = 'http://127.0.0.1:8000'
npm --prefix frontend run dev -- --host 127.0.0.1
```

Open `http://127.0.0.1:4321/purchases/new`. The frontend's `/api` requests are proxied to `API_ORIGIN`; the default development origin is `http://127.0.0.1:8000`.

## Upload and Save Behavior

- Uploads are limited to 20 MiB. The API enforces the limit while reading the multipart body; it does not rely on the declared content length, MIME type, or client filename.
- Embedded PDF text is extracted locally. Image-only pages are rendered one at a time and passed to the local Tesseract process with Polish and English language data (`pol+eng`). No invoice content is sent to an external OCR or AI provider.
- Preview is non-persistent. The PDF is only staged beneath the private data root after the owner selects **Zapisz zakup**.
- Product name, purchase date, and purchase type (private or business) are required. Seller, payment method, and a custom warranty end date are optional.
- OCR suggestions are editable. Once shown, a suggestion is not reapplied over the owner's edits. If extraction fails, the selected PDF remains attached and required values can be entered manually before saving.
- On Save, the app writes the corrected values and PDF under the profile lock. It inserts the database row and atomically promotes the staged document; failures roll back the row and remove temporary or promoted files.
- The confirmation shows the purchase ID, not a local filesystem path or public document URL.
