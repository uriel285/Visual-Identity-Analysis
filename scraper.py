
import csv
import json
import re
import time
import urllib.request
import urllib.robotparser
import urllib.error

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = "top1400.txt"
OUTPUT_DIR = Path("output")
OUTPUT_FILE = OUTPUT_DIR / "tourism_design_dataset.csv"

USER_AGENT = "TourismDesignResearchBot/1.0"

NAVIGATION_TIMEOUT = 25000
DELAY_BETWEEN_SITES = 2

OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# UTILITIES
# ============================================================

def load_domains(filename):
    domains = []

    with open(filename, "r", encoding="utf-8") as file:
        for line in file:
            value = line.strip()

            if not value or value.startswith("#"):
                continue

            if not value.startswith(("http://", "https://")):
                value = "https://" + value

            parsed = urlparse(value)

            if parsed.netloc:
                domains.append(
                    f"{parsed.scheme}://{parsed.netloc}"
                )

    # Remove duplicates while preserving order
    return list(dict.fromkeys(domains))


def check_robots(url):
    """
    Checks robots.txt before accessing the homepage.
    If robots.txt cannot be retrieved, records the
    uncertainty and proceeds with a low request rate.
    """

    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)

    try:
        request = urllib.request.Request(
            robots_url,
            headers={"User-Agent": USER_AGENT}
        )

        with urllib.request.urlopen(
            request, timeout=8
        ) as response:

            content = response.read().decode(
                "utf-8", errors="replace"
            )

            parser.parse(content.splitlines())

        allowed = parser.can_fetch(USER_AGENT, url)

        return allowed, "available"

    except urllib.error.HTTPError as error:

        if error.code == 404:
            return True, "not_found"

        return True, "unavailable"

    except Exception:
        return True, "unavailable"


def safe_json(value):
    return json.dumps(value, ensure_ascii=False)


# ============================================================
# BROWSER DATA EXTRACTION
# ============================================================

