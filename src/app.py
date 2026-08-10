import os
import mimetypes
from flask import Flask, request, redirect, jsonify, send_from_directory, abort
from src.config import PROJECT_ROOT, SECRET_KEY
from src.utils import get_db, save_uploaded_image
from src.routes.user import user_bp
from src.routes.admin import admin_bp

app = Flask(__name__, static_folder=None)
app.secret_key = SECRET_KEY

# Register blueprints
app.register_blueprint(user_bp, url_prefix='/server/user')
app.register_blueprint(admin_bp, url_prefix='/server/admin')

@app.before_request
def security_guard():
    path = request.path.lower()
    blocked_patterns = ['/env/', '/database/imh.db', '/database/test_data.json', '/app.py', '/.git/', '/__pycache__/']
    for pattern in blocked_patterns:
        if pattern in path or path.endswith(pattern.strip('/')):
            abort(403)

@app.route('/', methods=['GET'])
def index():
    return redirect('/user/login/userLogin.html')

@app.route('/user/login', methods=['POST'])
def user_login_post():
    username = request.form.get('username') or request.form.get('id')
    password = request.form.get('password')

    if not username or not password:
        return redirect('/user/login/userLogin.html?error=1')

    db = get_db()
    try:
        user_id = int(username)
        user = db.execute("SELECT * FROM \"user\" WHERE id = ? AND password = ?", (user_id, password)).fetchone()
    except ValueError:
        user = None
    db.close()

    if user:
        return redirect(f"/user/index.html?id={user['id']}")
    else:
        return redirect('/user/login/userLogin.html?error=1')

@app.route('/user/signup', methods=['POST'])
def user_signup_post():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    dob = data.get('dob')
    blood_group = data.get('blood_group')
    phone_number = data.get('phone_number') or data.get('phone')
    password = data.get('password', '1234')

    picture_path = None
    if 'profile_picture' in request.files and request.files['profile_picture'].filename:
        picture_path = save_uploaded_image(request.files['profile_picture'], 'users')
    elif data.get('profile_picture') and str(data.get('profile_picture')).startswith('data:'):
        picture_path = save_uploaded_image(data.get('profile_picture'), 'users')

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO "user" (first_name, last_name, blood_group, phone_number, dob, picture, password)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (first_name, last_name, blood_group, phone_number, dob, picture_path, password))
    user_id = cur.lastrowid
    db.commit()
    db.close()

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'lastInsertedID': user_id, 'id': user_id})

    return redirect(f"/user/index.html?id={user_id}")

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    username = request.form.get('username') or request.form.get('id')
    password = request.form.get('password')

    if not username or not password:
        return redirect('/admin/login/adminLogin.html?error=1')

    db = get_db()
    try:
        hos_id = int(username)
        hospital = db.execute("SELECT * FROM hospitals WHERE id = ? AND password = ?", (hos_id, password)).fetchone()
    except ValueError:
        hospital = None
    db.close()

    if hospital:
        return redirect(f"/admin/index.html?id={hospital['id']}")
    else:
        return redirect('/admin/login/adminLogin.html?error=1')

@app.route('/admin/signup', methods=['POST'])
def admin_signup_post():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    name = data.get('name')
    contact_no = data.get('contact_no') or data.get('hotline')
    h_type = data.get('type', 'private')
    emergency_units = int(data.get('emergency_units') or data.get('emergency_unit') or 0)
    lat = float(data.get('latitude', 23.7258))
    lng = float(data.get('longitude', 90.3976))
    password = data.get('password', '1234')

    image_path = None
    if 'image' in request.files and request.files['image'].filename:
        image_path = save_uploaded_image(request.files['image'], 'hospitals')
    elif data.get('image') and str(data.get('image')).startswith('data:'):
        image_path = save_uploaded_image(data.get('image'), 'hospitals')

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO hospitals (name, latitude, longitude, type, emergency_unit, image, contact_no, password)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, lat, lng, h_type, emergency_units, image_path, contact_no, password))
    hos_id = cur.lastrowid
    db.commit()
    db.close()

    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'lastInsertedID': hos_id, 'id': hos_id})

    return redirect(f"/admin/index.html?id={hos_id}")

@app.route('/<path:filename>', methods=['GET'])
def catch_all(filename):
    # Check PROJECT_ROOT first
    target_path = os.path.join(PROJECT_ROOT, filename)
    if os.path.exists(target_path) and os.path.isfile(target_path):
        directory = os.path.dirname(target_path)
        base = os.path.basename(target_path)
        return send_from_directory(directory, base)

    # Check templates/ directory
    template_path = os.path.join(PROJECT_ROOT, 'templates', filename)
    if os.path.exists(template_path) and os.path.isfile(template_path):
        directory = os.path.dirname(template_path)
        base = os.path.basename(template_path)
        return send_from_directory(directory, base)

    abort(404)
