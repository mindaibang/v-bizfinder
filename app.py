import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import os

BASE_URL = "https://masothue.com"
HISTORY_FILE = "history.json"

# ========== File handling ==========
def save_json_file(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json_file(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# ========== Crawl ==========
def fetch_new_companies(limit_pages=5):
    """
    Crawl doanh nghiệp mới thành lập từ masothue.com (đi qua tối đa limit_pages)
    """
    results = []
    page_url = f"{BASE_URL}/tra-cuu-ma-so-thue-doanh-nghiep-moi-thanh-lap"
    pages_crawled = 0

    while page_url and pages_crawled < limit_pages:
        try:
            resp = requests.get(page_url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Lấy các doanh nghiệp
            listings = soup.select(".tax-listing > div")
            for item in listings:
                a_tag = item.find("a")
                address_tag = item.find("address")
                if a_tag and address_tag:
                    name = a_tag.text.strip()
                    link = BASE_URL + a_tag["href"]
                    address = address_tag.text.strip()
                    results.append({
                        "Tên doanh nghiệp": name,
                        "Địa chỉ": address,
                        "Link": link
                    })

            # Tìm link trang tiếp theo
            next_link = soup.select_one(".page-numbers.current + li a")
            if next_link:
                page_url = BASE_URL + next_link["href"]
            else:
                page_url = None

            pages_crawled += 1

        except Exception as e:
            st.warning(f"⚠️ Lỗi khi tải trang {pages_crawled+1}: {e}")
            break

    return pd.DataFrame(results)

# ========== UI ==========
st.title("📊 Tra cứu doanh nghiệp mới thành lập")

if "search_results" not in st.session_state:
    st.session_state["search_results"] = pd.DataFrame()

if st.button("🔍 Tra cứu"):
    st.info("⏳ Đang tải dữ liệu (5 trang)...")
    df = fetch_new_companies(limit_pages=5)
    if not df.empty:
        st.success(f"✅ Đã tìm thấy {len(df)} doanh nghiệp.")
        st.session_state["search_results"] = df

        # Lưu lịch sử
        history = load_json_file(HISTORY_FILE)
        history.insert(0, {"Tìm kiếm": "5 trang", "Số lượng": len(df)})
        save_json_file(HISTORY_FILE, history[:10])
    else:
        st.warning("⚠️ Không tìm thấy dữ liệu.")

# Hiển thị bảng + lọc tỉnh
if not st.session_state["search_results"].empty:
    provinces = ["Tất cả"] + sorted(set([addr.split(",")[-1].strip() for addr in st.session_state["search_results"]["Địa chỉ"]]))
    selected_province = st.selectbox("📍 Lọc theo tỉnh/TP", provinces)
    if selected_province != "Tất cả":
        filtered_df = st.session_state["search_results"][st.session_state["search_results"]["Địa chỉ"].str.contains(selected_province, case=False)]
    else:
        filtered_df = st.session_state["search_results"]
    st.dataframe(filtered_df, use_container_width=True)

# Lịch sử
st.subheader("⏳ Lịch sử tìm kiếm")
history = load_json_file(HISTORY_FILE)
if history:
    st.table(pd.DataFrame(history))
else:
    st.info("📭 Chưa có lịch sử.")
