import math
from datetime import datetime
from flask import Blueprint, request, jsonify
from src.utils import get_db, save_uploaded_image, encode_image

user_bp = Blueprint('user_bp', __name__)

def haversine_distance(lat1, lon1, lat2, lon2):
    # Radius of earth in kilometers
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@user_bp.route('/allCoordinates', methods=['GET'])
def all_coordinates():
    db = get_db()
    rows = db.execute("SELECT id, latitude as lat, longitude as lng, name FROM hospitals").fetchall()
    db.close()
    return jsonify([dict(row) for row in rows])

@user_bp.route('/filterCoordinate', methods=['GET'])
def filter_coordinate():
    lat = float(request.args.get('lat', 23.7258))
    lon = float(request.args.get('lon', 90.3976))
    radius = float(request.args.get('radiusDistance', 400))
    has_ward = request.args.get('hasWard', '0')
    has_emergency = request.args.get('hasEmergencyUnit', '0')
    is_public = request.args.get('public', '0')
    is_private = request.args.get('private', '0')

    db = get_db()
    query = "SELECT id, name, latitude as lat, longitude as lng, type, emergency_unit FROM hospitals"
    hospitals = db.execute(query).fetchall()

    filtered = []
    for h in hospitals:
        dist = haversine_distance(lat, lon, h['lat'], h['lng'])
        if dist > radius:
            continue

        if has_emergency == '1' and h['emergency_unit'] != 1:
            continue

        if is_public == '1' and is_private == '0' and h['type'].lower() != 'public':
            continue
        if is_private == '1' and is_public == '0' and h['type'].lower() != 'private':
            continue

        if has_ward == '1':
            w_count = db.execute("SELECT COUNT(*) as cnt FROM ward WHERE belong = ?", (h['id'],)).fetchone()['cnt']
            if w_count == 0:
                continue

        filtered.append({
            'id': h['id'],
            'lat': h['lat'],
            'lng': h['lng'],
            'name': h['name'],
            'distance': round(dist, 2)
        })

    db.close()
    return jsonify(filtered)

@user_bp.route('/search', methods=['GET'])
def search_hospitals():
    search = request.args.get('search', '')
    db = get_db()
    query = """
        SELECT h.id, h.name, h.type, h.emergency_unit, h.contact_no, h.image,
               COALESCE(AVG(r.rate), 0) as avg_rating
        FROM hospitals h
        LEFT JOIN review r ON h.id = r.hospital
        WHERE h.name LIKE ?
        GROUP BY h.id
    """
    rows = db.execute(query, (f"%{search}%",)).fetchall()
    db.close()

    results = []
    for r in rows:
        item = dict(r)
        item['image'] = encode_image(item['image'])
        results.append(item)
    return jsonify(results)

@user_bp.route('/searchEnhanced', methods=['GET'])
def search_enhanced():
    search = request.args.get('search', '')
    db = get_db()
    query = "SELECT id, name, type, emergency_unit, contact_no, image FROM hospitals WHERE name LIKE ?"
    hospitals = db.execute(query, (f"%{search}%",)).fetchall()

    results = []
    for h in hospitals:
        hid = h['id']
        avg_rate = db.execute("SELECT COALESCE(AVG(rate), 0) as avg FROM review WHERE hospital = ?", (hid,)).fetchone()['avg']
        ward_cnt = db.execute("SELECT COUNT(*) as cnt FROM ward WHERE belong = ?", (hid,)).fetchone()['cnt']
        doc_cnt = db.execute("SELECT COUNT(*) as cnt FROM doctors WHERE belong = ?", (hid,)).fetchone()['cnt']
        test_cnt = db.execute("SELECT COUNT(*) as cnt FROM test WHERE own = ?", (hid,)).fetchone()['cnt']
        rev_cnt = db.execute("SELECT COUNT(*) as cnt FROM review WHERE hospital = ?", (hid,)).fetchone()['cnt']

        results.append({
            'id': hid,
            'name': h['name'],
            'type': h['type'],
            'emergency': h['emergency_unit'],
            'contact': h['contact_no'],
            'image': encode_image(h['image']),
            'rating': round(float(avg_rate), 1),
            'ward_count': ward_cnt,
            'doctor_count': doc_cnt,
            'test_count': test_cnt,
            'review_count': rev_cnt
        })

    db.close()
    return jsonify(results)

