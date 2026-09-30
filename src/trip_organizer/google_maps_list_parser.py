"""Extract places from a public Google Maps list URL.

This uses the HTML served for a public/shared list and does not require a
Google Maps API key. Google may change that HTML or require JavaScript/login;
in those cases the CLI reports a useful error instead of returning partial
data silently.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import asdict, dataclass
from typing import Iterable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
)
PLACE_PATH = re.compile(r"^/maps/place/", re.IGNORECASE)


@dataclass
class Place:
    name: str
    url: str
    source_list_url: str
    address: str | None = None
    rating: float | None = None
    review_count: int | None = None


def _clean(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def _number_from_label(label: str | None, pattern: str) -> int | float | None:
    if not label:
        return None
    match = re.search(pattern, label, re.IGNORECASE)
    if not match:
        return None
    try:
        return float(match.group(1)) if "." in match.group(1) else int(match.group(1).replace(",", ""))
    except ValueError:
        return None


def _place_url(href: str, base_url: str) -> str | None:
    absolute = urljoin(base_url, href)
    parsed = urlparse(absolute)
    if parsed.netloc not in {"www.google.com", "google.com", "maps.google.com"}:
        return None
    if not PLACE_PATH.match(parsed.path):
        return None
    # The /data=... suffix is generated per link and is not needed to open
    # the place. Removing it also prevents duplicate cards in a list.
    path = parsed.path.split("/data=", 1)[0]
    return f"https://www.google.com{path}"


def _extract_address(card: BeautifulSoup) -> str | None:
    # Google has used several labels/classes over time. Prefer semantic
    # attributes, then look for a likely address in the card text.
    for element in card.select('[aria-label*="Address"], [data-item-id*="address"]'):
        text = _clean(element.get("aria-label") or element.get_text(" ", strip=True))
        if text:
            return re.sub(r"^Address:\s*", "", text, flags=re.IGNORECASE)
    return None


def parse_places(html: str, source_url: str) -> list[Place]:
    """Parse place entries from already downloaded Google Maps HTML."""
    soup = BeautifulSoup(html, "html.parser")
    places: list[Place] = []
    seen: set[str] = set()

    for link in soup.find_all("a", href=True):
        url = _place_url(link["href"], source_url)
        if not url or url in seen:
            continue
        seen.add(url)
        card = link.find_parent(["div", "li", "article"]) or link.parent
        label = link.get("aria-label")
        name = _clean(label or link.get_text(" ", strip=True))
        if not name:
            name = _clean(urlparse(url).path.split("/maps/place/", 1)[-1].replace("+", " "))

        card_text = _clean(card.get_text(" ", strip=True)) or ""
        rating = _number_from_label(card_text, r"\b([0-5](?:\.\d)?)\s*(?:stars?|/\s*5)\b")
        review_count = _number_from_label(card_text, r"\(([\d,]+)\s*(?:reviews?)?\)")
        places.append(
            Place(
                name=name or "Unknown place",
                url=url,
                source_list_url=source_url,
                address=_extract_address(card),
                rating=float(rating) if isinstance(rating, (int, float)) else None,
                review_count=int(review_count) if isinstance(review_count, (int, float)) else None,
            )
        )
    return places


def extract_page(
    page,
    url: str,
    timeout: float = 20,
    wait_seconds: float = 8,
    interactive: bool = True,
) -> list[Place]:
    """Open a list in a real browser and parse its rendered DOM."""
    page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
    try:
        page.wait_for_load_state("networkidle", timeout=int(timeout * 1000))
    except PlaywrightTimeoutError:
        # Google Maps can keep background requests open indefinitely. The DOM
        # is still usable after the initial page has rendered.
        pass
    page.wait_for_timeout(int(wait_seconds * 1000))
    final_url = page.url
    html = page.content()
    places = parse_places(html, final_url)
    if not places:
        lowered = html.lower()
        is_consent = "consent.google" in lowered
        is_sign_in = "sign in" in lowered or "accounts.google.com" in lowered
        if is_consent or is_sign_in or "captcha" in lowered:
            if is_consent and interactive:
                print(
                    "Google is asking for consent in the browser window. "
                    "Complete consent only, then press Enter here to retry...",
                    file=sys.stderr,
                )
                try:
                    input()
                except EOFError:
                    pass
                page.wait_for_timeout(1500)
                final_url = page.url
                places = parse_places(page.content(), final_url)
                if places:
                    return places
            raise RuntimeError(
                "Google returned a consent, sign-in, or anti-bot page "
                f"(resolved URL: {final_url}). Open the list in a browser, "
                "accept Google's consent if prompted, and make sure the list is shared publicly. "
                "Do not enter Google credentials in the automated browser. "
                "If the list requires sign-in, use a public sharing link or the official API instead."
            )
        raise RuntimeError(
            "No places were found. The list may be private, JavaScript-rendered, or Google may have changed its HTML."
        )
    return places


def read_urls(input_file: str) -> list[str]:
    """Read one URL per line; blank lines and lines beginning with # are ignored."""
    with open(input_file, encoding="utf-8") as file:
        urls = []
        for raw_line in file:
            line = raw_line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
        return urls


def extract_file(
    page,
    input_file: str,
    timeout: float = 20,
    wait_seconds: float = 8,
    interactive: bool = True,
) -> list[Place]:
    places: list[Place] = []
    errors: list[str] = []
    for url in read_urls(input_file):
        try:
            places.extend(extract_page(page, url, timeout, wait_seconds, interactive))
        except (PlaywrightTimeoutError, RuntimeError) as exc:
            errors.append(f"{url}: {exc}")
    if not places and errors:
        raise RuntimeError("No places could be extracted.\n" + "\n".join(errors))
    if errors:
        print("warning: some lists could not be read:", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)
    return places


def write_output(places: Iterable[Place], output_format: str) -> None:
    rows = [asdict(place) for place in places]
    if output_format == "json":
        json.dump(rows, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return
    writer = csv.DictWriter(sys.stdout, fieldnames=rows[0].keys() if rows else ["name", "url", "address", "rating", "review_count"])
    writer.writeheader()
    writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract places from public Google Maps list URLs in a text file.")
    parser.add_argument(
        "input_file",
        nargs="?",
        default="data/private/links.txt",
        help="Text file containing one list URL per line (default: data/private/links.txt)",
    )
    parser.add_argument("-o", "--output", choices=("json", "csv"), default="json")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--wait-seconds", type=float, default=8, help="Seconds to leave the browser open for consent/login (default: 8)")
    parser.add_argument("--headless", action="store_true", help="Run without a visible browser; consent/login cannot be completed interactively")
    parser.add_argument(
        "--browser-channel",
        choices=("chromium", "msedge", "chrome"),
        default="chromium",
        help="Browser to launch (default: Playwright Chromium)",
    )
    args = parser.parse_args()
    try:
        with sync_playwright() as playwright:
            profile_dir = ".playwright-profile"
            browser_channel = None if args.browser_channel == "chromium" else args.browser_channel
            context = playwright.chromium.launch_persistent_context(
                profile_dir,
                headless=args.headless,
                channel=browser_channel,
                user_agent=USER_AGENT,
                locale="en-US",
                viewport={"width": 1440, "height": 1000},
            )
            try:
                page = context.pages[0] if context.pages else context.new_page()
                places = extract_file(
                    page,
                    args.input_file,
                    args.timeout,
                    args.wait_seconds,
                    interactive=not args.headless,
                )
            finally:
                context.close()
        write_output(places, args.output)
        return 0
    except (PlaywrightTimeoutError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
