from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import sys
import io

# 設置標準輸出的編碼為 utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# URL of the race results page
URL = "https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx?RaceDate=2025/03/02&Racecourse=ST&RaceNo=2"

def scrape_race_results():
    with sync_playwright() as p:
        # Launch the browser (headless=False to see the browser in action, set to True for production)
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # Navigate to the URL
            print(f"Navigating to {URL}...")
            page.goto(URL)

            # Wait for the page to fully load (networkidle ensures all dynamic content is loaded)
            page.wait_for_load_state("networkidle", timeout=30000)  # 30 seconds timeout

            # Save the HTML content for debugging
            html_content = page.content()
            with open("debug_playwright.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("HTML content saved to debug_playwright.html")

            # Check if the page title contains "賽果"
            page_title = page.title()
            if "賽果" not in page_title:
                print("找不到賽果標題！請檢查 debug_playwright.html 文件，確認是否包含比賽數據")
                return
            else:
                print("找到賽果標題，繼續提取比賽數據...")

            # Use BeautifulSoup to parse the HTML and extract the race results table
            soup = BeautifulSoup(html_content, "html.parser")
            table = soup.find("table", class_="f_tac table_bd")

            if not table:
                print("未找到比賽數據表格！請檢查頁面結構或 debug_playwright.html 文件")
                return

            # Extract table headers
            headers = [th.get_text(strip=True) for th in table.find("thead").find_all("th")]
            print("Table headers:", headers)

            # Extract table rows
            rows = []
            for tr in table.find("tbody").find_all("tr"):
                row = [td.get_text(strip=True) for td in tr.find_all("td")]
                rows.append(row)

            if not rows:
                print("表格中沒有數據！")
                return

            # Convert to DataFrame for easier handling
            df = pd.DataFrame(rows, columns=headers)
            print("\nExtracted Race Results:")
            print(df)

            # Save the results to a CSV file
            output_file = "race_results.csv"
            df.to_csv(output_file, index=False, encoding="utf-8-sig")  # utf-8-sig for Chinese characters
            print(f"\nRace results saved to {output_file}")

        except Exception as e:
            print(f"發生錯誤：{str(e)}")
            print("請檢查 debug_playwright.html 文件以診斷問題")

        finally:
            # Close the browser
            browser.close()

if __name__ == "__main__":
    # Ensure required libraries are installed
    try:
        import playwright
        import bs4
        import pandas
    except ImportError:
        print("缺少必要的庫！請先安裝以下庫：")
        print("pip install playwright beautifulsoup4 pandas")
        print("然後運行：playwright install")
        exit(1)

    # Run the scraper
    scrape_race_results()