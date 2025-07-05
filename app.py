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
WATCHLIST_DIR = "watchlists"
if not os.path.exists(WATCHLIST_DIR):
    os.makedirs(WATCHLIST_DIR)

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

def get_user_watchlist_file(username):
    return os.path.join(WATCHLIST_DIR, f"watchlist_{username}.json")

# ===========================
# FETCH DATA

def fetch_new_companies():
    rows = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        resp = requests.get(BASE_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        listings = soup.select("div.tax-listing div[data-prefetch]")
        for div in listings:
            a_tag = div.find("a")
            addr_tag = div.find("address")
            tax_code = div.get("data-prefetch").split("-")[0].strip("/")
            if a_tag and addr_tag:
                rows.append({
                    "Tên doanh nghiệp": a_tag.get_text(strip=True),
                    "Mã số thuế": tax_code,
                    "Địa chỉ": addr_tag.get_text(strip=True),
                    "Link": BASE_URL + a_tag['href'],
                    "Ghi chú": ""
                })
    except Exception as e:
        st.error(f"⚠️ Lỗi khi tải dữ liệu: {e}")
    return pd.DataFrame(rows)

def fetch_company_details(link):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
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
    st.caption("(Tác giả : Ngô Thị Thơm - VietinBank CN Bảo Lộc - 0919026552; lync: thom.nt)")
    st.markdown("Dành tặng riêng cho các VietinBanker")

    if st.button("🔍 Tra cứu DN mới"):
        st.info("⏳ Đang tải dữ liệu...")
        df = fetch_new_companies()
        if df.empty:
            st.warning("⚠️ Không tìm thấy dữ liệu.")
        else:
            st.session_state["search_results"] = df
            st.success(f"✅ Đã tìm thấy {len(df)} doanh nghiệp mới.")

    if "search_results" in st.session_state:
        df = st.session_state["search_results"]
        st.dataframe(df.drop(columns=["Link"]))

        st.subheader("➕ Thêm DN vào danh sách theo dõi")
        index = st.number_input("Nhập STT DN", min_value=1, max_value=len(df), step=1)
        if st.button("⭐ Thêm vào theo dõi"):
            watchlist_file = get_user_watchlist_file(st.session_state["username"])
            watchlist = load_json_file(watchlist_file)
            new_dn = df.iloc[index - 1].to_dict()
            if any(d['Mã số thuế'] == new_dn['Mã số thuế'] for d in watchlist):
                st.info("✅ DN đã có trong danh sách theo dõi.")
            else:
                watchlist.append(new_dn)
                save_json_file(watchlist_file, watchlist)
                st.success("✅ Đã thêm vào danh sách theo dõi.")

def theo_doi_tab():
    st.header("👁️ Theo dõi doanh nghiệp")
    watchlist_file = get_user_watchlist_file(st.session_state["username"])
    watchlist = load_json_file(watchlist_file)
    
    if watchlist:
        df = pd.DataFrame(watchlist)
        df.index += 1
        st.dataframe(df.drop(columns=["Link"]))

        index = st.number_input("Nhập STT DN để thao tác", min_value=1, max_value=len(df), step=1)
        ghi_chu = st.text_area("📝 Ghi chú", value=df.iloc[index - 1]["Ghi chú"])
        col1, col2, col3, col4 = st.columns(4)
        
        if col1.button("💾 Lưu ghi chú"):
            df.at[index - 1, "Ghi chú"] = ghi_chu
            save_json_file(watchlist_file, df.to_dict(orient="records"))
            st.success("✅ Đã lưu ghi chú.")
        
        if col2.button("📄 Xem chi tiết"):
            details = fetch_company_details(df.iloc[index - 1]["Link"])
            with st.modal(f"📄 Chi tiết: {df.iloc[index - 1]['Tên doanh nghiệp']}"):
                st.json(details)
        
        if col3.button("✏️ Sửa thông tin"):
            st.warning("⚠️ Chức năng sửa đang phát triển.")
        
        if col4.button("🗑 Xoá DN"):
            df = df.drop(df.index[index - 1])
            save_json_file(watchlist_file, df.to_dict(orient="records"))
            st.success("✅ Đã xoá doanh nghiệp.")
            st.rerun()
    else:
        st.info("📭 Danh sách theo dõi trống.")

def quan_ly_user_tab():
    st.header("👑 Quản lý người dùng")
    users = load_users()
    st.table(pd.DataFrame(list(users.keys()), columns=["Tên đăng nhập"]))

    st.subheader("➕ Thêm user mới")
    new_user = st.text_input("Tên đăng nhập mới")
    new_pass = st.text_input("Mật khẩu mới", type="password")
    if st.button("Thêm user"):
        if new_user in users:
            st.warning("⚠️ User đã tồn tại.")
        else:
            hashed_pw = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
            users[new_user] = hashed_pw
            save_json_file(USERS_FILE, users)
            st.success(f"✅ Đã thêm user {new_user}.")

    st.subheader("📥 Thêm user theo lô")
    uploaded_file = st.file_uploader("Tải file JSON user", type="json")
    if uploaded_file and st.button("Import user"):
        batch_users = json.load(uploaded_file)
        for u, p in batch_users.items():
            if u not in users:
                users[u] = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
        save_json_file(USERS_FILE, users)
        st.success("✅ Đã import user theo lô.")

def huong_dan_tab():
    st.header("📖 Hướng dẫn sử dụng")
    st.markdown("""
    - **Tra cứu DN mới**: Lấy danh sách doanh nghiệp mới thành lập.
    - **Theo dõi DN**: Quản lý danh sách doanh nghiệp bạn đang theo dõi.
    - **Quản lý User**: Chỉ user `admin` mới thấy tab này.
    
    ⚠ **Lưu ý**: Danh sách DN mới được cập nhật liên tục, vui lòng tra cứu và lưu vào danh sách theo dõi mỗi ngày.
    """)

# ===========================
# MAIN APP

def main_app():
    st.sidebar.title(f"Xin chào, {st.session_state['username']}")
    pages = ["Tra cứu DN mới", "Theo dõi DN"]
    if st.session_state["username"] == "admin":
        pages.append("Quản lý user")
    pages.append("Hướng dẫn")

    page = st.sidebar.radio("📂 Menu", pages)
    if page == "Tra cứu DN mới":
        tra_cuu_tab()
    elif page == "Theo dõi DN":
        theo_doi_tab()
    elif page == "Quản lý user":
        quan_ly_user_tab()
    elif page == "Hướng dẫn":
        huong_dan_tab()

    if st.sidebar.button("🚪 Đăng xuất"):
        st.session_state.clear()
        st.rerun()

# ===========================
# ENTRY POINT

if "logged_in" not in st.session_state:
    show_login()
else:
