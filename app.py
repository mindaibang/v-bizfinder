import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import bcrypt
import json
import os
from concurrent.futures import ThreadPoolExecutor

# ==============================
# CONFIG
BASE_URL = "https://hsctvn.com"
PROVINCES = {
    "Hà Nội": "ha-noi", "Hồ Chí Minh": "ho-chi-minh", "Đà Nẵng": "da-nang",
    "Bình Dương": "binh-duong", "Bắc Ninh": "bac-ninh", "Hải Phòng": "hai-phong"
    # ... thêm các tỉnh khác như app gốc
}
USERS_FILE = "users.json"
WATCHLIST_FILE = "watchlist.json"
HISTORY_FILE = "history.json"

# ==============================
# AUTHENTICATION
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # Nếu chưa có file thì tạo user admin mặc định
    admin_hash = bcrypt.hashpw("123456".encode(), bcrypt.gensalt()).decode()
    users = {"admin": admin_hash}
    save_json_file(USERS_FILE, users)
    return users

def verify_user(username, password):
    users = load_users()
    if username in users:
        hashed_pw = users[username].encode("utf-8")
        return bcrypt.checkpw(password.encode("utf-8"), hashed_pw)
    return False

# ==============================
# WATCHLIST & HISTORY
def load_json_file(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json_file(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==============================
# FETCH DATA
def fetch_announcements(month, year, province_slug):
    url = f"{BASE_URL}/thang-{month}/{year}-{province_slug}"
    rows = []
    try:
        resp = requests.get(url, timeout=10, verify=False)
        soup = BeautifulSoup(resp.text, "html.parser")
        for li in soup.find_all("li"):
            h3 = li.find("h3")
            if not h3:
                continue
            a = h3.find("a")
            name = a.get_text(strip=True)
            href = a["href"]
            link = href if href.startswith("http") else BASE_URL + "/" + href.lstrip("/")
            div = li.find("div")
            if div and "Mã số thuế:" in div.text:
                addr, tax = div.get_text(" ", strip=True).split("Mã số thuế:", 1)
                rows.append({
                    "Tên doanh nghiệp": name,
                    "Mã số thuế": tax.strip(),
                    "Địa chỉ": addr.replace("Địa chỉ:", "").strip(),
                    "Link": link
                })
    except Exception as e:
        st.error(f"Lỗi khi tải dữ liệu: {e}")
    return pd.DataFrame(rows)

def fetch_detail(link):
    try:
        resp = requests.get(link, timeout=10, verify=False)
        soup = BeautifulSoup(resp.text, "html.parser")
        content_lines = []
        h1 = soup.find("h1")
        if h1:
            content_lines.append(f"**Tên doanh nghiệp:** {h1.get_text(strip=True)}")
        for li in soup.find_all("li"):
            text = li.get_text(" ", strip=True)
            icon = li.find("i")
            if not icon:
                continue
            cls = icon.get("class", [])
            if "fa-hashtag" in cls:
                content_lines.append(f"**Mã số thuế:** {text.replace('Mã số thuế:', '').strip()}")
            elif "fa-map-marker" in cls:
                content_lines.append(f"**Địa chỉ thuế:** {text.replace('Địa chỉ thuế:', '').strip()}")
            elif "fa-user-o" in cls:
                a = li.find("a")
                if a:
                    content_lines.append(f"**Đại diện pháp luật:** {a.get_text(strip=True)}")
            elif "fa-phone" in cls:
                content_lines.append(f"**Điện thoại:** {text.replace('Điện thoại:', '').strip()}")
            elif "fa-calendar" in cls:
                content_lines.append(f"**Ngày cấp:** {text.replace('Ngày cấp:', '').strip()}")
            elif "fa-anchor" in cls:
                content_lines.append(f"**Ngành nghề chính:** {text.replace('Ngành nghề chính:', '').strip()}")
        return "\n\n".join(content_lines)
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
            st.experimental_rerun()
        else:
            st.error("❌ Sai tên đăng nhập hoặc mật khẩu")

def tra_cuu_tab():
    st.header("📊 Tra cứu doanh nghiệp")
    start_month = st.selectbox("Từ tháng", [f"{i:02d}" for i in range(1, 13)], key="start_month")
    start_year = st.selectbox("Từ năm", [str(y) for y in range(2020, 2031)], key="start_year")
    end_month = st.selectbox("Đến tháng", [f"{i:02d}" for i in range(1, 13)], key="end_month")
    end_year = st.selectbox("Đến năm", [str(y) for y in range(2020, 2031)], key="end_year")

    provinces = st.multiselect("Chọn tỉnh/TP", list(PROVINCES.keys()), help="Chỉ chọn tối đa 2 tỉnh")
    if len(provinces) > 2:
        st.warning("⚠️ Chỉ chọn tối đa 2 tỉnh")

    thread_count = st.slider("Số luồng xử lý", 1, 10, 5)

    if st.button("🔍 Tra cứu"):
        if not provinces:
            st.warning("⚠️ Vui lòng chọn ít nhất 1 tỉnh")
        else:
            results = []
            with ThreadPoolExecutor(max_workers=thread_count) as executor:
                futures = [
                    executor.submit(fetch_announcements, start_month, start_year, PROVINCES[p])
                    for p in provinces
                ]
                for f in futures:
                    df = f.result()
                    if not df.empty:
                        results.append(df)

            if results:
                final_df = pd.concat(results, ignore_index=True)
                st.session_state["search_results"] = final_df
                st.success(f"✅ Đã tìm thấy {len(final_df)} doanh nghiệp")
                st.dataframe(final_df, use_container_width=True)

                selected = st.selectbox("🔗 Chọn doanh nghiệp để xem chi tiết", final_df["Tên doanh nghiệp"])
                selected_row = final_df[final_df["Tên doanh nghiệp"] == selected].iloc[0]
                detail = fetch_detail(selected_row["Link"])
                st.markdown(detail)

                if st.button("➕ Thêm vào danh sách theo dõi"):
                    watchlist = load_json_file(WATCHLIST_FILE)
                    if any(item["Mã số thuế"] == selected_row["Mã số thuế"] for item in watchlist):
                        st.info("Doanh nghiệp đã có trong danh sách theo dõi")
                    else:
                        watchlist.append(selected_row.to_dict())
                        save_json_file(WATCHLIST_FILE, watchlist)
                        st.success("✅ Đã thêm vào danh sách theo dõi")

                history = load_json_file(HISTORY_FILE)
                entry = {"from": (start_month, start_year), "to": (end_month, end_year), "provinces": provinces}
                history.insert(0, entry)
                save_json_file(HISTORY_FILE, history)

                st.download_button("💾 Tải Excel", final_df.to_csv(index=False).encode("utf-8"), "tra_cuu.csv")
            else:
                st.info("❌ Không tìm thấy doanh nghiệp")

    # Lịch sử tra cứu
    history = load_json_file(HISTORY_FILE)
    if history:
        st.markdown("### 📖 Lịch sử tra cứu")
        for i, entry in enumerate(history[:5]):
            st.write(f"{i+1}. {entry['from'][0]}/{entry['from'][1]} → {entry['to'][0]}/{entry['to'][1]} - {', '.join(entry['provinces'])}")

def theo_doi_tab():
    st.header("👁️ Theo dõi doanh nghiệp")
    watchlist = load_json_file(WATCHLIST_FILE)

    if watchlist:
        df_watch = pd.DataFrame(watchlist)
        selected = st.selectbox("🔗 Chọn doanh nghiệp để xem chi tiết", df_watch["Tên doanh nghiệp"])
        selected_row = df_watch[df_watch["Tên doanh nghiệp"] == selected].iloc[0]
        detail = fetch_detail(selected_row["Link"])
        st.markdown(detail)

        note = st.text_area("📝 Ghi chú", value=selected_row.get("Ghi chú", ""))
        if st.button("💾 Lưu ghi chú"):
            for i, item in enumerate(watchlist):
                if item["Mã số thuế"] == selected_row["Mã số thuế"]:
                    watchlist[i]["Ghi chú"] = note
            save_json_file(WATCHLIST_FILE, watchlist)
            st.success("✅ Đã lưu ghi chú")

        if st.button("🗑️ Xoá doanh nghiệp này"):
            watchlist = [item for item in watchlist if item["Mã số thuế"] != selected_row["Mã số thuế"]]
            save_json_file(WATCHLIST_FILE, watchlist)
            st.success("✅ Đã xoá khỏi danh sách")
            st.experimental_rerun()

        st.download_button("💾 Tải Excel", df_watch.to_csv(index=False).encode("utf-8"), "theo_doi.csv")
    else:
        st.info("📭 Danh sách theo dõi trống")

def quan_ly_user_tab():
    st.header("👑 Quản lý người dùng (Admin)")
    users = load_users()

    # Hiển thị danh sách user
    st.subheader("📋 Danh sách người dùng")
    df_users = pd.DataFrame({"Username": list(users.keys())})
    st.dataframe(df_users)

    # Thêm user
    st.subheader("➕ Thêm người dùng mới")
    new_user = st.text_input("Tên user mới")
    new_pass = st.text_input("Mật khẩu", type="password")
    if st.button("✅ Thêm user"):
        if new_user and new_pass:
            if new_user in users:
                st.warning("⚠️ User đã tồn tại")
            else:
                hashed_pw = bcrypt.hashpw(new_pass.encode(), bcrypt.gensalt()).decode()
                users[new_user] = hashed_pw
                save_json_file(USERS_FILE, users)
                st.success(f"🎉 Đã thêm user: {new_user}")
                st.experimental_rerun()

    # Xoá user
    st.subheader("🗑️ Xoá người dùng")
    user_to_delete = st.selectbox("Chọn user để xoá", [u for u in users if u != "admin"])
    if st.button("❌ Xoá user"):
        del users[user_to_delete]
        save_json_file(USERS_FILE, users)
        st.success(f"✅ Đã xoá user: {user_to_delete}")
        st.experimental_rerun()

# ==============================
# MAIN APP
def main_app():
    st.sidebar.title(f"Xin chào, {st.session_state['username']}")
    menu_items = ["Tra cứu doanh nghiệp", "Theo dõi doanh nghiệp"]
    if st.session_state["username"] == "admin":
        menu_items.append("Quản lý người dùng (Admin)")

    page = st.sidebar.radio("📂 Menu", menu_items)

    if page == "Tra cứu doanh nghiệp":
        tra_cuu_tab()
    elif page == "Theo dõi doanh nghiệp":
        theo_doi_tab()
    elif page == "Quản lý người dùng (Admin)":
        quan_ly_user_tab()

    if st.sidebar.button("🚪 Đăng xuất"):
        st.session_state.clear()
        st.experimental_rerun()

# ==============================
# ENTRY POINT
if "logged_in" not in st.session_state:
    show_login()
else:
    main_app()
