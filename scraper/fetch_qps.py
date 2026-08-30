import asyncio
import base64
import httpx
from pathlib import Path
from playwright.async_api import async_playwright

BASE_URL = "https://api.ktu.edu.in/ktu-web-portal-api/anon"
SCHEME_ID = 70
PDF_DIR = Path(__file__).parent / "downloads"
PAGE_SIZE = 50  # default response pageable.size was 10 — request bigger pages explicitly


async def get_token_via_browser() -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = await browser.new_page()

        await page.goto("https://ktu.edu.in/academics/scheme", timeout=90000, wait_until="domcontentloaded")
        await page.wait_for_selector("h3.clr-maroon", timeout=30000)

        async with page.expect_response(
            lambda r: "additionalRegulations" in r.url,
            timeout=60000
        ) as response_info:
            scheme_row = page.locator(".border-bottom-dotted.row", has=page.locator("h3", has_text="B.TECH FULL TIME 2024 SCHEME"))
            docs_btn = scheme_row.locator("a", has_text="Documents")
            await docs_btn.click()
            await page.wait_for_url("**/academics/semestermodelpapers", timeout=30000)

        response = await response_info.value
        token = response.request.headers.get("x-token")
        await browser.close()
        return token


def make_headers(token: str) -> dict:
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "X-Token": token,
        "Origin": "https://ktu.edu.in",
        "Referer": "https://ktu.edu.in/",
    }


async def fetch_nodes(client: httpx.AsyncClient, token: str, parent_id: int | None) -> list[dict]:
    """Fetch all children of parent_id in the additionalRegulations tree,
    paging through until the response reports last=True."""
    nodes = []
    page_num = 0
    while True:
        body = {"schemeId": str(SCHEME_ID), "number": page_num, "size": PAGE_SIZE}
        if parent_id is not None:
            body["parentId"] = parent_id

        resp = await client.post(
            f"{BASE_URL}/additionalRegulations",
            headers=make_headers(token),
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        batch = data["content"]
        nodes.extend(batch)

        if data.get("last", True) or not batch:
            break
        page_num += 1

    return nodes


async def find_child_by_name(client: httpx.AsyncClient, token: str, parent_id: int | None, name: str) -> dict | None:
    nodes = await fetch_nodes(client, token, parent_id)
    for n in nodes:
        if n["name"].strip().lower() == name.strip().lower():
            return n
    return None


async def download_pdf(
    client: httpx.AsyncClient, token: str, encrypt_id: str, out_path: Path
) -> None:
    if out_path.exists():
        print(f"    [skip] {out_path.name}")
        return

    resp = await client.post(
        f"{BASE_URL}/getAttachment",
        headers=make_headers(token),
        json={"encryptId": encrypt_id},
    )
    resp.raise_for_status()

    base64_string = resp.text.strip('"')
    pdf_bytes = base64.b64decode(base64_string)

    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError(f"Invalid PDF response for encryptId: {encrypt_id}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(pdf_bytes)
    print(f"    [saved] {out_path}")


async def main():
    print("Launching browser to acquire token...")
    token = await get_token_via_browser()
    print(f"Token acquired: {token[:20]}...")

    async with httpx.AsyncClient(timeout=60, http1=True, http2=False) as client:
        # Model Question Papers is a top-level node under the scheme
        mqp_node = await find_child_by_name(client, token, None, "Model Question Papers")
        if mqp_node is None:
            raise RuntimeError("Could not find 'Model Question Papers' node — check top-level tree names")

        semesters = await fetch_nodes(client, token, mqp_node["id"])
        print(f"Found {len(semesters)} semesters")

        for sem in semesters:
            sem_name = sem["name"]
            print(f"\n[{sem['id']}] {sem_name}")

            branches = await fetch_nodes(client, token, sem["id"])
            print(f"  {len(branches)} branches")

            for branch in branches:
                encrypt_id = branch.get("attachmentEncryptedId")
                if not encrypt_id:
                    # not a leaf — shouldn't happen at this depth, but skip safely
                    continue
                branch_name = branch["name"]
                out_path = PDF_DIR / sem_name / f"{branch_name}.pdf"
                await download_pdf(client, token, encrypt_id, out_path)

    print("\nFinished scraping all model question papers :]")


if __name__ == "__main__":
    asyncio.run(main())