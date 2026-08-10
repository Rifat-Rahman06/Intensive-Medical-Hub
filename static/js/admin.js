// Admin Global State
let currentHosId = null;
let currentSection = 'ward';
let allSpecialties = [];

let profileMap = null;
let profileMarker = null;

let isAddItem = 0; // 0 = edit, 1 = add

const hospitalIcon = L.divIcon({
  className: 'custom-marker',
  html: `<div class="marker-pin marker-hospital-pin"><div class="marker-inner"><i class="fa fa-hospital-o"></i></div></div>`,
  iconSize: [36, 36],
  iconAnchor: [18, 36],
  popupAnchor: [0, -36]
});

document.addEventListener('DOMContentLoaded', () => {
  const urlParams = new URLSearchParams(window.location.search);
  currentHosId = urlParams.get('id');

  if (!currentHosId) {
    window.location.href = '/admin/login/adminLogin.html';
    return;
  }

  initAdmin();
});

async function initAdmin() {
  await loadHospitalHeader();
  await loadSpecialties();
  switchSection('ward');
}

async function loadHospitalHeader() {
  try {
    const res = await fetch(`/server/admin/loadProfile?id=${currentHosId}`);
    if (res.ok) {
      const data = await res.json();
      document.getElementById('hospitalNameHeader').innerText = data.name;
    }
  } catch (err) {
    console.error('Error loading hospital profile:', err);
  }
}

async function loadSpecialties() {
  try {
    const res = await fetch('/server/admin/getAllSpecialty');
    allSpecialties = await res.json();

    const select = document.getElementById('docSpecialty');
    select.innerHTML = allSpecialties.map(s => `
      <option value="${s.id}_${s.specialty_name}">${s.specialty_name}</option>
    `).join('');
  } catch (err) {
    console.error('Error loading specialties:', err);
  }
}

function switchSection(sec) {
  currentSection = sec;
  document.querySelectorAll('.admin-nav .nav-btn').forEach(b => b.classList.remove('active'));

  const titles = {
    ward: 'Ward Facilities',
    test: 'Diagnostic Tests',
    doctor: 'Medical Specialists & Doctors',
    blood: 'Active Blood Requests'
  };

  const addLabels = {
    ward: 'Add Ward',
    test: 'Add Test',
    doctor: 'Add Doctor',
    blood: 'Create Blood Request'
  };

  const btnId = 'nav' + capitalize(sec) + 'Btn';
  const navBtn = document.getElementById(btnId);
  if (navBtn) navBtn.classList.add('active');

  document.getElementById('sectionTitle').innerText = titles[sec];
  document.getElementById('addBtn').innerHTML = `<i class="fa fa-plus-circle"></i> ${addLabels[sec]}`;

  loadSectionData();
}

function loadSectionData() {
  if (currentSection === 'ward') loadWards();
  if (currentSection === 'test') loadTests();
  if (currentSection === 'doctor') loadDoctors();
  if (currentSection === 'blood') loadBloodRequests();
}

