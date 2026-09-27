from pathlib import Path
import json
import re
import html

from progress import (
    load_progress,
    update_status,
)


RAW_DIR = Path("raw")
PROCESSED_DIR = Path("processed")


# Các key thường dùng để chứa nội dung lesson.
CONTENT_KEYS = {
    "content",
    "markdown",
    "md",
    "body",
    "html",
    "description",
    "text",
}


def is_html(value):
    if not isinstance(value, str):
        return False

    return bool(
        re.search(
            r"<(?:p|h[1-6]|div|pre|code|ul|ol|li|strong|em|table|blockquote|a)\b",
            value,
            re.IGNORECASE,
        )
    )


def html_to_markdown(value):
    try:
        from markdownify import markdownify
    except ImportError:
        raise RuntimeError(
            "Cần cài markdownify:\n"
            "pip install markdownify"
        )

    return markdownify(
        value,
        heading_style="ATX",
        bullets="-",
    ).strip()


def clean_markdown(value):
    value = value.replace("\r\n", "\n")
    value = value.replace("\r", "\n")

    # Không để quá nhiều dòng trống.
    value = re.sub(r"\n{3,}", "\n\n", value)

    return value.strip() + "\n"


def convert_value(value):
    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    if is_html(value):
        return clean_markdown(
            html_to_markdown(value)
        )

    return clean_markdown(value)


def find_content(data, path=""):
    """
    Tìm field nội dung trong JSON một cách đệ quy.

    Ưu tiên các key:
        content
        markdown
        md
        body
        html
        description
        text

    Trả về:
        (content, path)
    """

    if isinstance(data, dict):

        # Ưu tiên key có tên rõ ràng là content/markdown...
        for key in CONTENT_KEYS:

            if key not in data:
                continue

            value = data[key]

            if isinstance(value, str):
                converted = convert_value(value)

                if converted:
                    return (
                        converted,
                        f"{path}.{key}" if path else key
                    )

        # Nếu chưa tìm thấy thì đi sâu hơn.
        for key, value in data.items():

            child_path = (
                f"{path}.{key}"
                if path
                else key
            )

            result = find_content(
                value,
                child_path
            )

            if result is not None:
                return result

    elif isinstance(data, list):

        for index, value in enumerate(data):

            child_path = (
                f"{path}[{index}]"
            )

            result = find_content(
                value,
                child_path
            )

            if result is not None:
                return result

    return None


def build_output_path(raw_path):
    return (
        PROCESSED_DIR /
        raw_path.with_suffix(".md").name
    )


def process_lesson(url, lesson_info, progress):

    raw_file = lesson_info.get("raw_file")

    if not raw_file:
        print("SKIP: chưa có raw_file")
        return

    raw_path = Path(raw_file)

    if not raw_path.exists():
        print(
            f"SKIP: không tìm thấy {raw_path}"
        )

        update_status(
            progress,
            url,
            "failed",
            error=f"Raw file not found: {raw_path}",
        )

        return

    output_path = build_output_path(raw_path)

    # Nếu đã processed và file vẫn còn,
    # không cần convert lại.
    if (
        lesson_info.get("status") == "processed"
        and output_path.exists()
    ):
        print(
            f"SKIP: {output_path.name}"
        )
        return

    update_status(
        progress,
        url,
        "processing",
        raw_file=str(raw_path),
        markdown_file=str(output_path),
    )

    with open(
        raw_path,
        "r",
        encoding="utf-8"
    ) as f:
        data = json.load(f)

    result = find_content(data)

    if result is None:
        update_status(
            progress,
            url,
            "failed",
            raw_file=str(raw_path),
            error=(
                "Không tìm thấy field content/markdown/"
                "md/body/html/description/text trong JSON"
            ),
        )

        print(
            f"FAILED: không tìm thấy content "
            f"trong {raw_path.name}"
        )
        return

    content, content_path = result

    # Thêm metadata tối thiểu ở đầu file.
    title = lesson_info.get(
        "slug",
        raw_path.stem
    )

    final_content = (
        f"# {title}\n\n"
        f"{content}"
    )

    final_content = clean_markdown(
        final_content
    )

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(final_content)

    update_status(
        progress,
        url,
        "processed",
        raw_file=str(raw_path),
        markdown_file=str(output_path),
        content_path=content_path,
    )

    print(
        f"PROCESSED: {raw_path.name}"
        f" -> {output_path.name}"
    )
    print(
        f"Content field: {content_path}"
    )


def main():

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if not RAW_DIR.exists():
        print("Không có thư mục raw/")
        return

    progress = load_progress()

    lessons = progress.get(
        "lessons",
        {}
    )

    if not lessons:
        print(
            "progress.json chưa có lesson."
        )
        return

    total = len(lessons)

    for index, (url, lesson_info) in enumerate(
        lessons.items(),
        start=1
    ):

        status = lesson_info.get(
            "status"
        )

        # Chỉ process những lesson đã crawl.
        if status not in {
            "crawled",
            "processing",
            "failed",
        }:
            if status == "processed":
                # processed nhưng file có thể đã bị xóa.
                raw_file = lesson_info.get("raw_file")
                markdown_file = lesson_info.get(
                    "markdown_file"
                )

                if (
                    raw_file
                    and markdown_file
                    and Path(markdown_file).exists()
                ):
                    print(
                        f"[{index}/{total}] "
                        f"SKIP processed"
                    )
                    continue

            else:
                print(
                    f"[{index}/{total}] "
                    f"SKIP status={status}"
                )
                continue

        print()
        print("=" * 80)
        print(
            f"[{index}/{total}] "
            f"Processing"
        )
        print(url)

        try:
            process_lesson(
                url,
                lesson_info,
                progress
            )

        except Exception as e:

            update_status(
                progress,
                url,
                "failed",
                error=repr(e),
            )

            print(
                "FAILED:",
                repr(e)
            )


if __name__ == "__main__":
    main()