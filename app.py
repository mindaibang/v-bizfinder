import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import bcrypt
import json
import os

# ========== CONFIG ==========
BASE_URL = "https://masothue.com"
USERS_FILE = "users.json"
WATCHLIST_DIR = "watchlists"
if not os.path.exists(WATCHLIST_DIR):
    os.makedirs(WATCHLIST_DIR)

# ========== AUTH ==========
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
        return bcrypt.checkpw(password.encode(), users[username].encode())
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
    return os.path.join(WATCHLIST_DIR, f"watchlist_{username}.json")

# ========== FETCH ==========
def fetch_company_details(link):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    details = {}
    try:
        resp = requests.get(link, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.select_one("table.table-taxinfo")
        if table:
            for row in table.select("tr"):
                cols = row.select("td")
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    details[key] = value
    except Exception as e:
        st.error(f"⚠️ Lỗi khi tải chi tiết: {e}")
    return details

# ========== UI ==========
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

def theo_doi_tab():
    st.header("👁️ Theo dõi doanh nghiệp")
    watchlist_file = get_watchlist_file(st.session_state["username"])
    watchlist = load_json_file(watchlist_file)

    if watchlist:
        df = pd.DataFrame(watchlist)
        df.index += 1  # STT từ 1
        selected = st.dataframe(df[["Tên doanh nghiệp", "Mã số thuế", "Địa chỉ", "Ghi chú"]], use_container_width=True)

        st.markdown("💡 *Click vào dòng để xem chi tiết*")
        for idx, row in df.iterrows():
            if st.button(f"📄 Chi tiết: {row['Tên doanh nghiệp']}", key=f"detail_{idx}"):
                details = fetch_company_details(row["Link"])
                with st.expander(f"📄 Thông tin chi tiết: {row['Tên doanh nghiệp']}", expanded=True):
                    for k, v in details.items():
                        st.markdown(f"**{k}**: {v}")

        selected_idx = st.number_input("Nhập STT doanh nghiệp để chỉnh sửa", min_value=1, max_value=len(df), step=1)
        selected_row = df.iloc[selected_idx - 1]
        note = st.text_area("📝 Ghi chú", value=selected_row.get("Ghi chú", ""), key=f"note_{selected_idx}")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 Lưu ghi chú"):
                watchlist[selected_idx - 1]["Ghi chú"] = note
                save_json_file(watchlist_file, watchlist)
                st.success("✅ Đã lưu ghi chú.")
        with col2:
            if st.button("✏️ Sửa thông tin"):
                new_name = st.text_input("🏢 Sửa tên DN", selected_row["Tên doanh nghiệp"])
                new_mst = st.text_input("🆔 Sửa mã số thuế", selected_row["Mã số thuế"])
                new_addr = st.text_input("📍 Sửa địa chỉ", selected_row["Địa chỉ"])
                if st.button("💾 Lưu chỉnh sửa"):
                    watchlist[selected_idx - 1]["Tên doanh nghiệp"] = new_name
                    watchlist[selected_idx - 1]["Mã số thuế"] = new_mst
                    watchlist[selected_idx - 1]["Địa chỉ"] = new_addr
                    save_json_file(watchlist_file, watchlist)
                    st.success("✅ Đã lưu chỉnh sửa.")
                    st.rerun()
        with col3:
            if st.button("🗑 Xoá doanh nghiệp"):
                watchlist.pop(selected_idx - 1)
                save_json_file(watchlist_file, watchlist)
                st.success("✅ Đã xoá khỏi danh sách.")
                st.rerun()
    else:
        st.info("📭 Danh sách theo dõi trống.")

def quan_ly_user_tab():
    st.header("👑 Quản lý người dùng")
    users = load_users()
    st.subheader("📋 Danh sách user")
    st.table(pd.DataFrame(list(users.keys()), columns=["Tên đăng nhập"]))

    st.subheader("➕ Thêm user mới")
    new_user = st.text_input("Tên đăng nhập")
    new_pass = st.text_input("Mật khẩu", type="password")
    if st.button("Thêm user"):
        if new_user in users:
            st.warning("⚠️ User đã tồn tại.")
        else:
            hashed_pw = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
            users[new_user] = hashed_pw
            save_json_file(USERS_FILE, users)
            st.success(f"✅ Đã thêm user {new_user}.")

    st.subheader("📥 Thêm user theo lô")
    uploaded_file = st.file_uploader("Tải file Excel (cột A: username, cột B: password)", type=["xlsx"])
    if uploaded_file:
        df_users = pd.read_excel(uploaded_file)
        for _, row in df_users.iterrows():
            uname, upass = row[0], row[1]
            if uname not in users:
                hashed_pw = bcrypt.hashpw(str(upass).encode(), bcrypt.gensalt()).decode()
                users[uname] = hashed_pw
        save_json_file(USERS_FILE, users)
        st.success("✅ Đã thêm user từ file Excel.")

    st.subheader("🔑 Reset mật khẩu user")
    reset_user = st.selectbox("Chọn user", list(users.keys()))
    if st.button("Reset mật khẩu"):
        users[reset_user] = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
        save_json_file(USERS_FILE, users)
        st.success(f"✅ Mật khẩu của {reset_user} đã reset về 123456.")

    st.subheader("🗑 Xoá user")
    delete_user = st.selectbox("Chọn user để xoá", [u for u in users if u != "admin"])
    if st.button("Xoá user"):
        users.pop(delete_user)
        save_json_file(USERS_FILE, users)
        st.success(f"✅ Đã xoá user {delete_user}.")

def huong_dan_tab():
    st.header("📖 Hướng dẫn sử dụng")
    st.markdown("""
    ✅ **Tra cứu doanh nghiệp mới thành lập**
    - Vào tab "Tra cứu", bấm **Tra cứu 5 trang mới nhất** để lấy dữ liệu.
    - Có thể xuất ra Excel hoặc xem trực tiếp trên màn hình.
    - **Hãy thêm doanh nghiệp quan tâm vào danh sách theo dõi để quản lý.**

    ✅ **Theo dõi doanh nghiệp**
    - Vào tab "Theo dõi", xem danh sách doanh nghiệp bạn đã thêm.
    - Có thể **thêm ghi chú, sửa hoặc xoá doanh nghiệp**.
    - Click vào dòng để xem thông tin chi tiết.

    ⚠️ **Lưu ý**: Danh sách doanh nghiệp mới **được cập nhật liên tục**. Hãy tra cứu và cập nhật mỗi ngày!
    """)

# ========== MAIN ==========
def main_app():
    st.sidebar.title(f"Xin chào, {st.session_state['username']}")
    pages = ["Theo dõi doanh nghiệp", "Quản lý người dùng", "Hướng dẫn"]
    if st.session_state["username"] != "admin":
        pages.remove("Quản lý người dùng")
    page = st.sidebar.radio("📂 Menu", pages)

    if page == "Theo dõi doanh nghiệp":
        theo_doi_tab()
    elif page == "Quản lý người dùng":
        quan_ly_user_tab()
    elif page == "Hướng dẫn":
        huong_dan_tab()

    if st.sidebar.button("🚪 Đăng xuất"):
        st.session_state.clear()
        st.rerun()

# ========== ENTRY ==========
if "logged_in" not in st.session_state:
    show_login()
else:
    main_app()
