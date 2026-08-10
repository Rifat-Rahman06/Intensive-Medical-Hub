from datetime import datetime
from flask import Blueprint, request, jsonify
from src.utils import get_db, save_uploaded_image, encode_image

admin_bp = Blueprint('admin_bp', __name__)

def calculate_age(dob_str):
    if not dob_str:
        return None
    try:
        dob = datetime.strptime(dob_str, '%Y-%m-%d')
        today = datetime.now()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except Exception:
        return None

@admin_bp.route('/loadProfile', methods=['GET'])
def load_profile():
    hos_id = request.args.get('id')
    db = get_db()
    h = db.execute("SELECT * FROM hospitals WHERE id = ?", (hos_id,)).fetchone()
    db.close()

    if not h:
        return jsonify({'error': 'Hospital not found'}), 404

    return jsonify({
        'id': h['id'],
        'name': h['name'],
        'contact_no': h['contact_no'],
        'type': h['type'],
        'emergency_units': h['emergency_unit'],
        'emergency_unit': h['emergency_unit'],
        'latitude': h['latitude'],
        'longitude': h['longitude'],
        'image': encode_image(h['image'])
    })

@admin_bp.route('/updateProfile', methods=['POST'])
def update_profile():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    hos_id = data.get('id')
    name = data.get('name')
    contact_no = data.get('contact_no')
    h_type = data.get('type')
    emergency_units = int(data.get('emergency_units', 0))
    lat = float(data.get('latitude', 23.7258))
    lng = float(data.get('longitude', 90.3976))

    db = get_db()
    curr = db.execute("SELECT image FROM hospitals WHERE id = ?", (hos_id,)).fetchone()
    if not curr:
        db.close()
        return jsonify({'error': 'Hospital not found'}), 404

    image_path = curr['image']
    if 'image' in request.files and request.files['image'].filename:
        image_path = save_uploaded_image(request.files['image'], 'hospitals', old_path=image_path)
    elif data.get('image') and str(data.get('image')).startswith('data:'):
        image_path = save_uploaded_image(data.get('image'), 'hospitals', old_path=image_path)

    db.execute("""
        UPDATE hospitals
        SET name = ?, contact_no = ?, type = ?, emergency_unit = ?, latitude = ?, longitude = ?, image = ?
        WHERE id = ?
    """, (name, contact_no, h_type, emergency_units, lat, lng, image_path, hos_id))
    db.commit()
    db.close()

    return jsonify({'success': True, 'image': encode_image(image_path)})

@admin_bp.route('/getIdentity', methods=['GET'])
def get_identity():
    hos_id = request.args.get('id')
    db = get_db()
    h = db.execute("SELECT id, name, type, emergency_unit, contact_no, image FROM hospitals WHERE id = ?", (hos_id,)).fetchone()
    db.close()
    if not h:
        return jsonify({'error': 'Hospital not found'}), 404

    return jsonify({
        'id': h['id'],
        'name': h['name'],
        'type': h['type'],
        'emergency': h['emergency_unit'],
        'contact': h['contact_no'],
        'image': encode_image(h['image'])
    })

@admin_bp.route('/getWard', methods=['GET'])
def get_ward():
    hos_id = request.args.get('id')
    db = get_db()
    rows = db.execute("SELECT * FROM ward WHERE belong = ?", (hos_id,)).fetchall()
    db.close()

    res = []
    for r in rows:
        res.append({
            'id': r['id'],
            'ward_type': r['ward_type'],
            'about': r['about'],
            'cost_per_day': r['cost_perday'],
            'cost_perday': r['cost_perday'],
            'capacity': r['capacity'],
            'occupied': r['occupied'],
            'available': r['occupied']
        })
    return jsonify(res)

@admin_bp.route('/getWardForm', methods=['GET'])
def get_ward_form():
    ward_id = request.args.get('id')
    db = get_db()
    r = db.execute("SELECT * FROM ward WHERE id = ?", (ward_id,)).fetchone()
    db.close()

    if not r:
        return jsonify({'error': 'Ward not found'}), 404

    return jsonify({
        'id': r['id'],
        'ward_type': r['ward_type'],
        'about': r['about'],
        'cost_per_day': r['cost_perday'],
        'cost_perday': r['cost_perday'],
        'capacity': r['capacity'],
        'occupied': r['occupied'],
        'available': r['occupied'],
        'belong': r['belong']
    })

@admin_bp.route('/addWard', methods=['POST'])
def add_ward():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    ward_type = data.get('ward_type')
    about = data.get('about')
    capacity = int(data.get('capacity', 0))
    occupied = int(data.get('available') or data.get('occupied') or 0)
    cost_per_day = int(data.get('cost_per_day') or data.get('cost_perday') or 0)
    belong = data.get('belong') or data.get('hos_id')

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO ward (ward_type, about, cost_perday, belong, capacity, occupied)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ward_type, about, cost_per_day, belong, capacity, occupied))
    ward_id = cur.lastrowid
    db.commit()
    db.close()

    return jsonify({'success': True, 'id': ward_id})

