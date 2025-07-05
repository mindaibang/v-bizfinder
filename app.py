import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import bcrypt
import json
import os

# ===========================
# CONFIG
BASE_URL = "https://masothue.com"
USERS_FILE = "users.json"
WATCHLIST_FILE = "watchlist.json"

# ===========================
# AUTHENTICATION
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    admin_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
    users = {"admin": admin_hash}
    save_json_file(USERS_FILE, users)
    return users

def verify_user(username, password):
    users = load_users()
    if username in users:
        hashed_pw = users[username].encode("utf-8")
        return bcrypt.checkpw(password.encode(), hashed_pw)
    return False

def save_json_file(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json_file(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

# ===========================
# FETCH DATA
def fetch_new_companies(pages=5):
    """
    Crawl 5 trang mới nhất
    """
    rows = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36"
    }
    for page in range(1, pages + 1):
        url = f"{BASE_URL}/tra-cuu-ma-so-thue-doanh-nghiep-moi-thanh-lap?page={page}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = soup.select("div.tax-listing div[data-prefetch]")
            for div in listings:
                a_tag = div.find("a")
                addr_tag = div.find("address")
                tax_code = div.get("data-prefetch").split("-")[0] if div.get("data-prefetch") else ""
                if a_tag and addr_tag:
                    name = a_tag.get_text(strip=True)
                    link = BASE_URL + a_tag['href']
                    address = addr_tag.get_text(strip=True)
                    rows.append({
                        "Tên doanh nghiệp": name,
                        "Mã số thuế": tax_code,
                        "Địa chỉ": address,
                        "Link": link  # Ẩn cột này khi hiển thị
                    })
        except Exception as e:
            st.error(f"⚠️ Lỗi khi tải trang {page}: {e}")
    return pd.DataFrame(rows)

def fetch_company_details(link):
    """
    Crawl trang chi tiết doanh nghiệp
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36"
    }
    details = {}
    try:
        resp = requests.get(link, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.select_one("table.table-taxinfo")
        if table:
            rows = table.select("tr")
            for row in rows:
                cols = row.select("td")
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    details[key] = value
    except Exception as e:
        st.error(f"⚠️ Lỗi khi tải chi tiết: {e}")
    return details

# ===========================
# UI COMPONENTS
def show_login():
    st.title("🔒 Đăng nhập")
    username = st.text_input("Tên đăng nhập")
    password = st.text_input("Mật khẩu", type="password")
    if st.button("Đăng nhập"):
        if verify_user(username, password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.success(f"✅ Xin chào {username}!")
            st.rerun()
        else:
            st.error("❌ Sai tên đăng nhập hoặc mật khẩu")

def tra_cuu_tab():
    st.header("📊 Tra cứu doanh nghiệp mới thành lập")
    if st.button("🔍 Tra cứu 5 trang mới nhất"):
        st.info("⏳ Đang tải dữ liệu...")
        df = fetch_new_companies()
        if df.empty:
            st.warning("⚠️ Không tìm thấy dữ liệu.")
        else:
            st.session_state["search_results"] = df
            st.success(f"✅ Đã tìm thấy {len(df)} doanh nghiệp mới.")

    if "search_results" in st.session_state:
        df = st.session_state["search_results"]
        st.subheader("📋 Kết quả tìm kiếm")
        df_display = df.drop(columns=["Link"])  # Ẩn cột Link khi hiển thị
        for i in df_display.index:
            cols = st.columns([4,1])
            with cols[0]:
                st.write(df_display.loc[i])
            with cols[1]:
                if st.button(f"⋮ Menu {i}"):
                    choice = st.radio("Chọn hành động:", ["📄 Xem chi tiết", "⭐ Thêm vào theo dõi"], key=f"menu_{i}")
                    if choice == "📄 Xem chi tiết":
                        details = fetch_company_details(df.loc[i, "Link"])
                        with st.modal(f"📄 Chi tiết: {df.loc[i, 'Tên doanh nghiệp']}"):
                            for k, v in details.items():
                                st.markdown(f"**{k}:** {v}")
                    elif choice == "⭐ Thêm vào theo dõi":
                        watchlist = load_json_file(WATCHLIST_FILE)
                        if any(w['Link'] == df.loc[i, "Link"] for w in watchlist):
                            st.info("✅ Doanh nghiệp đã được theo dõi.")
                        else:
                            watchlist.append(df.loc[i].to_dict())
                            save_json_file(WATCHLIST_FILE, watchlist)
                            st.success("✅ Đã thêm vào danh sách theo dõi.")

def theo_doi_tab():
    st.header("👁️ Theo dõi doanh nghiệp")
    watchlist = load_json_file(WATCHLIST_FILE)
    if watchlist:
        df = pd.DataFrame(watchlist).drop(columns=["Link"])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("📭 Danh sách theo dõi trống.")

def quan_ly_user_tab():
    st.header("👑 Quản lý người dùng")
    users = load_users()
    st.table(pd.DataFrame(list(users.keys()), columns=["Tên đăng nhập"]))

# ===========================
# MAIN APP
def main_app():
    st.sidebar.title(f"Xin chào, {st.session_state['username']}")
    pages = ["Tra cứu doanh nghiệp", "Theo dõi doanh nghiệp"]
    if st.session_state["username"] == "admin":
        pages.append("Quản lý người dùng")
    page = st.sidebar.radio("📂 Menu", pages)

    if page == "Tra cứu doanh nghiệp":
        tra_cuu_tab()
    elif page == "Theo dõi doanh nghiệp":
        theo_doi_tab()
    elif page == "Quản lý người dùng":
        quan_ly_user_tab()

    if st.sidebar.button("🚪 Đăng xuất"):
        st.session_state.clear()
        st.rerun()

# ===========================
# ENTRY POINT
if "logged_in" not in st.session_state:
    show_login()
else:
    main_app()
