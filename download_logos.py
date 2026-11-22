
import re
import time
import hashlib
import urllib.request
import urllib.error

from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone

import pandas as pd
from playwright.sync_api import sync_playwright


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "top600.txt"

OUTPUT_DIR = Path("assets/logos")
METADATA_FILE = Path("output/logos_metadata.csv")

USER_AGENT = "TourismDesignResearchBot/1.0"

TIMEOUT = 20000
DELAY = 2

MAX_LOGOS_PER_SITE = 6
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)


# ============================================================
# HELPERS
# ============================================================

def load_domains(filepath):

    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(
            f"Input file not found: {filepath}"
        )

    domains = []

    with path.open("r", encoding="utf-8-sig") as file:

        for line in file:

            domain = line.strip()

            if not domain:
                continue

            # Remove protocol if present
            domain = re.sub(
                r"^https?://",
                "",
                domain,
                flags=re.I
            )

            # Remove paths and trailing slashes
            domain = domain.split("/")[0].strip()

            if domain and domain not in domains:
                domains.append(domain)

    return domains


def safe_filename(value):
    value = re.sub(r"[^a-zA-Z0-9_-]", "_", value)
    return value[:80]


def get_extension(url, content_type):

    path = urlparse(url).path.lower()

    if path.endswith(".svg"):
        return ".svg"

    if path.endswith(".png"):
        return ".png"

    if path.endswith((".jpg", ".jpeg")):
        return ".jpg"

    if path.endswith(".webp"):
        return ".webp"

    if path.endswith(".ico"):
        return ".ico"

    mime = content_type.split(";")[0].strip().lower()

    extensions = {
        "image/svg+xml": ".svg",
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/webp": ".webp",
        "image/x-icon": ".ico",
        "image/vnd.microsoft.icon": ".ico"
    }

    return extensions.get(mime, ".bin")


def valid_image(data, content_type):

    mime = content_type.lower()

    signatures = {
        "image/png": data.startswith(b"\x89PNG"),
        "image/jpeg": data.startswith(b"\xff\xd8\xff"),
        "image/gif": data.startswith(b"GIF8"),
        "image/webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
        "image/x-icon": data.startswith(b"\x00\x00\x01\x00"),
        "image/vnd.microsoft.icon": data.startswith(b"\x00\x00\x01\x00")
    }

    if "svg" in mime:
        return b"<svg" in data[:2048].lower()

    return any(
        signatures.get(mime, False)
        for _ in [0]
    )


def download_asset(url, destination):

    if not url.startswith(("http://", "https://")):
        return None, "invalid_url"

    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT}
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=TIMEOUT
        ) as response:

            content_type = response.headers.get(
                "Content-Type", ""
            )

            content_length = response.headers.get(
                "Content-Length"
            )

            if content_length and int(content_length) > MAX_FILE_SIZE:
                return None, "file_too_large"

            mime = content_type.split(";")[0].lower()

            allowed = (
                mime.startswith("image/") or
                mime in ("application/octet-stream",)
            )

            if not allowed:
                return None, "not_an_image"

            data = response.read(MAX_FILE_SIZE + 1)

            if len(data) > MAX_FILE_SIZE:
                return None, "file_too_large"

            if not valid_image(data, mime):
                return None, "invalid_image_content"

            destination.write_bytes(data)

            return {
                "bytes": len(data),
                "content_type": mime,
                "extension": get_extension(url, content_type),
                "sha256": hashlib.sha256(data).hexdigest()
            }, "success"

    except urllib.error.HTTPError as error:
        return None, f"http_{error.code}"

    except Exception as error:
        return None, str(error)[:200]


# ============================================================
# LOGO DETECTION
# ============================================================