@user_bp.route('/profile', methods=['GET'])
def get_profile():
    user_id = request.args.get('id')
    if not user_id:
        return jsonify({'error': 'Missing id'}), 400

    db = get_db()
    user = db.execute("SELECT * FROM \"user\" WHERE id = ?", (user_id,)).fetchone()
    db.close()

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user['id'],
        'first_name': user['first_name'],
        'last_name': user['last_name'],
        'blood_group': user['blood_group'],
        'phone': user['phone_number'],
        'phone_number': user['phone_number'],
        'dob': user['dob'],
        'picture': encode_image(user['picture'])
    })

@user_bp.route('/updateProfile', methods=['POST'])
def update_profile():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    user_id = data.get('id')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    dob = data.get('dob')
    blood_group = data.get('blood_group')
    phone_number = data.get('phone_number') or data.get('phone')

    if not user_id:
        return jsonify({'error': 'User id required'}), 400

    db = get_db()
    curr = db.execute("SELECT picture FROM \"user\" WHERE id = ?", (user_id,)).fetchone()
    if not curr:
        db.close()
        return jsonify({'error': 'User not found'}), 404

    picture_path = curr['picture']
    if 'profile_picture' in request.files and request.files['profile_picture'].filename:
        file = request.files['profile_picture']
        picture_path = save_uploaded_image(file, 'users', old_path=picture_path)
    elif data.get('profile_picture') and str(data.get('profile_picture')).startswith('data:'):
        picture_path = save_uploaded_image(data.get('profile_picture'), 'users', old_path=picture_path)

    db.execute("""
        UPDATE "user"
        SET first_name = ?, last_name = ?, dob = ?, blood_group = ?, phone_number = ?, picture = ?
        WHERE id = ?
    """, (first_name, last_name, dob, blood_group, phone_number, picture_path, user_id))
    db.commit()
    db.close()

    return jsonify({'success': True, 'picture': encode_image(picture_path)})

@user_bp.route('/getIdentity', methods=['GET'])
def get_identity():
    hos_id = request.args.get('id')
    db = get_db()
    h = db.execute("SELECT * FROM hospitals WHERE id = ?", (hos_id,)).fetchone()
    if not h:
        db.close()
        return jsonify({'error': 'Hospital not found'}), 404

    avg_rate = db.execute("SELECT COALESCE(AVG(rate), 0) as avg FROM review WHERE hospital = ?", (hos_id,)).fetchone()['avg']
    db.close()

    return jsonify({
        'id': h['id'],
        'name': h['name'],
        'type': h['type'],
        'emergency': h['emergency_unit'],
        'contact': h['contact_no'],
        'image': encode_image(h['image']),
        'rate': round(float(avg_rate), 1),
        'avg_rate': round(float(avg_rate), 1)
    })

@user_bp.route('/getRate', methods=['GET'])
def get_rate():
    hos_id = request.args.get('hos_id')
    my_id = request.args.get('my_id')
    db = get_db()

    avg_rate = db.execute("SELECT COALESCE(AVG(rate), 0) as avg FROM review WHERE hospital = ?", (hos_id,)).fetchone()['avg']
    my_rate = 0
    if my_id and hos_id:
        try:
            r = db.execute("SELECT rate FROM review WHERE hospital = ? AND user = ?", (int(hos_id), int(my_id))).fetchone()
            if r:
                my_rate = r['rate']
        except ValueError:
            pass

    db.close()
    return jsonify({
        'rate': round(float(avg_rate), 1),
        'my_rate': my_rate
    })

@user_bp.route('/getContact', methods=['GET'])
def get_contact():
    hos_id = request.args.get('id')
    db = get_db()
    h = db.execute("SELECT contact_no FROM hospitals WHERE id = ?", (hos_id,)).fetchone()
    db.close()
    return jsonify({'contact_no': h['contact_no'] if h else ''})

