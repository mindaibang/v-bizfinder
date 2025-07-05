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

PROVINCES = [
    "Tất cả", "An Giang", "Bà Rịa - Vũng Tàu", "Bắc Giang", "Bắc Kạn", "Bạc Liêu",
    "Bắc Ninh", "Bến Tre", "Bình Định", "Bình Dương", "Bình Phước",
    "Bình Thuận", "Cà Mau", "Cần Thơ", "Cao Bằng", "Đà Nẵng", "Đắk Lắk",
    "Đắk Nông", "Điện Biên", "Đồng Nai", "Đồng Tháp", "Gia Lai", "Hà Giang",
    "Hà Nam", "Hà Nội", "Hà Tĩnh", "Hải Dương", "Hải Phòng", "Hậu Giang",
    "Hòa Bình", "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu",
    "Lâm Đồng", "Lạng Sơn", "Lào Cai", "Long An", "Nam Định", "Nghệ An",
    "Ninh Bình", "Ninh Thuận", "Phú Thọ", "Phú Yên", "Quảng Bình", "Quảng Nam",
    "Quảng Ngãi", "Quảng Ninh", "Quảng Trị", "Sóc Trăng", "Sơn La", "Tây Ninh",
    "Thái Bình", "Thái Nguyên", "Thanh Hóa", "Thừa Thiên Huế", "Tiền Giang",
    "TP. Hồ Chí Minh", "Trà Vinh", "Tuyên Quang", "Vĩnh Long", "Vĩnh Phúc",
    "Yên Bái"
]

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
    Crawl 5 trang mới nhất và lấy đầy đủ thông tin
    """
    rows = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
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
                tax_code_tag = div.find("div", class_="tax-code")  # Mã số thuế
                rep_tag = div.find("span", class_="tax-represent")  # Người đại diện

                if a_tag and addr_tag:
                    name = a_tag.get_text(strip=True)
                    link = BASE_URL + a_tag['href']
                    address = addr_tag.get_text(strip=True)
                    tax_code = tax_code_tag.get_text(strip=True) if tax_code_tag else ""
                    representative = rep_tag.get_text(strip=True) if rep_tag else ""

                    rows.append({
                        "Tên doanh nghiệp": name,
                        "Mã số thuế": tax_code,
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

    if st.button("🔍 Tra cứu"):
        st.info("⏳ Đang tải dữ liệu (5 trang)...")
        df = fetch_new_companies()
        if df.empty:
            st.warning("⚠️ Không tìm thấy dữ liệu.")
        else:
            st.session_state["search_results"] = df
            st.success(f"✅ Đã tìm thấy {len(df)} doanh nghiệp mới.")

    if "search_results" in st.session_state:
        df = st.session_state["search_results"]
        province_filter = st.selectbox("📍 Lọc theo tỉnh/TP", PROVINCES)
        if province_filter != "Tất cả":
            df_filtered = df[df["Địa chỉ"].str.contains(province_filter, case=False, na=False)]
        else:
            df_filtered = df

        st.dataframe(df_filtered, use_container_width=True)

        for idx, row in df_filtered.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{row['Tên doanh nghiệp']}**")
                st.markdown(f"💼 **Mã số thuế**: {row['Mã số thuế']}")
                st.markdown(f"👤 **Người đại diện**: {row['Người đại diện']}")
                st.markdown(f"📍 **Địa chỉ**: {row['Địa chỉ']}")
            with col2:
                if st.button(f"🔗 Chi tiết #{idx}"):
                    js = f"window.open('{row['Link']}')"
                    st.components.v1.html(f"<script>{js}</script>", height=0)
                if st.button(f"⭐ Theo dõi #{idx}"):
                    watchlist = load_json_file(WATCHLIST_FILE)
                    if any(w['Link'] == row['Link'] for w in watchlist):
                        st.info("✅ Doanh nghiệp đã trong danh sách theo dõi.")
                    else:
                        watchlist.append(row.to_dict())
                        save_json_file(WATCHLIST_FILE, watchlist)
                        st.success("✅ Đã thêm vào danh sách theo dõi.")

def theo_doi_tab():
    st.header("👁️ Theo dõi doanh nghiệp")
    watchlist = load_json_file(WATCHLIST_FILE)
    if watchlist:
        df = pd.DataFrame(watchlist)
        st.dataframe(df, use_container_width=True)
        for idx, row in df.iterrows():
            if st.button(f"❌ Bỏ theo dõi #{idx}"):
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
        new_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
        users[target_user] = new_hash
        save_json_file(USERS_FILE, users)
        st.success(f"✅ Đã reset mật khẩu user {target_user} về mặc định (123456).")

    st.subheader("🗑 Xóa user")
    user_to_delete = st.selectbox("Chọn user để xoá", [u for u in users if u != "admin"])
    if st.button("Xoá user"):
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
