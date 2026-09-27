import json
from pathlib import Path


PROGRESS_FILE = Path("progress.json")


def load_progress():
    if not PROGRESS_FILE.exists():
        return {
            "total": 0,
            "current": None,
            "lessons": {}
        }
    try: 
        with open(
            PROGRESS_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)
    
    except (json.JSONDecodeError, ValueError):
        # 2. Nếu file lỗi định dạng hoặc trống, cũng trả về dữ liệu mặc định
        return {
            "total": 0,
            "current": None,
            "lessons": {}
        }

def save_progress(progress):
    temp_file = Path("progress.json.tmp")

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            progress,
            f,
            ensure_ascii=False,
            indent=2
        )

    temp_file.replace(PROGRESS_FILE)


def initialize_progress(urls):

    progress = load_progress()

    progress["total"] = len(urls)

    for url in urls:

        if url not in progress["lessons"]:

            progress["lessons"][url] = {
                "status": "pending"
            }

    save_progress(progress)

    return progress


def update_status(
    progress,
    url,
    status,
    **extra
):

    progress["lessons"][url] = {
        "status": status,
        **extra
    }

    progress["current"] = url

    save_progress(progress)


def is_processed(progress, url):

    lesson = progress["lessons"].get(url)

    return (
        lesson is not None
        and lesson["status"] == "processed"
    )


def get_completed_count(progress):

    return sum(
        1
        for lesson in progress["lessons"].values()
        if lesson["status"] == "processed"
    )