JS_EXTRACTOR = r"""
() => {

    const clean = (value) =>
        value ? value.replace(/\s+/g, " ").trim() : "";

    const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);

        return (
            rect.width > 0 &&
            rect.height > 0 &&
            style.display !== "none" &&
            style.visibility !== "hidden"
        );
    };

    const toHex = (value) => {
        const match = value.match(/\d+/g);

        if (!match || match.length < 3) return null;

        const rgb = match.slice(0, 3).map(Number);

        if (rgb.every(v => v === 0) && value.includes("rgba") &&
            Number(match[3]) === 0) return null;

        return "#" + rgb.map(v =>
            v.toString(16).padStart(2, "0")
        ).join("").toUpperCase();
    };

    const colorFrequency = {
        backgrounds: {},
        text: {},
        borders: {}
    };

    const fontFrequency = {};

    const elements = [
        ...document.querySelectorAll("body *")
    ].filter(visible).slice(0, 4000);

    let stickyElements = 0;
    let gridElements = 0;
    let flexElements = 0;

    elements.forEach(el => {

        const style = getComputedStyle(el);

        const bg = toHex(style.backgroundColor);
        const color = toHex(style.color);
        const border = toHex(style.borderTopColor);

        const add = (object, key) => {
            if (key) {
                object[key] = (object[key] || 0) + 1;
            }
        };

        add(colorFrequency.backgrounds, bg);
        add(colorFrequency.text, color);
        add(colorFrequency.borders, border);

        const font = style.fontFamily.split(",")[0]
            .replace(/["']/g, "").trim();

        add(fontFrequency, font);

        if (
            style.position === "sticky" ||
            style.position === "fixed"
        ) {
            stickyElements++;
        }

        if (style.display === "grid") gridElements++;
        if (style.display === "flex") flexElements++;
    });

    const sorted = (object, limit = 15) =>
        Object.entries(object)
            .sort((a, b) => b[1] - a[1])
            .slice(0, limit)
            .map(([value, count]) => ({ value, count }));

    // IMAGES

    const images = [
        ...document.querySelectorAll("img")
    ].map(img => {

        const rect = img.getBoundingClientRect();

        return {
            src: img.currentSrc || img.src,
            alt: clean(img.alt),
            width: img.naturalWidth || img.width,
            height: img.naturalHeight || img.height,
            display_width: Math.round(rect.width),
            display_height: Math.round(rect.height),
            loading: img.loading,
            object_fit: getComputedStyle(img).objectFit,
            class_name: String(img.className || "").slice(0, 200)
        };

    }).filter(img => img.src).slice(0, 150);

    const largeImages = images.filter(img =>
        img.display_width >= 300 &&
        img.display_height >= 180
    );

    // LOGO CANDIDATES

    const logoSelectors = [
        "header img",
        "header svg",
        "img[alt*='logo' i]",
        "[class*='logo' i] img",
        "[class*='logo' i] svg",
        "[id*='logo' i] img",
        "[id*='logo' i] svg"
    ].join(",");

    const logoCandidates = [
        ...document.querySelectorAll(logoSelectors)
    ].filter(visible).slice(0, 20).map(el => {

        const rect = el.getBoundingClientRect();

        return {
            tag: el.tagName,
            src: el.currentSrc || el.src || "",
            alt: el.alt || "",
            class_name: String(el.className || "").slice(0, 200),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            view_box: el.getAttribute("viewBox") || ""
        };

    });

    // HEADINGS

    const headings = {};

    ["h1", "h2", "h3"].forEach(tag => {
        headings[tag] = [
            ...document.querySelectorAll(tag)
        ].filter(visible).slice(0, 30)
         .map(el => clean(el.innerText))
         .filter(Boolean);
    });

    // HERO

    const hero = document.querySelector(
        "main section, main, header + section, .hero, [class*='hero' i]"
    );

    let heroData = null;

    if (hero) {

        const style = getComputedStyle(hero);
        const rect = hero.getBoundingClientRect();

        heroData = {
            tag: hero.tagName,
            class_name: String(hero.className || "").slice(0, 200),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            background_color: style.backgroundColor,
            background_image: style.backgroundImage,
            text: clean(hero.innerText).slice(0, 1000)
        };
    }

    // NAVIGATION

    const header = document.querySelector("header");

    let headerPosition = "not_found";

    if (header) {
        headerPosition = getComputedStyle(header).position;
    }

    const nav = document.querySelector("nav");

    const navLinks = nav ? [
        ...nav.querySelectorAll("a")
    ].map(a => clean(a.innerText)).filter(Boolean) : [];

    // SEARCH

    const searchInputs = [
        ...document.querySelectorAll(
            'input[type="search"], input[placeholder], [role="search"]'
        )
    ].filter(visible).map(el => ({
        type: el.type || el.getAttribute("role") || "",
        placeholder: el.placeholder || "",
        aria_label: el.getAttribute("aria-label") || ""
    })).slice(0, 30);

    // CTA / BUTTONS

    const buttons = [
        ...document.querySelectorAll(
            "button, a[role='button'], input[type='submit']"
        )
    ].filter(visible);

    // CARD HEURISTICS

    const cardElements = elements.filter(el => {
        const value = (
            (typeof el.className === "string" ? el.className : "") +
            " " + (el.id || "")
        ).toLowerCase();

        return /card|tile|listing|result-item|product-item/.test(value);
    });

    // VIDEOS / SVG / SOCIAL

    const videos = [
        ...document.querySelectorAll("video, iframe")
    ];

    const svgElements = [
        ...document.querySelectorAll("svg")
    ];

    const socialLinks = [
        ...document.querySelectorAll("a[href]")
    ].map(a => a.href).filter(url =>
        /instagram\.com|facebook\.com|youtube\.com|tiktok\.com|pinterest\.com|linkedin\.com|x\.com/.test(url)
    );

    // META DATA

    const meta = (name, attribute = "name") => {
        const el = document.querySelector(
            `meta[${attribute}="${name}"]`
        );
        return el ? el.content : "";
    };

    const canonical = document.querySelector(
        'link[rel="canonical"]'
    );

    const favicon = document.querySelector(
        'link[rel*="icon"]'
    );

    const jsonLd = [
        ...document.querySelectorAll(
            'script[type="application/ld+json"]'
        )
    ].map(el => el.textContent.slice(0, 5000));

    const cssLinks = [
        ...document.querySelectorAll('link[rel="stylesheet"]')
    ].map(el => el.href).slice(0, 50);

    const fontFaces = [
        ...document.fonts
    ].map(font => font.family);

    const viewport = meta("viewport");

    return {

        title: document.title,
        description: meta("description"),
        keywords: meta("keywords"),

        language: document.documentElement.lang,
        canonical: canonical ? canonical.href : "",

        robots: meta("robots"),

        og_title: meta("og:title", "property"),
        og_description: meta("og:description", "property"),
        og_image: meta("og:image", "property"),
        og_type: meta("og:type", "property"),

        twitter_card: meta("twitter:card"),

        favicon: favicon ? favicon.href : "",
        viewport: viewport,

        headings: headings,

        images: images,
        large_images: largeImages,
        image_count: images.length,
        large_image_count: largeImages.length,

        logo_candidates: logoCandidates,
        logo_candidate_count: logoCandidates.length,

        hero: heroData,

        background_colors: sorted(colorFrequency.backgrounds),
        text_colors: sorted(colorFrequency.text),
        border_colors: sorted(colorFrequency.borders),

        font_families: sorted(fontFrequency, 20),
        loaded_fonts: [...new Set(fontFaces)],

        header_position: headerPosition,
        nav_links: navLinks,

        search_inputs: searchInputs,
        search_present: searchInputs.length > 0,

        button_count: buttons.length,
        card_candidate_count: cardElements.length,

        sticky_elements: stickyElements,
        grid_elements: gridElements,
        flex_elements: flexElements,

        video_count: videos.length,
        svg_count: svgElements.length,

        social_links: [...new Set(socialLinks)].slice(0, 30),

        css_files: cssLinks,
        json_ld: jsonLd,

        body_text_length: document.body.innerText.length
    };
}
"""


