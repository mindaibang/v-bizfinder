import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import os

# ==============================
# CONFIG
BASE_URL = "https://masothue.com"
HISTORY_FILE = "history.json"

# ==============================
# FILE HANDLING
def save_json_file(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json_file(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# ==============================
# CRAWLER
def get_total_pages():
    """
    Lấy số trang tối đa từ phân trang
    """
    try:
        resp = requests.get(f"{BASE_URL}/tra-cuu-ma-so-thue-doanh-nghiep-moi-thanh-lap", timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        page_numbers = [int(span.text) for span in soup.select(".page-numbers") if span.text.isdigit()]
        return max(page_numbers) if page_numbers else 1
    except Exception as e:
        st.error(f"⚠️ Không lấy được số trang: {e}")
        return 1

def fetch_new_companies():
    """
    Crawl toàn bộ DN mới thành lập (tất cả các trang)
    """
    rows = []
    total_pages = get_total_pages()
    for page in range(1, total_pages + 1):
        st.info(f"⏳ Đang tải dữ liệu (trang {page}/{total_pages})...")
        url = f"{BASE_URL}/tra-cuu-ma-so-thue-doanh-nghiep-moi-thanh-lap?page={page}"
        try:
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            items = soup.select("div.tax-listing h3 > a")
            for a_tag in items:
                name = a_tag.get_text(strip=True)
                link = BASE_URL + a_tag['href']
                parent_div = a_tag.find_parent("div")
                address_tag = parent_div.find_next("address")
                address = address_tag.get_text(strip=True) if address_tag else ""
                rows.append({
                    "Tên doanh nghiệp": name,
                    "Địa chỉ": address,
                    "Link": link
                })
        except Exception as e:
            st.error(f"⚠️ Lỗi khi tải trang {page}: {e}")
    return pd.DataFrame(rows)

# ==============================
# MAIN APP
def main():
    st.title("📊 Tra cứu doanh nghiệp mới thành lập")

    if st.button("🔍 Tra cứu"):
        st.session_state["search_results"] = fetch_new_companies()
        # Lưu vào lịch sử
        history = load_json_file(HISTORY_FILE)
        history.insert(0, {"Tìm kiếm": "Tất cả DN mới", "Số lượng": len(st.session_state["search_results"])})
        save_json_file(HISTORY_FILE, history)
        st.success(f"✅ Đã tìm thấy {len(st.session_state['search_results'])} doanh nghiệp mới.")

    if "search_results" in st.session_state and not st.session_state["search_results"].empty:
        df = st.session_state["search_results"]
        provinces = ["Tất cả"] + sorted(set([addr.split(",")[-1].strip() for addr in df["Địa chỉ"] if "," in addr]))
        selected_province = st.selectbox("📍 Lọc theo tỉnh/TP", provinces)
        if selected_province != "Tất cả":
            filtered_df = df[df["Địa chỉ"].str.contains(selected_province, case=False, na=False)]
        else:
            filtered_df = df
        st.dataframe(filtered_df, use_container_width=True)

    st.header("⏱️ Lịch sử tìm kiếm")
    history = load_json_file(HISTORY_FILE)
    if history:
        hist_df = pd.DataFrame(history)
        st.table(hist_df)
    else:
        st.info("📭 Chưa có lịch sử tìm kiếm nào.")

# ==============================
# ENTRY POINT
if __name__ == "__main__":
    main()
