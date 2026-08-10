import os
import sys
import shutil
import sqlite3

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import DB_PATH, UPLOAD_BASE_DIR, PROJECT_ROOT

def create_placeholder_image(path, text, color="#0d9488", text_color="#ffffff", size=(300, 300)):
    """Creates a clean SVG image and writes it if path ends with .png or .svg."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{size[0]}" height="{size[1]}" viewBox="0 0 {size[0]} {size[1]}">
  <rect width="100%" height="100%" fill="{color}"/>
  <circle cx="{size[0]//2}" cy="{size[1]//2}" r="{min(size)//3}" fill="rgba(255,255,255,0.15)"/>
  <text x="50%" y="50%" dominant-baseline="central" text-anchor="middle" fill="{text_color}" font-family="Arial, sans-serif" font-size="{min(size)//8}px" font-weight="bold">{text}</text>
</svg>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg_content)

def setup_static_images():
    img_dir = os.path.join(PROJECT_ROOT, "static", "images")
    os.makedirs(img_dir, exist_ok=True)

    create_placeholder_image(os.path.join(img_dir, "hospital.svg"), "HOSPITAL", "#0f766e", size=(100, 100))
    create_placeholder_image(os.path.join(img_dir, "pin-map.svg"), "YOU", "#2563eb", size=(80, 80))
    create_placeholder_image(os.path.join(img_dir, "blood.svg"), "BLOOD", "#dc2626", size=(80, 80))
    create_placeholder_image(os.path.join(img_dir, "blood2.svg"), "DROP", "#b91c1c", size=(100, 100))
    create_placeholder_image(os.path.join(img_dir, "profile.svg"), "USER", "#475569", size=(200, 200))

def init_db():
    print("Initializing Database...")

    # Clean uploads directory
    if os.path.exists(UPLOAD_BASE_DIR):
        shutil.rmtree(UPLOAD_BASE_DIR)

    os.makedirs(os.path.join(UPLOAD_BASE_DIR, "doctors"), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_BASE_DIR, "hospitals"), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_BASE_DIR, "users"), exist_ok=True)

    setup_static_images()

    # Remove existing DB
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception as e:
            print(f"Could not remove old db: {e}")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Schema definition
    cur.executescript("""
        DROP TABLE IF EXISTS interested;
        DROP TABLE IF EXISTS review;
        DROP TABLE IF EXISTS blood_requests;
        DROP TABLE IF EXISTS test;
        DROP TABLE IF EXISTS ward;
        DROP TABLE IF EXISTS doctors;
        DROP TABLE IF EXISTS "user";
        DROP TABLE IF EXISTS specialties;
        DROP TABLE IF EXISTS hospitals;

        CREATE TABLE hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            latitude REAL,
            longitude REAL,
            type TEXT NOT NULL,
            emergency_unit INTEGER NOT NULL,
            image TEXT,
            contact_no TEXT NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE specialties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            specialty_name TEXT NOT NULL
        );

        CREATE TABLE doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            about TEXT NOT NULL,
            speciality INTEGER NOT NULL,
            picture TEXT,
            belong INTEGER NOT NULL,
            FOREIGN KEY (speciality) REFERENCES specialties(id),
            FOREIGN KEY (belong) REFERENCES hospitals(id) ON DELETE CASCADE
        );

        CREATE TABLE "user" (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            phone_number TEXT NOT NULL,
            dob TEXT NOT NULL,
            picture TEXT,
            password TEXT NOT NULL
        );

        CREATE TABLE ward (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ward_type TEXT NOT NULL,
            about TEXT NOT NULL,
            cost_perday INTEGER NOT NULL,
            belong INTEGER NOT NULL,
            capacity INTEGER NOT NULL,
            occupied INTEGER NOT NULL,
            FOREIGN KEY (belong) REFERENCES hospitals(id) ON DELETE CASCADE
        );

        CREATE TABLE test (
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            cost INTEGER NOT NULL,
            own INTEGER NOT NULL,
            PRIMARY KEY (name, own),
            FOREIGN KEY (own) REFERENCES hospitals(id) ON DELETE CASCADE
        );

        CREATE TABLE blood_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            belong INTEGER NOT NULL,
            blood_group TEXT NOT NULL,
            description TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY (belong) REFERENCES hospitals(id) ON DELETE CASCADE
        );

        CREATE TABLE review (
            user INTEGER NOT NULL,
            hospital INTEGER NOT NULL,
            review TEXT NOT NULL,
            date TEXT NOT NULL,
            rate INTEGER NOT NULL,
            PRIMARY KEY (user, hospital),
            FOREIGN KEY (hospital) REFERENCES hospitals(id) ON DELETE CASCADE,
            FOREIGN KEY (user) REFERENCES "user"(id) ON DELETE CASCADE
        );

        CREATE TABLE interested (
            request_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (request_id, user_id),
            FOREIGN KEY (request_id) REFERENCES blood_requests(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE
        );
    """)

    conn.commit()

    tables = ["hospitals", "specialties", "doctors", "user", "ward", "test", "blood_requests", "review", "interested"]
    for t in tables:
        count = cur.execute(f"SELECT COUNT(*) FROM \"{t}\"" if t == "user" else f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"Table '{t}': {count} rows")

    conn.close()
    print("Database initialization complete!")

if __name__ == '__main__':
    init_db()
