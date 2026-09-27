from playwright.sync_api import sync_playwright


CDP_URL = "http://127.0.0.1:9222"


def connect_to_chrome():
    """
    Kết nối tới Chrome đang chạy với remote debugging.

    Chrome phải được khởi động với:
        --remote-debugging-port=9222

    Returns:
        playwright instance
        browser
        context
        page
    """

    playwright = sync_playwright().start()

    browser = playwright.chromium.connect_over_cdp(CDP_URL)

    if not browser.contexts:
        playwright.stop()
        raise RuntimeError(
            "Không tìm thấy Chrome context."
        )

    context = browser.contexts[0]

    # Tìm tab roadmap.sh
    page = None

    for p in context.pages:
        if "roadmap.sh" in p.url:
            page = p
            break

    if page is None:
        playwright.stop()
        raise RuntimeError(
            "Không tìm thấy tab roadmap.sh. "
            "Hãy mở roadmap.sh và đăng nhập trước."
        )

    return playwright, browser, context, page


if __name__ == "__main__":

    playwright, browser, context, page = connect_to_chrome()

    print("Connected!")
    print("Listening:", CDP_URL)
    print("Roadmap page:", page.url)

    # Giữ kết nối để kiểm tra thủ công
    input("\nNhấn Enter để đóng kết nối...")

    browser.close()
    playwright.stop()