DETECTION_JS = r"""
() => {

    const candidates = [];

    const add = (item) => candidates.push(item);

    const clean = value =>
        value ? value.replace(/\s+/g, " ").trim() : "";

    const visible = el => {
        const r = el.getBoundingClientRect();
        const s = getComputedStyle(el);

        return (
            r.width > 0 &&
            r.height > 0 &&
            s.display !== "none" &&
            s.visibility !== "hidden"
        );
    };

    // IMAGE LOGOS

    const images = [
        ...document.querySelectorAll("img")
    ];

    images.forEach(img => {

        const alt = img.alt || "";
        const cls = typeof img.className === "string"
            ? img.className : "";

        const id = img.id || "";
        const parent = img.closest("header, nav");
        const rect = img.getBoundingClientRect();

        const text = (
            alt + " " + cls + " " + id
        ).toLowerCase();

        const logoHint = /logo|brand|identity|symbol/.test(text);
        const inHeader = !!parent;

        if (!logoHint && !inHeader) return;
        if (!visible(img)) return;

        let score = 0;

        if (logoHint) score += 60;
        if (inHeader) score += 30;
        if (img.naturalWidth > 0) score += 10;

        if (rect.width > 30 && rect.width < 600) {
            score += 10;
        }

        add({
            kind: "logo",
            format: "remote",
            url: img.currentSrc || img.src,
            alt: clean(alt),
            selector: logoHint ? "img_logo_hint" : "header_img",
            width: img.naturalWidth || Math.round(rect.width),
            height: img.naturalHeight || Math.round(rect.height),
            score: score
        });
    });

    // INLINE SVG LOGOS

    const svgs = [
        ...document.querySelectorAll("svg")
    ];

    svgs.forEach(svg => {

        const cls = typeof svg.className === "object"
            ? svg.getAttribute("class") || ""
            : String(svg.className || "");

        const id = svg.id || "";
        const parent = svg.closest("header, nav");

        const text = (cls + " " + id).toLowerCase();

        const logoHint = /logo|brand|identity|symbol/.test(text);
        const inHeader = !!parent;

        if (!logoHint && !inHeader) return;
        if (!visible(svg)) return;

        const rect = svg.getBoundingClientRect();

        let score = 0;

        if (logoHint) score += 60;
        if (inHeader) score += 30;

        const markup = svg.outerHTML;

        if (markup.length < 100000) {
            add({
                kind: "logo",
                format: "inline_svg",
                svg: markup,
                alt: svg.getAttribute("aria-label") || "",
                selector: "inline_svg",
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                score: score + 15
            });
        }
    });

    // HOMEPAGE LINK IMAGES

    const homepageLinks = [
        ...document.querySelectorAll(
            'header a[href="/"], header a[href="./"], header a[aria-label*="home" i]'
        )
    ];

    homepageLinks.forEach(link => {

        const img = link.querySelector("img");

        if (!img || !visible(img)) return;

        add({
            kind: "logo",
            format: "remote",
            url: img.currentSrc || img.src,
            alt: img.alt || "",
            selector: "homepage_link_img",
            width: img.naturalWidth,
            height: img.naturalHeight,
            score: 65
        });
    });

    // FAVICON AND APPLE TOUCH ICONS

    const iconLinks = [
        ...document.querySelectorAll("link[rel]")
    ];

    iconLinks.forEach(link => {

        const rel = (link.rel || "").toLowerCase();

        if (!/icon/.test(rel)) return;

        add({
            kind: rel.includes("apple")
                ? "apple_touch_icon" : "favicon",
            format: "remote",
            url: link.href,
            alt: "",
            selector: "link_icon",
            width: 0,
            height: 0,
            score: rel.includes("apple") ? 50 : 40
        });
    });

    // Deduplicate remote resources

    const seen = new Set();

    return candidates.filter(item => {

        if (item.format === "inline_svg") return true;

        if (!item.url) return false;

        if (seen.has(item.url)) return false;

        seen.add(item.url);
        return true;
    }).sort((a, b) => b.score - a.score);
}
"""


# ============================================================
# PROCESS ONE WEBSITE
# ============================================================

