import os
import sqlite3
import base64
import uuid
import re
from src.config import DB_PATH, UPLOAD_BASE_DIR

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        from database.init_db import init_db
        init_db()

    conn = sqlite3.connect(DB_PATH)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA foreign_keys=ON;')
    conn.row_factory = sqlite3.Row

    try:
        cur = conn.cursor()
        table_check = cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user';").fetchone()
        if not table_check:
            conn.close()
            from database.init_db import init_db
            init_db()
            conn = sqlite3.connect(DB_PATH)
            conn.execute('PRAGMA journal_mode=WAL;')
            conn.execute('PRAGMA foreign_keys=ON;')
            conn.row_factory = sqlite3.Row
    except Exception as e:
        print(f"Database check error: {e}")

    return conn

def nl2br(text):
    if not text:
        return ""
    return str(text).replace("\n", "<br>")

def encode_image(image_path):
    if not image_path:
        return "/static/images/profile.svg"
    if image_path.startswith("data:") or image_path.startswith("http"):
        return image_path
    if image_path.startswith("/"):
        return image_path
    return "/" + image_path

def number_format(value, decimals=1):
    try:
        val = float(value)
        return f"{val:.{decimals}f}"
    except (ValueError, TypeError):
        return f"{0:.{decimals}f}"

def save_uploaded_image(image, subfolder, old_path=None):
    """
    Saves an uploaded image (Werkzeug FileStorage object, base64 string, or data URI)
    into UPLOAD_BASE_DIR/subfolder with a unique UUID filename.
    Returns relative path stored in database: database/uploads/subfolder/filename
    """
    if old_path and os.path.exists(old_path) and os.path.isfile(old_path):
        try:
            os.remove(old_path)
        except Exception:
            pass

    if not image:
        return None

    target_dir = os.path.join(UPLOAD_BASE_DIR, subfolder)
    os.makedirs(target_dir, exist_ok=True)

    filename = f"{uuid.uuid4().hex}.png"
    filepath = os.path.join(target_dir, filename)

    # If image is a string (base64 or data URI)
    if isinstance(image, str):
        if image.startswith("data:"):
            # strip data:image/png;base64,
            header, data = image.split(",", 1) if "," in image else ("", image)
            file_bytes = base64.b64decode(data)
        elif len(image) > 100:  # crude base64 check
            try:
                file_bytes = base64.b64decode(image)
            except Exception:
                file_bytes = None
        else:
            # might already be a path string
            return image

        if file_bytes:
            with open(filepath, "wb") as f:
                f.write(file_bytes)
            return f"database/uploads/{subfolder}/{filename}"

    # If image is a FileStorage object
    if hasattr(image, "filename") and image.filename:
        ext = os.path.splitext(image.filename)[1].lower() or ".png"
        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(target_dir, filename)
        image.save(filepath)
        return f"database/uploads/{subfolder}/{filename}"

    return None
