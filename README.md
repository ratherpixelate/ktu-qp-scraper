# ktu-papers-scraper

Scrapes model question papers for KTU B.Tech (2024 scheme) from ktu.edu.in.

## Setup

```
uv sync
uv run playwright install chromium
```

## Run

```
uv run fetch_qps.py
```

## Output

PDFs are saved under `downloads/<semester>/<branch>.pdf`, e.g.

```
downloads/SEMESTER 3/GROUP A.pdf
downloads/SEMESTER 3/GROUP B.pdf
```