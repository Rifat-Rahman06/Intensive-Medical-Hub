import os
from src.config import DB_PATH

if __name__ == '__main__':
    if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
        from database.init_db import init_db
        init_db()

    from src.app import app
    port = int(os.environ.get('PORT', 3000))
    print(f"Starting Intensive Medical Hub on http://0.0.0.0:{port}")
    print(f"User Login: http://localhost:{port}/user/login/userLogin.html")
    print(f"Admin Login: http://localhost:{port}/admin/login/adminLogin.html")
    app.run(host='0.0.0.0', port=port, debug=True)
