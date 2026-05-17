import csv
import re
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

OUTPUT_FILE = "booklog_import.csv"

def clean_text(s):
    return re.sub(r"\s+", " ", s or "").strip()

def normalize_date(s):
    s = clean_text(s)

    m = re.search(r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d} 00:00:00"

    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d} 00:00:00"

    return ""

def extract_asin(html):
    patterns = [
        r'"asin"\s*:\s*"([^"]+)"',
        r"'asin'\s*:\s*'([^']+)'",
        r"asin['\"]?\s*[:=]\s*['\"]([A-Z0-9]{10})['\"]",
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/b/([A-Z0-9]{10})",
    ]

    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group(1)

    return ""

def extract_review_id(html):
    m = re.search(r"/reviews/(\d+)", html)
    return m.group(1) if m else ""

def safe_goto(page, url, wait_seconds=1.0, label="ページ"):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        print(f"{label}遷移で警告: {e}")
        print("現在のページ内容で処理を続行します。")

    page.wait_for_timeout(int(wait_seconds * 1000))

def parse_books_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    items = []

    candidates = soup.select(".book, .book__detail, .detail, li, article")
    seen = set()

    for node in candidates:
        node_html = str(node)

        asin = extract_asin(node_html)
        if not asin:
            continue

        read_date = ""

        date_node = node.select_one(".detail__date")
        if date_node:
            read_date = normalize_date(date_node.get_text(" "))

        if not read_date:
            read_date = normalize_date(node.get_text(" "))

        review_id = extract_review_id(node_html)

        title = ""
        img = node.select_one("img")
        if img:
            title = img.get("alt") or ""

        key = (asin, read_date, review_id)
        if key in seen:
            continue

        seen.add(key)

        items.append({
            "asin": asin,
            "read_date": read_date,
            "review_id": review_id,
            "title": clean_text(title),
            "review": "",
        })

    return items

def parse_reviews_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    reviews = {}

    for node in soup.select(".review, .review__item, li, article"):
        node_html = str(node)
        rid = extract_review_id(node_html)

        if not rid:
            continue

        content = node.select_one(".review__content")

        if content:
            reviews[rid] = clean_text(content.get_text(" "))

    return reviews

def scrape(user_id, use_reviews=False, max_pages=200, max_review_pages=200, wait=1.0):
    read_url = f"https://bookmeter.com/users/{user_id}/books/read"
    review_url = f"https://bookmeter.com/users/{user_id}/reviews"

    user_data_dir = str(Path("./playwright-profile").expanduser())

    all_books = []
    reviews = {}

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
        )

        page = browser.new_page()

        print("読書メーターを開きます。")
        print("未ログインならブラウザ上でログインしてください。")

        safe_goto(
            page,
            "https://bookmeter.com/login",
            wait_seconds=wait,
            label="ログインページ"
        )

        input("ログインできたら Enter を押してください: ")

        for n in range(1, max_pages + 1):
            url = f"{read_url}?page={n}"

            print(f"読んだ本ページ取得: {url}")

            safe_goto(page, url, wait_seconds=wait, label=f"読んだ本 page={n}")

            html = page.content()

            books = parse_books_from_html(html)

            if not books:
                print(f"本が見つからなかったので停止: page={n}")
                break

            all_books.extend(books)

            print(f"  {len(books)}件")

        if use_reviews:
            print("")
            print("レビュー取得を開始します。")

            for n in range(1, max_review_pages + 1):
                url = f"{review_url}?page={n}"

                print(f"レビューページ取得: {url}")

                safe_goto(page, url, wait_seconds=wait, label=f"レビュー page={n}")

                html = page.content()

                found = parse_reviews_from_html(html)

                if not found:
                    print(f"レビューが見つからなかったので停止: page={n}")
                    break

                reviews.update(found)

                print(f"  {len(found)}件")

        browser.close()

    for book in all_books:
        rid = book.get("review_id")

        if rid and rid in reviews:
            book["review"] = reviews[rid]

    deduped = []
    seen = set()

    for book in all_books:
        key = (book["asin"], book["read_date"])

        if key not in seen:
            seen.add(key)
            deduped.append(book)

    return deduped

def write_booklog_csv(books):
    with open(OUTPUT_FILE, "w", newline="", encoding="cp932", errors="replace") as f:
        writer = csv.writer(f)

        for book in books:
            read_date = book.get("read_date", "")

            writer.writerow([
                "1",
                book.get("asin", ""),
                "",
                "",
                "",
                "読み終わった",
                book.get("review", ""),
                "",
                "",
                read_date,
                read_date,
                book.get("title", ""),
                "",
                "",
                "",
                "",
                "",
            ])

def main():
    print("=== Bookmeter → Booklog CSV Exporter ===")

    user_id = input("読書メーターのユーザーIDを入力してください: ").strip()

    if not user_id.isdigit():
        print("ユーザーIDは数字で入力してください。")
        return

    print("")
    review_answer = input("レビューも取得しますか？ (y/N): ").strip().lower()

    use_reviews = review_answer in ["y", "yes"]

    print("")

    books = scrape(user_id, use_reviews=use_reviews)

    write_booklog_csv(books)

    print("")
    print(f"完了: {OUTPUT_FILE}")
    print(f"出力件数: {len(books)}")

if __name__ == "__main__":
    main()
