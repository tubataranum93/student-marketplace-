import streamlit as st
from utils.db import get_supabase
from utils.auth import (
    generate_otp,
    login_user,
    logout,
    require_login,
    signup_user,
    valid_university_email,
)
from utils.storage import upload_listing_image

st.set_page_config(page_title="MU Student Marketplace", page_icon="🎓", layout="wide")

CATEGORIES = ["Textbooks", "Calculators", "Notes", "Stationery", "Lab coats", "Other"]
CONDITIONS = ["New", "Like New", "Good", "Fair", "Used"]
YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year", "5th Year", "PhD", "Other"]


def sb():
    return get_supabase()


def toast_success(msg: str):
    st.success(msg)


def create_notification(user_id: str, title: str, body: str):
    try:
        sb().table("notifications").insert({"user_id": user_id, "title": title, "body": body}).execute()
    except Exception:
        pass


def auth_page():
    st.title("🎓 MU Student Marketplace")
    st.caption("Verified Mahindra University marketplace for books, lab coats, calculators, notes, and stationery.")

    login_tab, signup_tab = st.tabs(["Login", "Sign up"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("University email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
        if submitted:
            user = login_user(email, password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error("Invalid email or password.")

    with signup_tab:
        if "pending_signup" not in st.session_state:
            with st.form("signup_form"):
                name = st.text_input("Full name")
                email = st.text_input("Mahindra University email")
                course = st.text_input("Course / Program", placeholder="B.Tech CSE, MBA, Design, etc.")
                year = st.selectbox("Year", YEARS)
                password = st.text_input("Create password", type="password")
                confirm = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("Send simulated verification code")
            if submitted:
                if not all([name, email, course, password, confirm]):
                    st.error("Please fill all fields.")
                elif not valid_university_email(email):
                    st.error("Use your @mahindrauniversity.edu.in email address.")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                else:
                    st.session_state.pending_signup = {
                        "name": name,
                        "email": email.lower().strip(),
                        "password": password,
                        "course": course,
                        "year": year,
                    }
                    st.session_state.otp = generate_otp()
                    st.info(f"Simulated verification code: {st.session_state.otp}")
        else:
            st.info(f"Simulated verification code: {st.session_state.otp}")
            code = st.text_input("Enter verification code")
            col1, col2 = st.columns(2)
            if col1.button("Verify & create account", type="primary"):
                if code == st.session_state.otp:
                    data = st.session_state.pending_signup
                    err = signup_user(**data)
                    if err:
                        st.error(err)
                    else:
                        toast_success("Account created. Please login.")
                        st.session_state.pop("pending_signup", None)
                        st.session_state.pop("otp", None)
                else:
                    st.error("Incorrect verification code.")
            if col2.button("Start over"):
                st.session_state.pop("pending_signup", None)
                st.session_state.pop("otp", None)
                st.rerun()


def sidebar():
    user = st.session_state.user
    st.sidebar.title("🎓 Marketplace")
    st.sidebar.write(f"**{user['name']}**")
    st.sidebar.caption(f"{user['course']} • {user['year']}")
    pages = ["Browse", "Create listing", "My listings", "Messages", "Notifications"]
    if user.get("is_admin"):
        pages.append("Admin")
    page = st.sidebar.radio("Navigate", pages)
    if st.sidebar.button("Logout"):
        logout()
        st.rerun()
    return page


def listing_card(listing):
    seller = listing.get("profiles") or {}
    with st.container(border=True):
        cols = st.columns([1, 2, 1])
        with cols[0]:
            if listing.get("image_url"):
                st.image(listing["image_url"], use_container_width=True)
            else:
                st.write("📚")
        with cols[1]:
            st.subheader(listing["title"])
            st.caption(f"{listing['category']} • {listing['condition']} • {listing.get('course') or 'Any course'} • {listing.get('year') or 'Any year'}")
            st.write(listing.get("description") or "No description added.")
            st.caption(f"Seller: {seller.get('name', 'Student')}")
        with cols[2]:
            st.metric("Price", f"₹{float(listing['price']):.0f}")
            st.status(listing["status"].title(), expanded=False)
            if st.button("View / Chat", key=f"view_{listing['id']}"):
                st.session_state.selected_listing = listing["id"]
                st.session_state.page_override = "Listing detail"
                st.rerun()


def browse_page():
    st.header("Browse listings")
    user = st.session_state.user
    with st.expander("Search & filters", expanded=True):
        c1, c2, c3, c4 = st.columns(4)
        keyword = c1.text_input("Keyword")
        category = c2.selectbox("Category", ["All"] + CATEGORIES)
        condition = c3.selectbox("Condition", ["All"] + CONDITIONS)
        max_price = c4.number_input("Max price", min_value=0, value=10000, step=100)
        c5, c6 = st.columns(2)
        course_filter = c5.text_input("Course contains", value="")
        year_filter = c6.selectbox("Year", ["All"] + YEARS)

    query = sb().table("listings").select("*, profiles(name,email,course,year)").neq("status", "sold").order("created_at", desc=True)
    data = query.execute().data or []

    def match(x):
        text = f"{x.get('title','')} {x.get('description','')}".lower()
        return (
            (not keyword or keyword.lower() in text)
            and (category == "All" or x.get("category") == category)
            and (condition == "All" or x.get("condition") == condition)
            and float(x.get("price") or 0) <= max_price
            and (not course_filter or course_filter.lower() in (x.get("course") or "").lower())
            and (year_filter == "All" or x.get("year") == year_filter)
        )

    results = [x for x in data if match(x)]
    st.write(f"Found **{len(results)}** listing(s).")
    for listing in results:
        listing_card(listing)


def create_listing_page():
    st.header("Create listing")
    user = st.session_state.user
    with st.form("create_listing", clear_on_submit=True):
        title = st.text_input("Title")
        description = st.text_area("Description")
        c1, c2, c3 = st.columns(3)
        category = c1.selectbox("Category", CATEGORIES)
        condition = c2.selectbox("Condition", CONDITIONS)
        price = c3.number_input("Price ₹", min_value=0.0, step=10.0)
        c4, c5 = st.columns(2)
        course = c4.text_input("Relevant course", value=user.get("course", ""))
        year = c5.selectbox("Relevant year", YEARS, index=YEARS.index(user.get("year")) if user.get("year") in YEARS else 0)
        uploaded = st.file_uploader("Upload listing photo", type=["png", "jpg", "jpeg", "webp"])
        image_url_manual = st.text_input("Or paste image URL")
        submitted = st.form_submit_button("Publish listing", type="primary")

    if submitted:
        if not title:
            st.error("Title is required.")
            return
        image_url = image_url_manual.strip() or upload_listing_image(uploaded, user["id"])
        sb().table("listings").insert({
            "seller_id": user["id"],
            "title": title,
            "description": description,
            "category": category,
            "condition": condition,
            "price": price,
            "course": course,
            "year": year,
            "image_url": image_url,
        }).execute()
        toast_success("Listing published.")


def my_listings_page():
    st.header("My listings")
    user = st.session_state.user
    listings = sb().table("listings").select("*").eq("seller_id", user["id"]).order("created_at", desc=True).execute().data or []
    for item in listings:
        with st.container(border=True):
            st.subheader(item["title"])
            st.write(f"₹{float(item['price']):.0f} • {item['category']} • {item['condition']}")
            status = st.selectbox("Status", ["available", "reserved", "sold"], index=["available", "reserved", "sold"].index(item["status"]), key=f"status_{item['id']}")
            c1, c2 = st.columns(2)
            if c1.button("Update status", key=f"upd_{item['id']}"):
                sb().table("listings").update({"status": status}).eq("id", item["id"]).execute()
                toast_success("Status updated.")
                st.rerun()
            if c2.button("Delete", key=f"del_{item['id']}"):
                sb().table("listings").delete().eq("id", item["id"]).execute()
                st.warning("Listing deleted.")
                st.rerun()


def listing_detail_page():
    require_login()
    user = st.session_state.user
    listing_id = st.session_state.get("selected_listing")
    rows = sb().table("listings").select("*, profiles(name,email)").eq("id", listing_id).execute().data or []
    if not rows:
        st.error("Listing not found.")
        return
    item = rows[0]
    if st.button("← Back to browse"):
        st.session_state.pop("selected_listing", None)
        st.session_state.pop("page_override", None)
        st.rerun()
    listing_card(item)
    if item["seller_id"] == user["id"]:
        st.info("This is your listing. Buyers can message you from here.")
        return
    st.divider()
    st.subheader("Message seller")
    msgs = sb().table("messages").select("*, sender:profiles!messages_sender_id_fkey(name)").eq("listing_id", listing_id).or_(f"sender_id.eq.{user['id']},receiver_id.eq.{user['id']}").order("created_at").execute().data or []
    for m in msgs:
        name = (m.get("sender") or {}).get("name", "Student")
        st.chat_message("user" if m["sender_id"] == user["id"] else "assistant").write(f"**{name}:** {m['body']}")
    body = st.chat_input("Write a message")
    if body:
        sb().table("messages").insert({
            "listing_id": listing_id,
            "sender_id": user["id"],
            "receiver_id": item["seller_id"],
            "body": body,
        }).execute()
        create_notification(item["seller_id"], "New message", f"New message about {item['title']}")
        st.rerun()


def messages_page():
    st.header("Messages")
    user = st.session_state.user
    msgs = sb().table("messages").select("*, listings(title), sender:profiles!messages_sender_id_fkey(name), receiver:profiles!messages_receiver_id_fkey(name)").or_(f"sender_id.eq.{user['id']},receiver_id.eq.{user['id']}").order("created_at", desc=True).execute().data or []
    if not msgs:
        st.info("No messages yet.")
    for m in msgs:
        listing_title = (m.get("listings") or {}).get("title", "Listing")
        sender_name = (m.get("sender") or {}).get("name", "Student")
        with st.container(border=True):
            st.caption(listing_title)
            st.write(f"**{sender_name}:** {m['body']}")
            st.caption(m.get("created_at", ""))


def notifications_page():
    st.header("Notifications")
    user = st.session_state.user
    rows = sb().table("notifications").select("*").eq("user_id", user["id"]).order("created_at", desc=True).execute().data or []
    if not rows:
        st.info("No notifications yet.")
    for n in rows:
        with st.container(border=True):
            st.write(f"**{n['title']}**")
            st.write(n["body"])
            st.caption(n.get("created_at", ""))
            if not n.get("is_read") and st.button("Mark read", key=f"read_{n['id']}"):
                sb().table("notifications").update({"is_read": True}).eq("id", n["id"]).execute()
                st.rerun()


def admin_page():
    st.header("Admin dashboard")
    user = st.session_state.user
    if not user.get("is_admin"):
        st.error("Admins only.")
        return
    tab1, tab2 = st.tabs(["Listings", "Users"])
    with tab1:
        rows = sb().table("listings").select("*, profiles(name,email)").order("created_at", desc=True).execute().data or []
        for item in rows:
            with st.container(border=True):
                seller = item.get("profiles") or {}
                st.write(f"**{item['title']}** — ₹{float(item['price']):.0f} — {item['status']}")
                st.caption(f"Seller: {seller.get('name')} <{seller.get('email')}>")
                c1, c2 = st.columns(2)
                new_status = c1.selectbox("Set status", ["available", "reserved", "sold"], index=["available", "reserved", "sold"].index(item["status"]), key=f"admin_status_{item['id']}")
                if c1.button("Save", key=f"admin_save_{item['id']}"):
                    sb().table("listings").update({"status": new_status}).eq("id", item["id"]).execute()
                    st.rerun()
                if c2.button("Remove listing", key=f"admin_del_{item['id']}"):
                    sb().table("listings").delete().eq("id", item["id"]).execute()
                    st.rerun()
    with tab2:
        users = sb().table("profiles").select("id,name,email,course,year,is_admin,created_at").order("created_at", desc=True).execute().data or []
        for u in users:
            with st.container(border=True):
                st.write(f"**{u['name']}** — {u['email']}")
                st.caption(f"{u['course']} • {u['year']} • Admin: {u['is_admin']}")
                if u["id"] != user["id"]:
                    if st.button("Toggle admin", key=f"toggle_{u['id']}"):
                        sb().table("profiles").update({"is_admin": not u["is_admin"]}).eq("id", u["id"]).execute()
                        st.rerun()


def main():
    if "user" not in st.session_state:
        auth_page()
        return
    if st.session_state.get("page_override") == "Listing detail":
        listing_detail_page()
        return
    page = sidebar()
    if page == "Browse":
        browse_page()
    elif page == "Create listing":
        create_listing_page()
    elif page == "My listings":
        my_listings_page()
    elif page == "Messages":
        messages_page()
    elif page == "Notifications":
        notifications_page()
    elif page == "Admin":
        admin_page()


if __name__ == "__main__":
    main()