@user_bp.route('/getWard', methods=['GET'])
def get_ward():
    hos_id = request.args.get('id')
    db = get_db()
    rows = db.execute("SELECT id, ward_type, about, cost_perday, capacity, occupied FROM ward WHERE belong = ?", (hos_id,)).fetchall()
    db.close()

    res = []
    for r in rows:
        res.append({
            'id': r['id'],
            'ward_type': r['ward_type'],
            'type': r['ward_type'],
            'about': r['about'],
            'cost': r['cost_perday'],
            'cost_perday': r['cost_perday'],
            'capacity': r['capacity'],
            'occupied': r['occupied']
        })
    return jsonify(res)

@user_bp.route('/getTest', methods=['GET'])
def get_test():
    hos_id = request.args.get('id')
    db = get_db()
    rows = db.execute("SELECT name, description, cost FROM test WHERE own = ?", (hos_id,)).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@user_bp.route('/getSpecialty', methods=['GET'])
def get_specialty():
    hos_id = request.args.get('id')
    db = get_db()
    query = """
        SELECT d.id, d.first_name, d.last_name, d.about, d.picture, s.specialty_name as specialty
        FROM doctors d
        JOIN specialties s ON d.speciality = s.id
        WHERE d.belong = ?
    """
    rows = db.execute(query, (hos_id,)).fetchall()
    db.close()

    res = []
    for r in rows:
        item = dict(r)
        item['picture'] = encode_image(item['picture'])
        res.append(item)
    return jsonify(res)

@user_bp.route('/getReview', methods=['GET'])
def get_review():
    hos_id = request.args.get('id')
    db = get_db()
    query = """
        SELECT r.user as user_id, u.first_name, u.last_name, u.picture,
               r.review, r.rate, r.date
        FROM review r
        JOIN "user" u ON r.user = u.id
        WHERE r.hospital = ?
        ORDER BY r.date DESC
    """
    rows = db.execute(query, (hos_id,)).fetchall()
    db.close()

    res = []
    for r in rows:
        item = dict(r)
        item['picture'] = encode_image(item['picture'])
        res.append(item)
    return jsonify(res)

@user_bp.route('/addReview', methods=['POST'])
def add_review():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    user_id = data.get('user') or data.get('my_id')
    hos_id = data.get('hospital') or data.get('hos_id')
    review_text = data.get('review', '')
    rate = data.get('rate', 5)
    date_str = data.get('date') or datetime.now().strftime('%Y-%m-%d')

    if not user_id or not hos_id:
        return jsonify({'error': 'Missing user or hospital id'}), 400

    db = get_db()
    try:
        user_id_int = int(user_id)
        hos_id_int = int(hos_id)
        rate_int = int(rate)
    except ValueError:
        db.close()
        return jsonify({'error': 'Invalid format'}), 400

    db.execute("""
        INSERT INTO review (user, hospital, review, date, rate)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user, hospital) DO UPDATE SET
            review = excluded.review,
            date = excluded.date,
            rate = excluded.rate
    """, (user_id_int, hos_id_int, review_text, date_str, rate_int))
    db.commit()
    db.close()

    return jsonify({'success': True})

@user_bp.route('/updateReview', methods=['POST'])
def update_review():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    my_id = data.get('my_id') or data.get('user')
    hos_id = data.get('hos_id') or data.get('hospital')
    review_text = data.get('review', '')
    rate = data.get('rate', 5)
    date_str = datetime.now().strftime('%Y-%m-%d')

    db = get_db()
    try:
        my_id_int = int(my_id)
        hos_id_int = int(hos_id)
        rate_int = int(rate)
    except ValueError:
        db.close()
        return jsonify({'error': 'Invalid format'}), 400

    db.execute("""
        UPDATE review
        SET review = ?, rate = ?, date = ?
        WHERE user = ? AND hospital = ?
    """, (review_text, rate_int, date_str, my_id_int, hos_id_int))
    db.commit()
    db.close()

    return jsonify({'success': True})