# ============================================================
# MAIN SCRAPER
# ============================================================

def scrape_site(browser, original_url):

    result = {
        "original_url": original_url,
        "final_url": "",
        "domain": urlparse(original_url).netloc,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "http_status": None,
        "robots_status": "",
        "scrape_status": "error",
        "error": ""
    }

    allowed, robots_status = check_robots(original_url)
    result["robots_status"] = robots_status

    if not allowed:
        result["scrape_status"] = "blocked_by_robots"
        return result

    page = browser.new_page(
        viewport={"width": 1440, "height": 900},
        user_agent=USER_AGENT
    )

    try:

        try:
            response = page.goto(
                original_url,
                wait_until="domcontentloaded",
                timeout=NAVIGATION_TIMEOUT
            )

        except PlaywrightTimeout:
            # A page may render useful content despite a timeout.
            response = None

        if response is None and not page.url:
            raise Exception("Navigation failed")

        result["final_url"] = page.url
        result["http_status"] = (
            response.status if response else None
        )

        page.wait_for_timeout(1500)

        # Extract rendered DOM and computed CSS
        data = page.evaluate(JS_EXTRACTOR)

        result["scrape_status"] = "success"

        # Flatten nested fields into CSV-friendly columns
        for key, value in data.items():

            if isinstance(value, (list, dict)):
                result[key] = safe_json(value)
            else:
                result[key] = value

    except Exception as error:

        result["error"] = str(error)[:500]
        result["scrape_status"] = "error"

    finally:
        page.close()

    return result


# ============================================================
# EXECUTION
# ============================================================

def main():

    domains = load_domains(INPUT_FILE)

    print(f"Domains loaded: {len(domains)}")

    if not domains:
        print("No valid domains found.")
        return

    results = []

    with sync_playwright() as playwright:

        browser = playwright.chromium.launch(
            headless=True
        )

        for index, domain in enumerate(domains, start=1):

            print(
                f"[{index}/{len(domains)}] Scraping {domain}"
            )

            result = scrape_site(browser, domain)

            results.append(result)

            print(
                f"  Status: {result['scrape_status']}"
            )

            # Save progress after every domain
            fieldnames = list(dict.fromkeys(
                key
                for row in results
                for key in row.keys()
            ))

            with open(
                OUTPUT_FILE,
                "w",
                newline="",
                encoding="utf-8-sig"
            ) as file:

                writer = csv.DictWriter(
                    file,
                    fieldnames=fieldnames
                )

                writer.writeheader()
                writer.writerows(results)

            time.sleep(DELAY_BETWEEN_SITES)

        browser.close()

    print("\n================================")
    print("SCRAPING FINISHED")
    print(f"Total domains: {len(domains)}")
    print(f"Successful: {sum(r['scrape_status'] == 'success' for r in results)}")
    print(f"Failed: {sum(r['scrape_status'] == 'error' for r in results)}")
    print(f"CSV: {OUTPUT_FILE}")
    print("================================")


if __name__ == "__main__":
    main()
