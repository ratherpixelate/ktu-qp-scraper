# KTU Model Question Papers Scraper

Downloads and organizes **KTU (APJ Abdul Kalam Technological University) B.Tech model / previous year question papers** (2024 scheme) directly from ktu.edu.in — split into clean, per-subject PDFs ready for exam prep.

## Features

- Scrapes model question papers for every semester and branch under the 2024 scheme
- Splits bundled multi-subject PDFs into one file per subject/course code
- Organized output: `semester → branch → subject code`

## Setup

```
uv sync
uv run playwright install chromium
```

## Usage

**1. Download the raw papers**

```
uv run scraper/fetch_qps.py
```

Saves bundled PDFs to `scraper/downloads/<semester>/<branch or group>.pdf`.

**2. Split into per-subject papers**

```
uv run scraper/split_papers.py
```

Splits each bundle by subject and writes to:

```
scraper/papers/<semester_number>/<branch_name>/<subject_code>/<subject_code> (MOD).pdf
```

e.g.

```
scraper/papers/3/Computer Science and Engineering/PCCST302/PCCST302 (MOD).pdf
```

## Keywords

KTU question papers, KTU model question papers, KTU previous year question papers, KTU PYQ download, APJ Abdul Kalam Technological University question bank, KTU 2024 scheme exam papers, KTU B.Tech question paper scraper