@admin_bp.route('/updateWard', methods=['POST'])
def update_ward():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    ward_id = data.get('id')
    ward_type = data.get('ward_type')
    about = data.get('about')
    capacity = int(data.get('capacity', 0))
    occupied = int(data.get('available') or data.get('occupied') or 0)
    cost_per_day = int(data.get('cost_per_day') or data.get('cost_perday') or 0)

    db = get_db()
    db.execute("""
        UPDATE ward
        SET ward_type = ?, about = ?, capacity = ?, occupied = ?, cost_perday = ?
        WHERE id = ?
    """, (ward_type, about, capacity, occupied, cost_per_day, ward_id))
    db.commit()
    db.close()

    return jsonify({'success': True})

@admin_bp.route('/deleteWard', methods=['GET'])
def delete_ward():
    ward_id = request.args.get('id')
    db = get_db()
    db.execute("DELETE FROM ward WHERE id = ?", (ward_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})

@admin_bp.route('/updateWardAvailability', methods=['GET'])
def update_ward_availability():
    ward_id = request.args.get('id')
    val = int(request.args.get('value', 0))

    db = get_db()
    w = db.execute("SELECT capacity, occupied FROM ward WHERE id = ?", (ward_id,)).fetchone()
    if w:
        new_occ = max(0, min(w['capacity'], w['occupied'] + val))
        db.execute("UPDATE ward SET occupied = ? WHERE id = ?", (new_occ, ward_id))
        db.commit()
    db.close()
    return jsonify({'success': True})

