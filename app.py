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
HISTORY_FILE = "history.json"

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
    for page in range(1, pages + 1):
        url = f"{BASE_URL}/tra-cuu-ma-so-thue-doanh-nghiep-moi-thanh-lap?page={page}"
        try:
            resp = requests.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            listings = soup.select("div.tax-listing div[data-prefetch]")
            for div in listings:
                a_tag = div.find("a")
                addr_tag = div.find("address")
                rep_tag = div.find("span", class_="tax-represent")

                if a_tag and addr_tag:
                    name = a_tag.get_text(strip=True)
                    link = BASE_URL + a_tag['href']
                    address = addr_tag.get_text(strip=True)
                    representative = rep_tag.get_text(strip=True) if rep_tag else ""
                    
                    rows.append({
                        "Tên doanh nghiệp": name,
                        "Người đại diện": representative,
                        "Địa chỉ": address,
                        "Link": link
                    })
        except Exception as e:
            st.error(f"⚠️ Lỗi khi tải trang {page}: {e}")
    return pd.DataFrame(rows)

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
            save_json_file(HISTORY_FILE, df.to_dict(orient="records"))
            st.success(f"✅ Đã tìm thấy {len(df)} doanh nghiệp mới.")

    # Hiển thị kết quả tìm kiếm
    if "search_results" in st.session_state:
        df = st.session_state["search_results"]
        st.subheader("📋 Kết quả tìm kiếm")
        st.dataframe(df, use_container_width=True)

        for idx, row in df.iterrows():
            col1, col2 = st.columns([3,1])
            with col1:
                st.markdown(f"**{row['Tên doanh nghiệp']}**")
                st.markdown(f"📍 {row['Địa chỉ']}")
                if row['Người đại diện']:
                    st.markdown(f"👤 {row['Người đại diện']}")
            with col2:
                if st.button(f"🔗 Xem chi tiết #{idx}"):
                    js = f"window.open('{row['Link']}')"
                    st.components.v1.html(f"<script>{js}</script>", height=0)
                if st.button(f"⭐ Theo dõi #{idx}"):
                    if st.confirm(f"Bạn có chắc muốn theo dõi {row['Tên doanh nghiệp']}?"):
                        watchlist = load_json_file(WATCHLIST_FILE)
                        if any(w['Link'] == row['Link'] for w in watchlist):
                            st.info("✅ Doanh nghiệp đã trong danh sách theo dõi.")
                        else:
                            watchlist.append(row.to_dict())
                            save_json_file(WATCHLIST_FILE, watchlist)
                            st.success("✅ Đã thêm vào danh sách theo dõi.")

    # Hiển thị lịch sử tìm kiếm
    st.subheader("🕑 Lịch sử tìm kiếm")
    history = load_json_file(HISTORY_FILE)
    if history:
        df_hist = pd.DataFrame(history)
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.info("📭 Chưa có lịch sử tìm kiếm.")

def theo_doi_tab():
    st.header("👁️ Theo dõi doanh nghiệp")
    watchlist = load_json_file(WATCHLIST_FILE)
    if watchlist:
        df = pd.DataFrame(watchlist)
        st.dataframe(df, use_container_width=True)
        for idx, row in df.iterrows():
            if st.button(f"❌ Bỏ theo dõi #{idx}"):
                if st.confirm(f"Bạn có chắc muốn bỏ theo dõi {row['Tên doanh nghiệp']}?"):
                    watchlist = [w for w in watchlist if w['Link'] != row['Link']]
                    save_json_file(WATCHLIST_FILE, watchlist)
                    st.success("✅ Đã bỏ theo dõi.")
                    st.rerun()
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

    st.subheader("🔑 Reset mật khẩu user")
    target_user = st.selectbox("Chọn user", list(users.keys()))
    if st.button("Reset mật khẩu"):
        if st.confirm(f"Bạn có chắc reset mật khẩu user {target_user}?"):
            new_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
            users[target_user] = new_hash
            save_json_file(USERS_FILE, users)
            st.success(f"✅ Đã reset mật khẩu user {target_user} về mặc định (123456).")

    st.subheader("🗑 Xóa user")
    user_to_delete = st.selectbox("Chọn user để xoá", [u for u in users if u != "admin"])
    if st.button("Xoá user"):
        if st.confirm(f"Bạn có chắc muốn xoá user {user_to_delete}?"):
            users.pop(user_to_delete)
            save_json_file(USERS_FILE, users)
            st.success(f"✅ Đã xoá user {user_to_delete}.")
            st.rerun()

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
