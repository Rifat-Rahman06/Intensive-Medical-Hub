import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'database', 'imh.db')
UPLOAD_BASE_DIR = os.path.join(PROJECT_ROOT, 'database', 'uploads')
SECRET_KEY = 'imh-dev-secret-key-change-in-production'
