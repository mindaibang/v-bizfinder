import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import bcrypt
import json
import os

# ==============================
# CONFIG
BASE_URL = "https://masothue.com"
PROVINCES = ["Tất cả"] + [
    "An Giang", "Bà Rịa - Vũng Tàu", "Bắc Giang", "Bắc Kạn", "Bạc Liêu",
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
USERS_FILE = "users.json"
WATCHLIST_FILE = "watchlist.json"
HISTORY_FILE = "history.json"

# ==============================
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

# ==============================
# FETCH DATA
def fetch_new_companies(province, pages=5):
    rows = []
    for page in range(1, pages + 1):
        url = f"{BASE_URL}/tra-cuu-ma-so-thue-doanh-nghiep-moi-thanh-lap?page={page}"
        try:
            resp = requests.get(url, timeout=10)
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

                    if province == "Tất cả" or province.lower() in address.lower():
                        rows.append({
                            "Tên doanh nghiệp": name,
                            "Mã số thuế": mst,
                            "Người đại diện": representative,
                            "Địa chỉ": address,
                            "Link": link
                        })
        except Exception as e:
            st.error(f"⚠️ Lỗi khi tải trang {page}: {e}")
    return pd.DataFrame(rows)

def fetch_detail(link):
    try:
        resp = requests.get(link, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        info = []
        name = soup.find("h1")
        if name:
            info.append(f"**Tên doanh nghiệp:** {name.get_text(strip=True)}")
        for li in soup.select(".company-info li"):
            text = li.get_text(" ", strip=True)
            info.append(text)
        return "\n\n".join(info)
    except Exception as e:
        return f"⚠️ Lỗi khi tải chi tiết: {e}"

# ==============================
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
    province = st.selectbox("Chọn tỉnh/TP", PROVINCES)
    if st.button("🔍 Tra cứu"):
        st.info("⏳ Đang tải dữ liệu...")
        df = fetch_new_companies(province)
        if not df.empty:
            st.session_state["search_results"] = df
            history = load_json_file(HISTORY_FILE)
            history.insert(0, {"province": province, "count": len(df)})
            save_json_file(HISTORY_FILE, history[:10])  # lưu 10 lần tìm gần nhất
            st.success(f"✅ Đã tìm thấy {len(df)} doanh nghiệp")
        else:
            st.warning("❌ Không tìm thấy dữ liệu")

    if "search_results" in st.session_state:
        df = st.session_state["search_results"]
        st.subheader("📄 Kết quả tìm kiếm")
        st.dataframe(df.drop(columns="Link"), use_container_width=True)

        selected = st.selectbox("🔗 Chọn DN để xem chi tiết", df["Tên doanh nghiệp"])
        selected_row = df[df["Tên doanh nghiệp"] == selected].iloc[0]
        st.markdown("---")
        st.markdown(fetch_detail(selected_row["Link"]))

        if st.button("➕ Thêm vào theo dõi"):
            watchlist = load_json_file(WATCHLIST_FILE)
            if any(item["Mã số thuế"] == selected_row["Mã số thuế"] for item in watchlist):
                st.info("📌 DN đã có trong danh sách theo dõi")
            else:
                watchlist.append(selected_row.to_dict())
                save_json_file(WATCHLIST_FILE, watchlist)
                st.success("✅ Đã thêm vào danh sách theo dõi")

    st.markdown("## 🕑 Lịch sử tìm kiếm")
    history = load_json_file(HISTORY_FILE)
    if history:
        for item in history:
            st.write(f"🔎 **{item['province']}** - {item['count']} doanh nghiệp")

def theo_doi_tab():
    st.header("👁️ Danh sách theo dõi DN")
    watchlist = load_json_file(WATCHLIST_FILE)
    if watchlist:
        df_watch = pd.DataFrame(watchlist)
        st.dataframe(df_watch.drop(columns="Link"), use_container_width=True)
        selected = st.selectbox("🔗 Chọn DN để xem chi tiết", df_watch["Tên doanh nghiệp"])
        selected_row = df_watch[df_watch["Tên doanh nghiệp"] == selected].iloc[0]
        st.markdown("---")
        st.markdown(fetch_detail(selected_row["Link"]))
        if st.button("🗑️ Xoá DN này khỏi theo dõi"):
            watchlist = [item for item in watchlist if item["Mã số thuế"] != selected_row["Mã số thuế"]]
            save_json_file(WATCHLIST_FILE, watchlist)
            st.success("✅ Đã xoá DN khỏi danh sách")
            st.rerun()
    else:
        st.info("📭 Danh sách theo dõi trống")

def quan_ly_user_tab():
    st.header("👑 Quản lý người dùng")
    users = load_users()
    st.subheader(f"📋 Danh sách user ({len(users)} tài khoản)")
    st.table(pd.DataFrame(list(users.keys()), columns=["Tên đăng nhập"]))

    st.subheader("➕ Thêm user mới")
    new_user = st.text_input("Tên đăng nhập mới")
    new_pass = st.text_input("Mật khẩu mới", type="password")
    if st.button("Thêm user"):
        if new_user in users:
            st.warning("⚠️ User đã tồn tại")
        else:
            hashed_pw = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
            users[new_user] = hashed_pw
            save_json_file(USERS_FILE, users)
            st.success(f"✅ Đã thêm user {new_user}")

    st.subheader("🔑 Đổi mật khẩu")
    target_user = st.selectbox("Chọn user", list(users.keys()))
    new_pass2 = st.text_input("Mật khẩu mới cho user", type="password")
    if st.button("Đổi mật khẩu"):
        hashed_pw = bcrypt.hashpw(new_pass2.encode(), bcrypt.gensalt()).decode()
        users[target_user] = hashed_pw
        save_json_file(USERS_FILE, users)
        st.success(f"✅ Đã đổi mật khẩu cho {target_user}")

    st.subheader("🗑 Xoá user")
    user_to_delete = st.selectbox("Chọn user để xoá", [u for u in users.keys() if u != "admin"])
    if st.button("Xoá user"):
        users.pop(user_to_delete)
        save_json_file(USERS_FILE, users)
        st.success(f"✅ Đã xoá user {user_to_delete}")
        st.rerun()

# ==============================
# MAIN APP
def main_app():
    st.sidebar.title(f"Xin chào, {st.session_state['username']}")
    pages = ["📊 Tra cứu DN", "👁️ Theo dõi DN"]
    if st.session_state["username"] == "admin":
        pages.append("👑 Quản lý user")
    page = st.sidebar.radio("📂 Menu", pages)

    if page == "📊 Tra cứu DN":
        tra_cuu_tab()
    elif page == "👁️ Theo dõi DN":
        theo_doi_tab()
    elif page == "👑 Quản lý user":
        quan_ly_user_tab()

    if st.sidebar.button("🚪 Đăng xuất"):
        st.session_state.clear()
        st.rerun()

# ==============================
# ENTRY POINT
if "logged_in" not in st.session_state:
    show_login()
else:
    main_app()