@admin_bp.route('/getDoctor', methods=['GET'])
def get_doctor():
    hos_id = request.args.get('id')
    db = get_db()
    query = """
        SELECT d.*, s.specialty_name as specialty, s.id as speciality_id
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
        item['profile_picture'] = item['picture']
        res.append(item)
    return jsonify(res)

@admin_bp.route('/getDoctorForm', methods=['GET'])
def get_doctor_form():
    doc_id = request.args.get('id')
    db = get_db()
    query = """
        SELECT d.*, s.specialty_name as specialty
        FROM doctors d
        JOIN specialties s ON d.speciality = s.id
        WHERE d.id = ?
    """
    d = db.execute(query, (doc_id,)).fetchone()
    db.close()

    if not d:
        return jsonify({'error': 'Doctor not found'}), 404

    item = dict(d)
    item['picture'] = encode_image(item['picture'])
    item['profile_picture'] = item['picture']
    return jsonify(item)

@admin_bp.route('/addDoctor', methods=['POST'])
def add_doctor():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    belong = data.get('hos_id') or data.get('belong')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    about = data.get('about')
    specialty_raw = data.get('specialty') or data.get('speciality')

    # Handle "1_Cardiology" or "1"
    if isinstance(specialty_raw, str) and '_' in specialty_raw:
        spec_id = int(specialty_raw.split('_')[0])
    else:
        spec_id = int(specialty_raw or 1)

    picture_path = None
    if 'profile_picture' in request.files and request.files['profile_picture'].filename:
        picture_path = save_uploaded_image(request.files['profile_picture'], 'doctors')
    elif data.get('profile_picture') and str(data.get('profile_picture')).startswith('data:'):
        picture_path = save_uploaded_image(data.get('profile_picture'), 'doctors')

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO doctors (first_name, last_name, about, speciality, picture, belong)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (first_name, last_name, about, spec_id, picture_path, belong))
    doc_id = cur.lastrowid
    db.commit()
    db.close()

    return jsonify({'success': True, 'id': doc_id})

@admin_bp.route('/updateDoctor', methods=['POST'])
def update_doctor():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    doc_id = data.get('id')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    about = data.get('about')
    specialty_raw = data.get('specialty') or data.get('speciality')

    if isinstance(specialty_raw, str) and '_' in specialty_raw:
        spec_id = int(specialty_raw.split('_')[0])
    else:
        spec_id = int(specialty_raw or 1)

    db = get_db()
    curr = db.execute("SELECT picture FROM doctors WHERE id = ?", (doc_id,)).fetchone()
    picture_path = curr['picture'] if curr else None

    if 'profile_picture' in request.files and request.files['profile_picture'].filename:
        picture_path = save_uploaded_image(request.files['profile_picture'], 'doctors', old_path=picture_path)
    elif data.get('profile_picture') and str(data.get('profile_picture')).startswith('data:'):
        picture_path = save_uploaded_image(data.get('profile_picture'), 'doctors', old_path=picture_path)

    db.execute("""
        UPDATE doctors
        SET first_name = ?, last_name = ?, about = ?, speciality = ?, picture = ?
        WHERE id = ?
    """, (first_name, last_name, about, spec_id, picture_path, doc_id))
    db.commit()
    db.close()

    return jsonify({'success': True})

@admin_bp.route('/deleteDoctor', methods=['GET'])
def delete_doctor():
    doc_id = request.args.get('id')
    db = get_db()
    db.execute("DELETE FROM doctors WHERE id = ?", (doc_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})

@admin_bp.route('/getAllSpecialty', methods=['GET'])
def get_all_specialty():
    db = get_db()
    rows = db.execute("SELECT id, specialty_name FROM specialties ORDER BY id ASC").fetchall()
    db.close()

    res = []
    for r in rows:
        res.append({
            'id': r['id'],
            'specialty_name': r['specialty_name'],
            'name': r['specialty_name']
        })
    return jsonify(res)

@admin_bp.route('/getTest', methods=['GET'])
def get_test():
    hos_id = request.args.get('hos_id') or request.args.get('id')
    db = get_db()
    rows = db.execute("SELECT * FROM test WHERE own = ?", (hos_id,)).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@admin_bp.route('/getTestForm', methods=['GET'])
def get_test_form():
    name = request.args.get('name')
    hos_id = request.args.get('hos_id')
    db = get_db()
    t = db.execute("SELECT * FROM test WHERE name = ? AND own = ?", (name, hos_id)).fetchone()
    db.close()
    if not t:
        return jsonify({'error': 'Test not found'}), 404
    return jsonify(dict(t))

@admin_bp.route('/addTest', methods=['POST'])
def add_test():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    name = data.get('name')
    description = data.get('description')
    cost = int(data.get('cost', 0))
    own = data.get('hos_id') or data.get('own')

    db = get_db()
    db.execute("""
        INSERT INTO test (name, description, cost, own)
        VALUES (?, ?, ?, ?)
    """, (name, description, cost, own))
    db.commit()
    db.close()

    return jsonify({'success': True})

@admin_bp.route('/updateTest', methods=['POST'])
def update_test():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    name = data.get('name')
    description = data.get('description')
    cost = int(data.get('cost', 0))
    own = data.get('hos_id') or data.get('own')

    db = get_db()
    db.execute("""
        UPDATE test
        SET description = ?, cost = ?
        WHERE name = ? AND own = ?
    """, (description, cost, name, own))
    db.commit()
    db.close()

    return jsonify({'success': True})

@admin_bp.route('/deleteTest', methods=['GET'])
def delete_test():
    name = request.args.get('name')
    hos_id = request.args.get('hos_id')

    db = get_db()
    db.execute("DELETE FROM test WHERE name = ? AND own = ?", (name, hos_id))
    db.commit()
    db.close()
    return jsonify({'success': True})

@admin_bp.route('/getBlood', methods=['GET'])
def get_blood():
    hos_id = request.args.get('hos_id') or request.args.get('id')
    db = get_db()
    rows = db.execute("SELECT * FROM blood_requests WHERE belong = ? ORDER BY id DESC", (hos_id,)).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@admin_bp.route('/getBloodForm', methods=['GET'])
def get_blood_form():
    req_id = request.args.get('id')
    db = get_db()
    r = db.execute("SELECT * FROM blood_requests WHERE id = ?", (req_id,)).fetchone()
    db.close()

    if not r:
        return jsonify({'error': 'Blood request not found'}), 404

    return jsonify(dict(r))

@admin_bp.route('/addBlood', methods=['POST'])
def add_blood():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    belong = data.get('hos_id') or data.get('belong')
    blood_group = data.get('blood_group')
    quantity = int(data.get('quantity', 1))
    date = data.get('date')
    time = data.get('time')
    description = data.get('description')

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO blood_requests (belong, blood_group, description, date, time, quantity)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (belong, blood_group, description, date, time, quantity))
    req_id = cur.lastrowid
    db.commit()
    db.close()

    return jsonify({'success': True, 'id': req_id})

@admin_bp.route('/updateBlood', methods=['POST'])
def update_blood():
    data = request.form if request.form else (request.get_json(silent=True) or {})
    req_id = data.get('id')
    blood_group = data.get('blood_group')
    quantity = int(data.get('quantity', 1))
    date = data.get('date')
    time = data.get('time')
    description = data.get('description')

    db = get_db()
    db.execute("""
        UPDATE blood_requests
        SET blood_group = ?, quantity = ?, date = ?, time = ?, description = ?
        WHERE id = ?
    """, (description and blood_group, quantity, date, time, description, req_id)) if False else db.execute("""
        UPDATE blood_requests
        SET blood_group = ?, quantity = ?, date = ?, time = ?, description = ?
        WHERE id = ?
    """, (blood_group, quantity, date, time, description, req_id))
    db.commit()
    db.close()

    return jsonify({'success': True})

@admin_bp.route('/deleteBlood', methods=['GET'])
def delete_blood():
    req_id = request.args.get('id')
    db = get_db()
    db.execute("DELETE FROM blood_requests WHERE id = ?", (req_id,))
    db.commit()
    db.close()
    return jsonify({'success': True})

@admin_bp.route('/interestedList', methods=['GET'])
def interested_list():
    req_id = request.args.get('id')
    db = get_db()
    query = """
        SELECT u.id as user_id, u.first_name, u.last_name, u.blood_group,
               u.phone_number, u.dob, u.picture
        FROM interested i
        JOIN "user" u ON i.user_id = u.id
        WHERE i.request_id = ?
    """
    rows = db.execute(query, (req_id,)).fetchall()
    db.close()

    res = []
    for r in rows:
        item = dict(r)
        item['age'] = calculate_age(item['dob'])
        item['picture'] = encode_image(item['picture'])
        res.append(item)
    return jsonify(res)
