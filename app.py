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
def fetch_new_companies():
    """
    Crawl danh sách DN mới nhất
    """
    rows = []
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    try:
        url = f"{BASE_URL}/tra-cuu-ma-so-thue-doanh-nghiep-moi-thanh-lap"
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        listings = soup.select("div.tax-listing div[data-prefetch]")
        for div in listings:
            a_tag = div.find("a")
            addr_tag = div.find("address")
            tax_code = div.get("data-prefetch").split("-")[0].strip("/")
            if a_tag and addr_tag:
                name = a_tag.get_text(strip=True)
                link = BASE_URL + a_tag['href']
                address = addr_tag.get_text(strip=True)
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
    """
    Crawl trang chi tiết DN
    """
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

def tra_cuu_tab():
    st.header("📊 Tra cứu doanh nghiệp mới thành lập")
    st.caption("*(Tác giả: Ngô Thị Thơm - VietinBank CN Bảo Lộc - 0919026552; lync: thom.nt)*")
    st.write("Dành tặng riêng cho các VietinBanker")

    if st.button("🔍 Tra cứu DN mới"):
        st.info("⏳ Đang tải dữ liệu...")
        df = fetch_new_companies()
        if df.empty:
            st.warning("⚠️ Không tìm thấy dữ liệu.")
        else:
            df.index += 1  # STT từ 1
            st.session_state["search_results"] = df
            st.success(f"✅ Đã tìm thấy {len(df)} doanh nghiệp mới.")
            st.dataframe(df[["Tên doanh nghiệp", "Mã số thuế", "Địa chỉ"]], use_container_width=True)

            selected_idx = st.number_input("Nhập STT DN để thao tác", min_value=1, max_value=len(df), step=1)
            selected_row = df.iloc[selected_idx - 1]

            col1, col2 = st.columns(2)
            with col1:
                if st.button("📄 Xem chi tiết"):
                    details = fetch_company_details(selected_row["Link"])
                    with st.expander(f"📄 Chi tiết: {selected_row['Tên doanh nghiệp']}", expanded=True):
                        for k, v in details.items():
                            st.markdown(f"**{k}**: {v}")
            with col2:
                if st.button("⭐ Thêm vào theo dõi"):
                    watchlist_file = get_watchlist_file(st.session_state["username"])
                    watchlist = load_json_file(watchlist_file)
                    if any(w['Link'] == selected_row["Link"] for w in watchlist):
                        st.info("✅ DN đã có trong danh sách theo dõi.")
                    else:
                        watchlist.append(selected_row.to_dict())
                        save_json_file(watchlist_file, watchlist)
                        st.success("✅ Đã thêm vào danh sách theo dõi.")

def theo_doi_tab():
    st.header("👁️ Theo dõi doanh nghiệp")
    watchlist_file = get_watchlist_file(st.session_state["username"])
    watchlist = load_json_file(watchlist_file)

    if watchlist:
        df = pd.DataFrame(watchlist)
        df.index += 1
        st.dataframe(df[["Tên doanh nghiệp", "Mã số thuế", "Địa chỉ", "Ghi chú"]], use_container_width=True)

        selected_idx = st.number_input("Nhập STT DN để thao tác", min_value=1, max_value=len(df), step=1)
        selected_row = df.iloc[selected_idx - 1]

        st.text_area("📝 Ghi chú", value=selected_row.get("Ghi chú", ""), key=f"note_{selected_idx}", height=100)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("💾 Lưu ghi chú"):
                watchlist[selected_idx - 1]["Ghi chú"] = st.session_state[f"note_{selected_idx}"]
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
            if st.button("🗑 Xoá DN"):
                watchlist.pop(selected_idx - 1)
                save_json_file(watchlist_file, watchlist)
                st.success("✅ Đã xoá khỏi danh sách.")
                st.rerun()
        with col4:
            if st.button("📄 Xem chi tiết"):
                details = fetch_company_details(selected_row["Link"])
                with st.expander(f"📄 Chi tiết: {selected_row['Tên doanh nghiệp']}", expanded=True):
                    for k, v in details.items():
                        st.markdown(f"**{k}**: {v}")
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
    bulk_users = st.text_area("Nhập danh sách (mỗi dòng: username,password)")
    if st.button("Thêm theo lô"):
        for line in bulk_users.strip().split("\n"):
            uname, pwd = line.strip().split(",")
            if uname not in users:
                hashed_pw = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
                users[uname] = hashed_pw
        save_json_file(USERS_FILE, users)
        st.success("✅ Đã thêm user theo lô.")

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

def huong_dan_tab():
    st.header("📖 Hướng dẫn sử dụng")
    st.markdown("""
    ✅ **Lưu ý**:
    - Danh sách DN mới được cập nhật liên tục.  
    - Bạn nên kiểm tra hàng ngày và thêm DN quan trọng vào danh sách theo dõi.
    - Bạn có thể xuất danh sách ra Excel hoặc xem trực tiếp trên màn hình.  

    🔒 **Admin** quản lý user, còn user thường chỉ quản lý dữ liệu của riêng mình.
    """)

# ========== MAIN ==========
def main_app():
    st.sidebar.title(f"Xin chào, {st.session_state['username']}")
    pages = ["Tra cứu DN mới", "Theo dõi doanh nghiệp", "Hướng dẫn"]
    if st.session_state["username"] == "admin":
        pages.append("Quản lý người dùng")
    page = st.sidebar.radio("📂 Menu", pages)

    if page == "Tra cứu DN mới":
        tra_cuu_tab()
    elif page == "Theo dõi doanh nghiệp":
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
