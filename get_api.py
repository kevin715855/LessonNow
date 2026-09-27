from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json

from connect import connect_to_chrome
from progress import (
    load_progress,
    initialize_progress,
    update_status,
    is_processed,
    get_completed_count,
)


API_BASE = "https://roadmap.sh/api/v1-get-ai-course-lesson/"
URLS_FILE = Path("urls.txt")
RAW_DIR = Path("raw")


def load_urls():
    if not URLS_FILE.exists():
        raise FileNotFoundError(
            f"Không tìm thấy {URLS_FILE}"
        )

    with open(URLS_FILE, "r", encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip() and not line.lstrip().startswith("#")
        ]


def parse_lesson_url(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    if "module" not in query or "lesson" not in query:
        raise ValueError(
            "URL phải có ?module=<n>&lesson=<n>"
        )

    module = int(query["module"][0])
    lesson = int(query["lesson"][0])

    if module < 1 or lesson < 1:
        raise ValueError(
            "module và lesson phải >= 1"
        )

    slug = parsed.path.rstrip("/").split("/")[-1]

    if not slug:
        raise ValueError("Không lấy được lesson slug từ URL")

    return slug, module, lesson


def build_api_url(slug, module, lesson):
    # roadmap.sh UI dùng index bắt đầu từ 1,
    # API dùng moduleIndex/lessonIndex bắt đầu từ 0.
    return (
        f"{API_BASE}{slug}"
        f"?moduleIndex={module - 1}"
        f"&lessonIndex={lesson - 1}"
    )


def build_raw_filename(module, lesson, slug):
    safe_slug = "".join(
        c if c.isalnum() or c in "-_" else "-"
        for c in slug
    )

    return (
        f"module-{module:02d}"
        f"-lesson-{lesson:02d}"
        f"-{safe_slug}.json"
    )


def fetch_lesson(page, api_url):
    return page.evaluate(
        """
        async (url) => {
            const response = await fetch(
                url,
                {
                    credentials: "include"
                }
            );

            return {
                status: response.status,
                text: await response.text()
            };
        }
        """,
        api_url,
    )


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    urls = load_urls()

    progress = initialize_progress(urls)

    print(f"Found {len(urls)} lesson URLs")

    playwright = None
    browser = None

    try:
        playwright, browser, context, page = connect_to_chrome()

        print("Chrome connected")
        print("Roadmap page:", page.url)

        for index, url in enumerate(urls, start=1):

            if is_processed(progress, url):
                print(
                    f"[{index}/{len(urls)}] "
                    f"SKIP - already processed"
                )
                continue

            print()
            print("=" * 80)
            print(f"[{index}/{len(urls)}] {url}")

            try:
                slug, module, lesson = parse_lesson_url(url)
                api_url = build_api_url(
                    slug,
                    module,
                    lesson
                )

                raw_filename = build_raw_filename(
                    module,
                    lesson,
                    slug
                )

                raw_path = RAW_DIR / raw_filename

                # Nếu raw đã tồn tại nhưng progress chưa ghi nhận,
                # coi như đã crawl xong để tránh gọi API lại.
                if raw_path.exists():
                    print("RAW đã tồn tại:", raw_path)

                    update_status(
                        progress,
                        url,
                        "crawled",
                        api_url=api_url,
                        raw_file=str(raw_path),
                        module=module,
                        lesson=lesson,
                        slug=slug,
                    )

                    continue

                update_status(
                    progress,
                    url,
                    "crawling",
                    api_url=api_url,
                    module=module,
                    lesson=lesson,
                    slug=slug,
                )

                print("API:", api_url)

                result = fetch_lesson(page, api_url)
                status = result["status"]

                print("STATUS:", status)

                if status != 200:
                    update_status(
                        progress,
                        url,
                        "failed",
                        api_url=api_url,
                        module=module,
                        lesson=lesson,
                        slug=slug,
                        error=(
                            f"HTTP {status}: "
                            f"{result['text'][:1000]}"
                        ),
                    )

                    print("FAILED")
                    continue

                try:
                    data = json.loads(result["text"])
                except json.JSONDecodeError as e:
                    update_status(
                        progress,
                        url,
                        "failed",
                        api_url=api_url,
                        module=module,
                        lesson=lesson,
                        slug=slug,
                        error=f"Invalid JSON: {e}",
                    )

                    print("FAILED: response không phải JSON")
                    continue

                with open(
                    raw_path,
                    "w",
                    encoding="utf-8"
                ) as f:
                    json.dump(
                        data,
                        f,
                        ensure_ascii=False,
                        indent=2,
                    )

                update_status(
                    progress,
                    url,
                    "crawled",
                    api_url=api_url,
                    raw_file=str(raw_path),
                    module=module,
                    lesson=lesson,
                    slug=slug,
                )

                completed = get_completed_count(progress)

                print("SAVED:", raw_path)
                print(
                    f"Progress: "
                    f"{completed}/{len(urls)}"
                )

            except Exception as e:
                update_status(
                    progress,
                    url,
                    "failed",
                    error=repr(e),
                )

                print("FAILED:", repr(e))

    finally:
        if browser is not None:
            browser.close()

        if playwright is not None:
            playwright.stop()


if __name__ == "__main__":
    main()