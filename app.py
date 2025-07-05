import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import bcrypt
import os
import time

# ==================== CONFIG ====================
BASE_URL = "https://masothue.com"
USERS_FILE = "users.json"
WATCHLIST_DIR = "watchlists"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# Ensure watchlists directory exists
if not os.path.exists(WATCHLIST_DIR):
    os.makedirs(WATCHLIST_DIR)

# ==================== AUTH ====================
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

def get_watchlist_file(username):
    return os.path.join(WATCHLIST_DIR, f"{username}_watchlist.json")

# ==================== FETCH ====================
def fetch_new_companies():
    rows = []
    try:
        resp = requests.get(BASE_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        listings = soup.select("div.tax-listing div[data-prefetch]")

        for div in listings:
            a_tag = div.find("a")
            addr_tag = div.find("address")
            tax_code = div.get("data-prefetch").split("-")[0].strip("/")
            if a_tag and addr_tag:
                name = a_tag.get_text(strip=True)
                address = addr_tag.get_text(strip=True)
                link = BASE_URL + a_tag['href']
                rows.append({
                    "Tên doanh nghiệp": name,
                    "Mã số thuế": tax_code,
                    "Địa chỉ": address,
                    "Link": link
                })
    except Exception as e:
        st.error(f"⚠️ Lỗi khi tải dữ liệu: {e}")
    return pd.DataFrame(rows)

def fetch_company_details(link):
    details = {}
    try:
        resp = requests.get(link, headers=HEADERS, timeout=10)
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

# ==================== UI ====================
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
    st.write("Dành tặng riêng cho các VietinBanker")

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
        st.dataframe(df, use_container_width=True)

        st.subheader("📌 Thao tác")
        selected = st.number_input("Nhập STT doanh nghiệp để thao tác", min_value=1, max_value=len(df))
        selected_row = df.iloc[selected-1]
        if st.button("📄 Xem chi tiết"):
            details = fetch_company_details(selected_row['Link'])
            st.json(details)
        if st.button("⭐ Thêm vào danh sách theo dõi"):
            watchlist_file = get_watchlist_file(st.session_state['username'])
            watchlist = load_json_file(watchlist_file)
            if any(w['Link'] == selected_row['Link'] for w in watchlist):
                st.info("✅ Doanh nghiệp đã trong danh sách theo dõi.")
            else:
                watchlist.append(selected_row.to_dict())
                save_json_file(watchlist_file, watchlist)
                st.success("✅ Đã thêm vào danh sách theo dõi.")

def theo_doi_tab():
    st.header("👁️ Theo dõi doanh nghiệp")
    watchlist_file = get_watchlist_file(st.session_state['username'])
    watchlist = load_json_file(watchlist_file)
    if watchlist:
        df = pd.DataFrame(watchlist)
        st.dataframe(df, use_container_width=True)

        selected = st.number_input("Nhập STT doanh nghiệp để chỉnh sửa", min_value=1, max_value=len(df))
        note = st.text_area("📝 Ghi chú", df.iloc[selected-1].get("Ghi chú", ""))
        if st.button("💾 Lưu ghi chú"):
            df.at[selected-1, "Ghi chú"] = note
            save_json_file(watchlist_file, df.to_dict(orient="records"))
            st.success("✅ Đã lưu ghi chú.")
        if st.button("🗑 Xoá doanh nghiệp"):
            df = df.drop(df.index[selected-1])
            save_json_file(watchlist_file, df.to_dict(orient="records"))
            st.success("✅ Đã xoá doanh nghiệp.")
            st.rerun()
        if st.button("✏️ Sửa thông tin"):
            st.warning("⚠️ Chức năng này đang được phát triển.")
    else:
        st.info("📭 Danh sách theo dõi trống.")

def quan_ly_user_tab():
    st.header("👑 Quản lý người dùng")
    users = load_users()
    st.subheader(f"📋 Danh sách user (Tổng: {len(users)})")
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

    st.subheader("📂 Thêm user theo lô")
    bulk_users = st.text_area("Nhập danh sách user, mỗi dòng 1 user:pass")
    if st.button("Thêm user theo lô"):
        added = 0
        for line in bulk_users.strip().splitlines():
            u, p = line.split(":")
            if u not in users:
                hashed_pw = bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
                users[u] = hashed_pw
                added += 1
        save_json_file(USERS_FILE, users)
        st.success(f"✅ Đã thêm {added} user mới.")

def huong_dan_tab():
    st.header("📖 Hướng dẫn sử dụng")
    st.markdown("""
    ✅ **Tra cứu DN mới**: Click để lấy danh sách doanh nghiệp mới thành lập.
    ✅ **Theo dõi DN**: Quản lý danh sách doanh nghiệp bạn quan tâm, thêm ghi chú, xoá, sửa.
    ✅ **Quản lý người dùng**: Chỉ user admin mới thấy tab này.
    
    ⚠️ **Lưu ý:**
    - Danh sách doanh nghiệp mới được cập nhật liên tục. Bạn nên tra cứu hàng ngày và thêm vào danh sách theo dõi.
    - Có thể xuất dữ liệu ra Excel để quản lý.
    """)

# ==================== MAIN ====================
def main_app():
    st.sidebar.title(f"Xin chào, {st.session_state['username']}")
    pages = ["Tra cứu DN mới", "Theo dõi DN", "Hướng dẫn"]
    if st.session_state["username"] == "admin":
        pages.append("Quản lý người dùng")
    page = st.sidebar.radio("📂 Menu", pages)

    if page == "Tra cứu DN mới":
        tra_cuu_tab()
    elif page == "Theo dõi DN":
        theo_doi_tab()
    elif page == "Quản lý người dùng":
        quan_ly_user_tab()
    elif page == "Hướng dẫn":
        huong_dan_tab()

    if st.sidebar.button("🚪 Đăng xuất"):
        st.session_state.clear()
        st.rerun()

# ==================== ENTRY ====================
if "logged_in" not in st.session_state:
    show_login()
else:
    main_app()