@user_bp.route('/deleteReview', methods=['GET'])
def delete_review():
    hos_id = request.args.get('hos_id')
    my_id = request.args.get('my_id')

    if not hos_id or not my_id:
        return jsonify({'error': 'Missing parameters'}), 400

    try:
        hos_id_int = int(hos_id)
        my_id_int = int(my_id)
    except ValueError:
        return jsonify({'error': 'Invalid format'}), 400

    db = get_db()
    db.execute("DELETE FROM review WHERE user = ? AND hospital = ?", (my_id_int, hos_id_int))
    db.commit()
    db.close()

    return jsonify({'success': True})

@user_bp.route('/loadBHospital', methods=['GET'])
def load_b_hospital():
    db = get_db()
    query = """
        SELECT DISTINCT h.id, h.latitude as lat, h.longitude as lng, h.name
        FROM hospitals h
        JOIN blood_requests br ON h.id = br.belong
    """
    rows = db.execute(query).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@user_bp.route('/loadBHospitalByFilter', methods=['GET'])
def load_b_hospital_by_filter():
    my_id = request.args.get('my_id')
    db = get_db()

    user = db.execute("SELECT blood_group FROM \"user\" WHERE id = ?", (my_id,)).fetchone()
    if not user:
        db.close()
        return jsonify([])

    blood_group = user['blood_group']
    query = """
        SELECT DISTINCT h.id, h.latitude as lat, h.longitude as lng, h.name
        FROM hospitals h
        JOIN blood_requests br ON h.id = br.belong
        WHERE br.blood_group = ?
    """
    rows = db.execute(query, (blood_group,)).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@user_bp.route('/getRequest', methods=['GET'])
def get_request():
    hos_id = request.args.get('hos_id')
    db = get_db()
    query = """
        SELECT br.*, h.name as hospital_name
        FROM blood_requests br
        JOIN hospitals h ON br.belong = h.id
        WHERE br.belong = ?
        ORDER BY br.id DESC
    """
    rows = db.execute(query, (hos_id,)).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@user_bp.route('/getRequestByFilter', methods=['GET'])
def get_request_by_filter():
    hos_id = request.args.get('hos_id')
    my_id = request.args.get('my_id')

    db = get_db()
    user = db.execute("SELECT blood_group FROM \"user\" WHERE id = ?", (my_id,)).fetchone()
    if not user:
        db.close()
        return jsonify([])

    query = """
        SELECT br.*, h.name as hospital_name
        FROM blood_requests br
        JOIN hospitals h ON br.belong = h.id
        WHERE br.belong = ? AND br.blood_group = ?
        ORDER BY br.id DESC
    """
    rows = db.execute(query, (hos_id, user['blood_group'])).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@user_bp.route('/interested', methods=['GET'])
def toggle_interested():
    req_id = request.args.get('req_id')
    my_id = request.args.get('my_id')

    if not req_id or not my_id:
        return jsonify({'error': 'Missing parameters'}), 400

    db = get_db()
    existing = db.execute("SELECT * FROM interested WHERE request_id = ? AND user_id = ?", (req_id, my_id)).fetchone()

    if existing:
        db.execute("DELETE FROM interested WHERE request_id = ? AND user_id = ?", (req_id, my_id))
        status = "removed"
    else:
        db.execute("INSERT INTO interested (request_id, user_id) VALUES (?, ?)", (req_id, my_id))
        status = "added"

    db.commit()
    db.close()
    return jsonify({'status': status})

@user_bp.route('/checkInterested', methods=['GET'])
def check_interested():
    req_id = request.args.get('req_id')
    my_id = request.args.get('my_id')

    db = get_db()
    r = db.execute("SELECT 1 FROM interested WHERE request_id = ? AND user_id = ?", (req_id, my_id)).fetchone()
    db.close()

    return jsonify({'interested': bool(r)})

@user_bp.route('/getMyInterests', methods=['GET'])
def get_my_interests():
    my_id = request.args.get('my_id')
    db = get_db()
    rows = db.execute("SELECT request_id FROM interested WHERE user_id = ?", (my_id,)).fetchall()
    db.close()
    return jsonify([r['request_id'] for r in rows])