// 1. WARDS MANAGEMENT
async function loadWards() {
  const grid = document.getElementById('cardsGrid');
  grid.innerHTML = '<p>Loading wards...</p>';

  try {
    const res = await fetch(`/server/admin/getWard?id=${currentHosId}`);
    const wards = await res.json();

    if (wards.length === 0) {
      grid.innerHTML = '<p class="empty">No wards added yet. Click "Add Ward" above.</p>';
      return;
    }

    grid.innerHTML = wards.map(w => {
      const pct = w.capacity > 0 ? Math.round((w.occupied / w.capacity) * 100) : 0;
      return `
        <div class="admin-card">
          <div>
            <div class="card-header">
              <h3>${w.ward_type}</h3>
              <span class="badge" style="background:#e0f2fe; color:#0369a1;">৳${w.cost_per_day}/day</span>
            </div>
            <div class="card-body">
              <p>${w.about}</p>
              <div class="occ-bar">
                <div class="occ-text">
                  <span>Bed Occupancy:</span>
                  <strong>${w.occupied} / ${w.capacity}</strong>
                </div>
                <div class="progress-bg">
                  <div class="progress-fill" style="width:${pct}%; background:${pct > 85 ? '#ef4444' : '#0284c7'};"></div>
                </div>
              </div>
              <div class="occ-controls">
                <span>Quick Adjust:</span>
                <button class="btn-qty" onclick="adjustWardOccupancy(${w.id}, -1)">-</button>
                <button class="btn-qty" onclick="adjustWardOccupancy(${w.id}, 1)">+</button>
              </div>
            </div>
          </div>
          <div class="card-actions">
            <button class="btn-card-edit" onclick="editWard(${w.id})"><i class="fa fa-pencil"></i> Edit</button>
            <button class="btn-card-delete" onclick="deleteWard(${w.id})"><i class="fa fa-trash"></i> Delete</button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Error loading wards:', err);
  }
}

async function adjustWardOccupancy(wardId, val) {
  try {
    await fetch(`/server/admin/updateWardAvailability?id=${wardId}&value=${val}`);
    loadWards();
  } catch (err) {
    console.error('Error adjusting ward availability:', err);
  }
}

async function editWard(wardId) {
  isAddItem = 0;
  document.getElementById('wardModalTitle').innerText = 'Edit Ward';

  const res = await fetch(`/server/admin/getWardForm?id=${wardId}`);
  const w = await res.json();

  document.getElementById('wardId').value = w.id;
  document.getElementById('wardType').value = w.ward_type;
  document.getElementById('wardCapacity').value = w.capacity;
  document.getElementById('wardOccupied').value = w.occupied;
  document.getElementById('wardCost').value = w.cost_per_day;
  document.getElementById('wardAbout').value = w.about;

  openModal('wardModal');
}

async function saveWard() {
  const form = document.getElementById('wardForm');
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }

  const formData = new FormData(form);
  formData.append('belong', currentHosId);
  formData.append('hos_id', currentHosId);

  const endpoint = isAddItem === 1 ? '/server/admin/addWard' : '/server/admin/updateWard';

  try {
    const res = await fetch(endpoint, { method: 'POST', body: formData });
    const result = await res.json();
    if (result.success) {
      closeModal('wardModal');
      loadWards();
    }
  } catch (err) {
    console.error('Error saving ward:', err);
  }
}

async function deleteWard(wardId) {
  if (!confirm('Are you sure you want to delete this ward?')) return;
  try {
    await fetch(`/server/admin/deleteWard?id=${wardId}`);
    loadWards();
  } catch (err) {
    console.error('Error deleting ward:', err);
  }
}

// 2. DOCTORS MANAGEMENT
async function loadDoctors() {
  const grid = document.getElementById('cardsGrid');
  grid.innerHTML = '<p>Loading doctors...</p>';

  try {
    const res = await fetch(`/server/admin/getDoctor?id=${currentHosId}`);
    const doctors = await res.json();

    if (doctors.length === 0) {
      grid.innerHTML = '<p class="empty">No doctors added yet. Click "Add Doctor" above.</p>';
      return;
    }

    grid.innerHTML = doctors.map(d => `
      <div class="admin-card">
        <div>
          <div class="card-header" style="align-items:center; gap:12px;">
            <img src="${d.picture}" style="width:50px; height:50px; border-radius:50%; object-fit:cover;">
            <div>
              <h3>${d.first_name} ${d.last_name}</h3>
              <span class="badge" style="background:#e0f2fe; color:#0369a1;">${d.specialty}</span>
            </div>
          </div>
          <div class="card-body">
            <p>${d.about}</p>
          </div>
        </div>
        <div class="card-actions">
          <button class="btn-card-edit" onclick="editDoctor(${d.id})"><i class="fa fa-pencil"></i> Edit</button>
          <button class="btn-card-delete" onclick="deleteDoctor(${d.id})"><i class="fa fa-trash"></i> Delete</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading doctors:', err);
  }
}

function previewDocImg(event) {
  const reader = new FileReader();
  reader.onload = function() {
    document.getElementById('doctorPreview').src = reader.result;
  };
  if (event.target.files[0]) {
    reader.readAsDataURL(event.target.files[0]);
  }
}

async function editDoctor(docId) {
  isAddItem = 0;
  document.getElementById('doctorModalTitle').innerText = 'Edit Doctor';

  const res = await fetch(`/server/admin/getDoctorForm?id=${docId}`);
  const d = await res.json();

  document.getElementById('doctorId').value = d.id;
  document.getElementById('doctorPreview').src = d.picture;
  document.getElementById('docFirstName').value = d.first_name;
  document.getElementById('docLastName').value = d.last_name;
  document.getElementById('docAbout').value = d.about;

  if (d.speciality) {
    const matched = allSpecialties.find(s => s.id == d.speciality);
    if (matched) {
      document.getElementById('docSpecialty').value = `${matched.id}_${matched.specialty_name}`;
    }
  }

  openModal('doctorModal');
}

async function saveDoctor() {
  const form = document.getElementById('doctorForm');
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }

  const formData = new FormData(form);
  formData.append('hos_id', currentHosId);
  formData.append('belong', currentHosId);

  const endpoint = isAddItem === 1 ? '/server/admin/addDoctor' : '/server/admin/updateDoctor';

  try {
    const res = await fetch(endpoint, { method: 'POST', body: formData });
    const result = await res.json();
    if (result.success) {
      closeModal('doctorModal');
      loadDoctors();
    }
  } catch (err) {
    console.error('Error saving doctor:', err);
  }
}

async function deleteDoctor(docId) {
  if (!confirm('Are you sure you want to delete this doctor?')) return;
  try {
    await fetch(`/server/admin/deleteDoctor?id=${docId}`);
    loadDoctors();
  } catch (err) {
    console.error('Error deleting doctor:', err);
  }
}

// 3. TESTS MANAGEMENT
async function loadTests() {
  const grid = document.getElementById('cardsGrid');
  grid.innerHTML = '<p>Loading tests...</p>';

  try {
    const res = await fetch(`/server/admin/getTest?hos_id=${currentHosId}`);
    const tests = await res.json();

    if (tests.length === 0) {
      grid.innerHTML = '<p class="empty">No tests added yet. Click "Add Test" above.</p>';
      return;
    }

    grid.innerHTML = tests.map(t => `
      <div class="admin-card">
        <div>
          <div class="card-header">
            <h3>${t.name}</h3>
            <span class="badge" style="background:#f0fdf4; color:#15803d;">৳${t.cost}</span>
          </div>
          <div class="card-body">
            <p>${t.description}</p>
          </div>
        </div>
        <div class="card-actions">
          <button class="btn-card-edit" onclick="editTest('${encodeURIComponent(t.name)}')"><i class="fa fa-pencil"></i> Edit</button>
          <button class="btn-card-delete" onclick="deleteTest('${encodeURIComponent(t.name)}')"><i class="fa fa-trash"></i> Delete</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading tests:', err);
  }
}

async function editTest(encodedName) {
  isAddItem = 0;
  document.getElementById('testModalTitle').innerText = 'Edit Diagnostic Test';

  const res = await fetch(`/server/admin/getTestForm?name=${encodedName}&hos_id=${currentHosId}`);
  const t = await res.json();

  document.getElementById('testOldName').value = t.name;
  document.getElementById('testName').value = t.name;
  document.getElementById('testCost').value = t.cost;
  document.getElementById('testDesc').value = t.description;

  openModal('testModal');
}

async function saveTest() {
  const form = document.getElementById('testForm');
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }

  const formData = new FormData(form);
  formData.append('hos_id', currentHosId);
  formData.append('own', currentHosId);

  const endpoint = isAddItem === 1 ? '/server/admin/addTest' : '/server/admin/updateTest';

  try {
    const res = await fetch(endpoint, { method: 'POST', body: formData });
    const result = await res.json();
    if (result.success) {
      closeModal('testModal');
      loadTests();
    }
  } catch (err) {
    console.error('Error saving test:', err);
  }
}

async function deleteTest(encodedName) {
  if (!confirm('Are you sure you want to delete this test?')) return;
  try {
    await fetch(`/server/admin/deleteTest?name=${encodedName}&hos_id=${currentHosId}`);
    loadTests();
  } catch (err) {
    console.error('Error deleting test:', err);
  }
}

// 4. BLOOD REQUESTS MANAGEMENT
async function loadBloodRequests() {
  const grid = document.getElementById('cardsGrid');
  grid.innerHTML = '<p>Loading blood requests...</p>';

  try {
    const res = await fetch(`/server/admin/getBlood?hos_id=${currentHosId}`);
    const requests = await res.json();

    if (requests.length === 0) {
      grid.innerHTML = '<p class="empty">No blood requests created yet. Click "Create Blood Request" above.</p>';
      return;
    }

    grid.innerHTML = requests.map(b => `
      <div class="admin-card" style="border-left:4px solid #dc2626;">
        <div>
          <div class="card-header">
            <h3>Blood Request</h3>
            <span class="badge" style="background:#fef2f2; color:#dc2626; font-size:14px; font-weight:800;">${b.blood_group}</span>
          </div>
          <div class="card-body">
            <p><strong>Quantity Needed:</strong> ${b.quantity} Bag(s)</p>
            <p><strong>Required Date:</strong> ${b.date} at ${b.time}</p>
            <p>${b.description}</p>
          </div>
        </div>
        <div class="card-actions">
          <button class="btn-card-edit" onclick="editBlood(${b.id})"><i class="fa fa-users"></i> View Donors / Edit</button>
          <button class="btn-card-delete" onclick="deleteBlood(${b.id})"><i class="fa fa-trash"></i> Delete</button>
        </div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Error loading blood requests:', err);
  }
}

async function editBlood(reqId) {
  isAddItem = 0;
  document.getElementById('bloodModalTitle').innerText = 'Manage Blood Request';
  document.getElementById('donorsSection').style.display = 'block';

  const res = await fetch(`/server/admin/getBloodForm?id=${reqId}`);
  const b = await res.json();

  document.getElementById('bloodId').value = b.id;
  document.getElementById('bloodGroupSelect').value = b.blood_group;
  document.getElementById('bloodQty').value = b.quantity;
  document.getElementById('bloodDate').value = b.date;
  document.getElementById('bloodTime').value = b.time;
  document.getElementById('bloodDesc').value = b.description;

  // Load interested donors list
  loadInterestedDonors(reqId);

  openModal('bloodModal');
}

async function loadInterestedDonors(reqId) {
  const tbody = document.getElementById('donorsList');
  tbody.innerHTML = '<tr><td colspan="4">Loading registered donors...</td></tr>';

  try {
    const res = await fetch(`/server/admin/interestedList?id=${reqId}`);
    const donors = await res.json();

    if (donors.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#64748b;">No interested donors registered yet.</td></tr>';
      return;
    }

    tbody.innerHTML = donors.map(d => `
      <tr>
        <td style="display:flex; align-items:center; gap:8px;">
          <img src="${d.picture}" style="width:28px; height:28px; border-radius:50%; object-fit:cover;">
          <strong>${d.first_name} ${d.last_name}</strong>
        </td>
        <td><span class="badge" style="background:#fef2f2; color:#dc2626;">${d.blood_group}</span></td>
        <td>${d.age ? d.age + ' yrs' : 'N/A'}</td>
        <td><a href="tel:${d.phone_number}" style="color:#0284c7; text-decoration:none;"><i class="fa fa-phone"></i> ${d.phone_number}</a></td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Error loading interested donors:', err);
  }
}

async function saveBlood() {
  const form = document.getElementById('bloodForm');
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }

  const formData = new FormData(form);
  formData.append('hos_id', currentHosId);
  formData.append('belong', currentHosId);

  const endpoint = isAddItem === 1 ? '/server/admin/addBlood' : '/server/admin/updateBlood';

  try {
    const res = await fetch(endpoint, { method: 'POST', body: formData });
    const result = await res.json();
    if (result.success) {
      closeModal('bloodModal');
      loadBloodRequests();
    }
  } catch (err) {
    console.error('Error saving blood request:', err);
  }
}

async function deleteBlood(reqId) {
  if (!confirm('Are you sure you want to delete this blood request?')) return;
  try {
    await fetch(`/server/admin/deleteBlood?id=${reqId}`);
    loadBloodRequests();
  } catch (err) {
    console.error('Error deleting blood request:', err);
  }
}

// Global Add Button Handler
function openAddForm() {
  isAddItem = 1;
  if (currentSection === 'ward') {
    document.getElementById('wardForm').reset();
    document.getElementById('wardModalTitle').innerText = 'Add Ward';
    openModal('wardModal');
  } else if (currentSection === 'doctor') {
    document.getElementById('doctorForm').reset();
    document.getElementById('doctorPreview').src = '/static/images/profile.svg';
    document.getElementById('doctorModalTitle').innerText = 'Add Doctor';
    openModal('doctorModal');
  } else if (currentSection === 'test') {
    document.getElementById('testForm').reset();
    document.getElementById('testModalTitle').innerText = 'Add Diagnostic Test';
    openModal('testModal');
  } else if (currentSection === 'blood') {
    document.getElementById('bloodForm').reset();
    document.getElementById('donorsSection').style.display = 'none';
    document.getElementById('bloodModalTitle').innerText = 'Create Blood Request';
    openModal('bloodModal');
  }
}

// 5. HOSPITAL PROFILE SETTINGS & LOCATION MAP
async function openProfileModal() {
  try {
    const res = await fetch(`/server/admin/loadProfile?id=${currentHosId}`);
    const data = await res.json();

    document.getElementById('hosName').value = data.name;
    document.getElementById('hosContact').value = data.contact_no;
    document.getElementById('hosType').value = data.type;
    document.getElementById('hosEmergency').value = data.emergency_units;
    document.getElementById('hosLat').value = data.latitude;
    document.getElementById('hosLng').value = data.longitude;
    document.getElementById('hospitalPreview').src = data.image;

    openModal('profileModal');

    // Initialize Map for Pinning
    setTimeout(() => {
      initProfileMap(data.latitude, data.longitude);
    }, 200);
  } catch (err) {
    console.error('Error opening profile modal:', err);
  }
}

function initProfileMap(lat, lng) {
  if (!profileMap) {
    profileMap = L.map('profileMap').setView([lat, lng], 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors'
    }).addTo(profileMap);

    profileMarker = L.marker([lat, lng], { draggable: true, icon: hospitalIcon }).addTo(profileMap);

    profileMarker.on('dragend', (e) => {
      const pos = profileMarker.getLatLng();
      document.getElementById('hosLat').value = pos.lat.toFixed(6);
      document.getElementById('hosLng').value = pos.lng.toFixed(6);
    });

    profileMap.on('click', (e) => {
      profileMarker.setLatLng(e.latlng);
      document.getElementById('hosLat').value = e.latlng.lat.toFixed(6);
      document.getElementById('hosLng').value = e.latlng.lng.toFixed(6);
    });
  } else {
    profileMap.setView([lat, lng], 14);
    profileMarker.setLatLng([lat, lng]);
    profileMap.invalidateSize();
  }
}

function setMapToMyLocation() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition((pos) => {
      const lat = pos.coords.latitude;
      const lng = pos.coords.longitude;
      document.getElementById('hosLat').value = lat.toFixed(6);
      document.getElementById('hosLng').value = lng.toFixed(6);

      if (profileMap && profileMarker) {
        profileMap.setView([lat, lng], 14);
        profileMarker.setLatLng([lat, lng]);
      }
    });
  }
}

function previewHosImg(event) {
  const reader = new FileReader();
  reader.onload = function() {
    document.getElementById('hospitalPreview').src = reader.result;
  };
  if (event.target.files[0]) {
    reader.readAsDataURL(event.target.files[0]);
  }
}

async function saveHospitalProfile() {
  const form = document.getElementById('hospitalProfileForm');
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }

  const formData = new FormData(form);
  formData.append('id', currentHosId);

  try {
    const res = await fetch('/server/admin/updateProfile', {
      method: 'POST',
      body: formData
    });
    const result = await res.json();
    if (result.success) {
      alert('Hospital profile updated successfully!');
      closeModal('profileModal');
      loadHospitalHeader();
    }
  } catch (err) {
    console.error('Error saving hospital profile:', err);
  }
}

// Modal Helpers
function openModal(id) {
  document.getElementById(id).style.display = 'flex';
}

function closeModal(id) {
  document.getElementById(id).style.display = 'none';
}

function logout() {
  window.location.href = '/admin/login/adminLogin.html';
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}