def process_site(browser, domain, url):

    print(f"\nProcessing {domain}: {url}")

    site_folder = OUTPUT_DIR / safe_filename(domain)
    site_folder.mkdir(parents=True, exist_ok=True)

    metadata = []

    page = browser.new_page(
        viewport={"width": 1440, "height": 900},
        user_agent=USER_AGENT
    )

    try:

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=TIMEOUT
        )

        page.wait_for_timeout(1500)

        candidates = page.evaluate(DETECTION_JS)

        page.close()

    except Exception as error:

        print(f"  Detection error: {error}")
        page.close()
        return metadata

    # Separate logo candidates from icons

    logos = [
        item for item in candidates
        if item["kind"] == "logo"
    ][:MAX_LOGOS_PER_SITE]

    icons = [
        item for item in candidates
        if item["kind"] in (
            "favicon", "apple_touch_icon"
        )
    ]

    selected = logos + icons

    logo_counter = 0
    icon_counter = {}

    for candidate in selected:

        kind = candidate["kind"]
        fmt = candidate["format"]

        if kind == "logo":
            logo_counter += 1
            filename_base = (
                "logo_primary" if logo_counter == 1
                else f"logo_variant_{logo_counter}"
            )

        else:
            icon_counter[kind] = icon_counter.get(kind, 0) + 1

            filename_base = (
                "favicon" if kind == "favicon"
                else "apple_touch_icon"
            )

            if icon_counter[kind] > 1:
                filename_base += f"_{icon_counter[kind]}"

        if fmt == "inline_svg":

            extension = ".svg"
            filename = filename_base + extension
            destination = site_folder / filename

            try:
                svg = candidate["svg"]

                if re.search(
                    r"<script|javascript:|onload\s*=",
                    svg,
                    re.I
                ):
                    status = "unsafe_svg_rejected"
                    details = {}

                else:
                    destination.write_text(
                        svg,
                        encoding="utf-8"
                    )

                    status = "success"
                    details = {
                        "bytes": destination.stat().st_size,
                        "content_type": "image/svg+xml",
                        "extension": ".svg"
                    }

            except Exception as error:
                status = str(error)[:200]
                details = {}

            source_url = ""

        else:

            source_url = urljoin(
                url,
                candidate["url"]
            )

            destination = site_folder / (
                filename_base + ".download"
            )

            details, status = download_asset(
                source_url,
                destination
            )

            if status == "success":

                final_extension = details["extension"]

                final_destination = site_folder / (
                    filename_base + final_extension
                )

                destination.rename(final_destination)
                destination = final_destination

            else:
                destination = None

        metadata.append({

            "domain": domain,

            "asset_type": kind,
            "format_detected": (
                details.get("extension", "")
                if details else
                ".svg" if fmt == "inline_svg" else ""
            ),

            "source_url": source_url,
            "local_path": (
                str(destination) if destination else ""
            ),

            "selector": candidate.get("selector", ""),
            "alt_text": candidate.get("alt", ""),

            "width": candidate.get("width", 0),
            "height": candidate.get("height", 0),

            "confidence_score": candidate.get("score", 0),

            "file_size_bytes": (
                details.get("bytes", 0) if details else 0
            ),

            "sha256": (
                details.get("sha256", "") if details else ""
            ),

            "download_status": status,

            "collected_at": datetime.now(
                timezone.utc
            ).isoformat()

        })

        print(f"  {kind}: {status}")

    return metadata


# ============================================================
# MAIN
# ============================================================

def main():

    # Load domains from TXT

    domains = load_domains(INPUT_FILE)

    print("===================================")
    print("LOGO COLLECTION STARTED")
    print(f"Domains loaded: {len(domains)}")
    print("===================================")

    all_metadata = []

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True
        )

        for index, domain in enumerate(domains, start=1):

            # Build URL automatically

            url = f"https://{domain}"

            print(
                f"\n[{index}/{len(domains)}]"
            )

            metadata = process_site(
                browser,
                domain,
                url
            )

            all_metadata.extend(metadata)

            # Save progress after every site

            pd.DataFrame(all_metadata).to_csv(
                METADATA_FILE,
                index=False,
                encoding="utf-8-sig"
            )

            time.sleep(DELAY)

        browser.close()

    print("\n===================================")
    print("LOGO COLLECTION FINISHED")
    print(f"Sites processed: {len(domains)}")
    print(f"Assets found: {len(all_metadata)}")
    print(f"Metadata: {METADATA_FILE}")
    print(f"Files: {OUTPUT_DIR}")
    print("===================================")


if __name__ == "__main__":
    main()
