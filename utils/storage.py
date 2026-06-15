import mimetypes
import time
import streamlit as st
from utils.db import get_supabase


def upload_listing_image(uploaded_file, user_id: str) -> str | None:
    if uploaded_file is None:
        return None
    sb = get_supabase()
    content_type = uploaded_file.type or mimetypes.guess_type(uploaded_file.name)[0] or "image/jpeg"
    ext = uploaded_file.name.split(".")[-1].lower() if "." in uploaded_file.name else "jpg"
    path = f"{user_id}/{int(time.time())}.{ext}"
    try:
        sb.storage.from_("listing-images").upload(
            path,
            uploaded_file.getvalue(),
            {"content-type": content_type, "upsert": "true"},
        )
        return sb.storage.from_("listing-images").get_public_url(path)
    except Exception as exc:
        st.warning(f"Image upload failed. You can use an image URL instead. Details: {exc}")
        return None
