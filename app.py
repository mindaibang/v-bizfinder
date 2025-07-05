import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://masothue.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/114.0.0.0 Safari/537.36"
}

def fetch_new_companies(pages=5):
    """
    Lấy danh sách doanh nghiệp mới nhất từ masothue.com
    """
    rows = []
    for page in range(1, pages + 1):
        url = f"{BASE_URL}/tra-cuu-ma-so-thue-doanh-nghiep-moi-thanh-lap?page={page}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for li in soup.select(".tax-listing li"):
                name_tag = li.find("a", class_="tax-name")
                mst_tag = li.find("div", class_="tax-code")
                addr_tag = li.find("span", class_="address")
                rep_tag = li.find("span", class_="legal-represent")

                if name_tag and mst_tag and addr_tag:
                    name = name_tag.get_text(strip=True)
                    mst = mst_tag.get_text(strip=True).replace("Mã số thuế:", "").strip()
                    address = addr_tag.get_text(strip=True)
                    representative = rep_tag.get_text(strip=True) if rep_tag else ""
                    link = BASE_URL + name_tag["href"]

                    rows.append({
                        "Tên doanh nghiệp": name,
                        "Mã số thuế": mst,
                        "Người đại diện": representative,
                        "Địa chỉ": address,
                        "Link": link
                    })
        except Exception as e:
            st.error(f"Lỗi khi tải trang {page}: {e}")
    return pd.DataFrame(rows)


# ==================
# UI Streamlit
st.title("📊 Tra cứu doanh nghiệp mới thành lập")

if st.button("🔍 Tra cứu 5 trang mới nhất"):
    st.info("⏳ Đang tải dữ liệu...")
    df = fetch_new_companies()
    if df.empty:
        st.warning("⚠️ Không tìm thấy dữ liệu.")
    else:
        st.success(f"✅ Tìm thấy {len(df)} doanh nghiệp")
        st.dataframe(df, use_container_width=True)
