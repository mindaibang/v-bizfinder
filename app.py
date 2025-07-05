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
def fetch_new_companies(pages=5):
    """
    Lấy danh sách DN mới thành lập (5 trang)
    """
    rows = []
    for page in range(1, pages + 1):
        url = f"{BASE_URL}/tra-cuu-ma-so-thue-doanh-nghiep-moi-thanh-lap?page={page}"
        try:
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            for li in soup.select(".tax-listing li"):
                name_tag = li.find("a", class_="tax-name")
                addr_tag = li.find("span", class_="address")
                if name_tag and addr_tag:
                    name = name_tag.get_text(strip=True)
                    link = BASE_URL + name_tag["href"]
                    address = addr_tag.get_text(strip=True)
                    rows.append({
                        "Tên doanh nghiệp": name,
                        "Địa chỉ": address,
                        "Link": link
                    })
        except Exception as e:
            st.error(f"⚠️ Lỗi khi tải trang {page}: {e}")
    return pd.DataFrame(rows)

# ==============================
# UI
st.title("📊 Tra cứu doanh nghiệp mới thành lập")

# Nút tra cứu
if st.button("🔍 Tra cứu"):
    st.info("⏳ Đang tải dữ liệu (5 trang)...")
    df = fetch_new_companies(pages=5)

    if not df.empty:
        st.success(f"✅ Đã tìm thấy {len(df)} doanh nghiệp mới.")
        # Lọc tỉnh
        provinces = ["Tất cả"] + sorted(list(set([addr.split(",")[-1].strip() for addr in df["Địa chỉ"]])))
        selected_province = st.selectbox("📍 Lọc theo tỉnh/TP", provinces)

        if selected_province != "Tất cả":
            filtered_df = df[df["Địa chỉ"].str.contains(selected_province, case=False)]
        else:
            filtered_df = df

        st.dataframe(filtered_df, use_container_width=True)

        # Lưu lịch sử
        history = load_json_file(HISTORY_FILE)
        history.insert(0, {
            "Tìm kiếm": "Tất cả DN mới",
            "Số lượng": len(df)
        })
        save_json_file(HISTORY_FILE, history[:10])  # Lưu tối đa 10 dòng

    else:
        st.warning("⚠️ Không tìm thấy dữ liệu.")

# Hiển thị lịch sử
st.subheader("⏳ Lịch sử tìm kiếm")
history = load_json_file(HISTORY_FILE)
if history:
    st.table(pd.DataFrame(history))
else:
    st.info("📭 Chưa có lịch sử.")
