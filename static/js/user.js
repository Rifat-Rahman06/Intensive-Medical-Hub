// Global Application State
let currentUserId = null;
let userProfile = null;
let userLat = 23.7258;
let userLng = 90.3976;

let hospitalMap = null;
let bloodMap = null;
let userMarker = null;

let hospitalMarkers = [];
let bloodMarkers = [];

let selectedHospitalId = null;
let currentRatingScore = 5;
let currentReviews = [];

// Leaflet Icons
const hospitalIcon = L.divIcon({
  className: 'custom-marker',
  html: `<div class="marker-pin marker-hospital-pin"><div class="marker-inner"><i class="fa fa-hospital-o"></i></div></div>`,
  iconSize: [36, 36],
  iconAnchor: [18, 36],
  popupAnchor: [0, -36]
});

const userIcon = L.divIcon({
  className: 'custom-marker',
  html: `<div class="user-pulse-marker"><div class="pulse-ring"></div><div class="pulse-dot"></div></div>`,
  iconSize: [24, 24],
  iconAnchor: [12, 12]
});

const bloodIcon = L.divIcon({
  className: 'custom-marker',
  html: `<div class="marker-pin marker-blood-pin"><div class="marker-inner"><i class="fa fa-tint" style="color:var(--accent-red);"></i></div></div>`,
  iconSize: [36, 36],
  iconAnchor: [18, 36],
  popupAnchor: [0, -36]
});

// Document Ready Initialization
document.addEventListener('DOMContentLoaded', () => {
  const urlParams = new URLSearchParams(window.location.search);
  currentUserId = urlParams.get('id');

  if (!currentUserId) {
    window.location.href = '/user/login/userLogin.html';
    return;
  }

  initUser();
  initMaps();
  setInterval(loadMyLocation, 5000);
});

async function initUser() {
  try {
    const res = await fetch(`/server/user/profile?id=${currentUserId}`);
    if (res.ok) {
      userProfile = await res.json();
      document.getElementById('userNameHeader').innerText = `${userProfile.first_name} ${userProfile.last_name}`;
      document.getElementById('userAvatarHeader').src = userProfile.picture;
      document.getElementById('profilePreview').src = userProfile.picture;

      // Populate profile edit form
      document.getElementById('profFirstName').value = userProfile.first_name;
      document.getElementById('profLastName').value = userProfile.last_name;
      document.getElementById('profDob').value = userProfile.dob;
      document.getElementById('profBloodGroup').value = userProfile.blood_group;
      document.getElementById('profPhone').value = userProfile.phone_number;
    }
  } catch (err) {
    console.error('Failed to load user profile:', err);
  }
}

function initMaps() {
  // Hospital Map
  hospitalMap = L.map('hospitalMap').setView([userLat, userLng], 13);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap contributors'
  }).addTo(hospitalMap);

  hospitalMap.on('click', () => {
    // Optionally close drawer on map click
  });

  loadMyLocation();
  loadAllHospitals();
}

function loadMyLocation() {
  if (navigator.geolocation) {
    navigator.geolocation.getCurrentPosition((pos) => {
      userLat = pos.coords.latitude;
      userLng = pos.coords.longitude;

      if (hospitalMap) {
        if (!userMarker) {
          userMarker = L.marker([userLat, userLng], { icon: userIcon }).addTo(hospitalMap).bindPopup("You are here");
        } else {
          userMarker.setLatLng([userLat, userLng]);
        }
      }
    }, (err) => {
      // Use default coordinates if geolocation denied
    });
  }
}

async function loadAllHospitals() {
  try {
    const res = await fetch('/server/user/allCoordinates');
    const data = await res.json();
    clearHospitalMarkers();

    data.forEach(h => {
      const marker = L.marker([h.lat, h.lng], { icon: hospitalIcon }).addTo(hospitalMap);
      marker.bindTooltip(h.name, { permanent: false, direction: 'top' });
      marker.on('click', () => getinfo(h.id));
      hospitalMarkers.push(marker);
    });
  } catch (err) {
    console.error('Error loading hospital coordinates:', err);
  }
}

function clearHospitalMarkers() {
  hospitalMarkers.forEach(m => hospitalMap.removeLayer(m));
  hospitalMarkers = [];
}

async function loadFilter() {
  const radius = document.getElementById('radiusDistance').value;
  const hasWard = document.getElementById('checkWard').checked ? '1' : '0';
  const hasEmergency = document.getElementById('checkEmergency').checked ? '1' : '0';
  const ownership = document.querySelector('input[name="ownership"]:checked').value;

  const isPublic = (ownership === 'public' || ownership === 'all') ? '1' : '0';
  const isPrivate = (ownership === 'private' || ownership === 'all') ? '1' : '0';

  const query = `radiusDistance=${radius}&hasWard=${hasWard}&hasEmergencyUnit=${hasEmergency}&public=${isPublic}&private=${isPrivate}&lat=${userLat}&lon=${userLng}`;

  try {
    const res = await fetch(`/server/user/filterCoordinate?${query}`);
    const filtered = await res.json();

    clearHospitalMarkers();
    filtered.forEach(h => {
      const marker = L.marker([h.lat, h.lng], { icon: hospitalIcon }).addTo(hospitalMap);
      marker.bindTooltip(`${h.name} (${h.distance} km)`, { permanent: false, direction: 'top' });
      marker.on('click', () => getinfo(h.id));
      hospitalMarkers.push(marker);
    });
  } catch (err) {
    console.error('Error filtering hospitals:', err);
  }
}

function updateRadiusLabel(val) {
  document.getElementById('radiusVal').innerText = `${val} km`;
}

function resetFilters() {
  document.getElementById('radiusDistance').value = 400;
  document.getElementById('radiusVal').innerText = '400 km';
  document.getElementById('checkWard').checked = false;
  document.getElementById('checkEmergency').checked = false;
  document.querySelector('input[name="ownership"][value="all"]').checked = true;
  loadAllHospitals();
}

async function getinfo(hosId, keepCurrentTab = false) {
  selectedHospitalId = hosId;
  document.getElementById('infoTab').classList.add('open');

  try {
    const [identityRes, rateRes] = await Promise.all([
      fetch(`/server/user/getIdentity?id=${hosId}`),
      fetch(`/server/user/getRate?hos_id=${hosId}&my_id=${currentUserId}`)
    ]);

    const identity = await identityRes.json();
    const rateData = await rateRes.json();

    document.getElementById('infoHospitalImg').src = identity.image;
    document.getElementById('infoHospitalName').innerText = identity.name;
    const typeSpan = document.getElementById('infoHospitalType');
    typeSpan.innerText = identity.type;
    typeSpan.className = 'badge';
    if (identity.type && identity.type.toLowerCase() === 'public') {
      typeSpan.classList.add('badge-public');
    } else {
      typeSpan.classList.add('badge-private');
    }

    const emergencySpan = document.getElementById('infoHospitalEmergency');
    emergencySpan.innerText = identity.emergency ? 'Emergency 24/7' : 'No Emergency';
    emergencySpan.className = 'badge';
    if (identity.emergency) {
      emergencySpan.classList.add('badge-emergency');
    } else {
      emergencySpan.classList.add('badge-no-emergency');
    }
    document.getElementById('infoHospitalContact').innerText = identity.contact;
    document.getElementById('infoHospitalRating').innerText = rateData.rate;

    setRating(rateData.my_rate || 5);

    // Pan map to hospital location
    fetch(`/server/user/allCoordinates`).then(r => r.json()).then(data => {
      const h = data.find(x => x.id == hosId);
      if (h) hospitalMap.panTo([h.lat, h.lng]);
    });

    let targetTab = 'wards';
    if (keepCurrentTab) {
      ['wards', 'tests', 'doctors', 'reviews'].forEach(t => {
        const btn = document.getElementById(`tab${capitalize(t)}Btn`);
        if (btn && btn.classList.contains('active')) {
          targetTab = t;
        }
      });
    }
    switchDrawerTab(targetTab);
  } catch (err) {
    console.error('Error fetching hospital info:', err);
  }
}

function closeInfo() {
  document.getElementById('infoTab').classList.remove('open');
  selectedHospitalId = null;
}

function switchDrawerTab(tabName) {
  ['wards', 'tests', 'doctors', 'reviews'].forEach(t => {
    document.getElementById(`tab${capitalize(t)}Btn`).classList.toggle('active', t === tabName);
    document.getElementById(`drawer${capitalize(t)}`).classList.toggle('active', t === tabName);
  });

  if (selectedHospitalId) {
    if (tabName === 'wards') loadWards(selectedHospitalId);
    if (tabName === 'tests') loadTests(selectedHospitalId);
    if (tabName === 'doctors') loadDoctors(selectedHospitalId);
    if (tabName === 'reviews') loadReviews(selectedHospitalId);
  }
}

async function loadWards(hosId) {
  const container = document.getElementById('drawerWards');
  container.innerHTML = '<p class="loading">Loading wards...</p>';

  const res = await fetch(`/server/user/getWard?id=${hosId}`);
  const wards = await res.json();

  if (wards.length === 0) {
    container.innerHTML = '<p class="empty">No wards listed for this hospital.</p>';
    return;
  }

  container.innerHTML = wards.map(w => {
    const pct = w.capacity > 0 ? Math.round((w.occupied / w.capacity) * 100) : 0;
    return `
      <div class="info-card">
        <h4>${w.ward_type}</h4>
        <p>${w.about}</p>
        <div style="margin-top:6px; font-size:12px; font-weight:600; display:flex; justify-content:space-between;">
          <span>Occupancy: ${w.occupied}/${w.capacity} beds</span>
          <span>Cost: ৳${w.cost}/day</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" style="width:${pct}%; background:${pct > 85 ? '#ef4444' : '#0d9488'};"></div>
        </div>
      </div>
    `;
  }).join('');
}

async function loadTests(hosId) {
  const container = document.getElementById('drawerTests');
  container.innerHTML = '<p class="loading">Loading tests...</p>';

  const res = await fetch(`/server/user/getTest?id=${hosId}`);
  const tests = await res.json();

  if (tests.length === 0) {
    container.innerHTML = '<p class="empty">No diagnostic tests listed.</p>';
    return;
  }

  container.innerHTML = tests.map(t => `
    <div class="info-card">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <h4>${t.name}</h4>
        <span class="badge" style="background:#f0fdf4; color:#0f766e;">৳${t.cost}</span>
      </div>
      <p style="margin-top:4px;">${t.description}</p>
    </div>
  `).join('');
}

async function loadDoctors(hosId) {
  const container = document.getElementById('drawerDoctors');
  container.innerHTML = '<p class="loading">Loading doctors...</p>';

  const res = await fetch(`/server/user/getSpecialty?id=${hosId}`);
  const doctors = await res.json();

  if (doctors.length === 0) {
    container.innerHTML = '<p class="empty">No doctors listed.</p>';
    return;
  }

  container.innerHTML = doctors.map(d => `
    <div class="info-card" style="display:flex; gap:12px; align-items:center;">
      <img src="${d.picture}" alt="${d.last_name}" style="width:50px; height:50px; border-radius:50%; object-fit:cover;">
      <div>
        <h4>${d.first_name} ${d.last_name}</h4>
        <span class="badge" style="margin-bottom:4px; display:inline-block;">${d.specialty}</span>
        <p>${d.about}</p>
      </div>
    </div>
  `).join('');
}

async function loadReviews(hosId) {
  const container = document.getElementById('reviewList');
  container.innerHTML = '<p class="loading">Loading reviews...</p>';

  const res = await fetch(`/server/user/getReview?id=${hosId}`);
  const reviews = await res.json();
  currentReviews = reviews;

  if (reviews.length === 0) {
    container.innerHTML = '<p class="empty">No patient reviews yet. Be the first to review!</p>';
    return;
  }

  container.innerHTML = reviews.map(r => {
    const isMyReview = r.user_id == currentUserId;
    const stars = Array.from({length: 5}, (_, i) => `<i class="fa fa-star ${i < r.rate ? 'text-warning' : 'text-muted'}"></i>`).join('');
    
    let actionsHtml = '';
    if (isMyReview) {
      actionsHtml = `
        <div style="display:flex; gap:8px; margin-top:10px;">
          <button class="btn-primary-sm" style="background:#0d9488; padding:4px 10px; display:inline-flex; align-items:center; gap:4px;" onclick="editMyReview()">
            <i class="fa fa-pencil"></i> Edit
          </button>
          <button class="btn-primary-sm" style="background:#ef4444; padding:4px 10px; display:inline-flex; align-items:center; gap:4px;" onclick="deleteReview()">
            <i class="fa fa-trash"></i> Delete
          </button>
        </div>
      `;
    }

    return `
      <div class="info-card" style="margin-bottom:12px; border-radius:12px; border:1px solid #e2e8f0; box-shadow:0 1px 3px rgba(0,0,0,0.02);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div style="display:flex; gap:10px; align-items:center;">
            <img src="${r.picture}" style="width:34px; height:34px; border-radius:50%; object-fit:cover; border:1px solid #cbd5e1;">
            <strong>${r.first_name} ${r.last_name} ${isMyReview ? '<span class="badge badge-emergency" style="margin-left:4px;">You</span>' : ''}</strong>
          </div>
          <span style="font-size:11px; color:#94a3b8;"><i class="fa fa-clock-o"></i> ${r.date}</span>
        </div>
        <div style="margin:8px 0 6px 0;">${stars}</div>
        <p style="font-size:13px; color:#475569; line-height:1.4; margin:0;">${r.review}</p>
        ${actionsHtml}
      </div>
    `;
  }).join('');
}

function setRating(score) {
  currentRatingScore = score;
  const stars = document.querySelectorAll('#starSelector i');
  stars.forEach((s, idx) => {
    s.classList.toggle('active', idx < score);
  });
}

function editMyReview() {
  const myReview = currentReviews.find(r => r.user_id == currentUserId);
  if (!myReview) return;

  document.getElementById('reviewTextInput').value = myReview.review;
  setRating(myReview.rate);
  const btn = document.getElementById('submitReviewBtn');
  if (btn) {
    btn.innerHTML = '<i class="fa fa-save"></i> Save Changes';
  }
  const cancelBtn = document.getElementById('cancelEditReviewBtn');
  if (cancelBtn) {
    cancelBtn.style.display = 'inline-block';
  }
  const heading = document.getElementById('reviewBoxHeading');
  if (heading) {
    heading.innerText = 'Edit Your Review';
  }
}

function resetReviewForm() {
  document.getElementById('reviewTextInput').value = '';
  setRating(5);
  const btn = document.getElementById('submitReviewBtn');
  if (btn) {
    btn.innerHTML = '<i class="fa fa-paper-plane"></i> Submit Review';
  }
  const cancelBtn = document.getElementById('cancelEditReviewBtn');
  if (cancelBtn) {
    cancelBtn.style.display = 'none';
  }
  const heading = document.getElementById('reviewBoxHeading');
  if (heading) {
    heading.innerText = 'Write a Review';
  }
}

async function submitReview() {
  if (!selectedHospitalId) return;
  const reviewText = document.getElementById('reviewTextInput').value.trim();

  if (!reviewText) {
    alert('Please write your review text.');
    return;
  }

  try {
    const res = await fetch('/server/user/addReview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        user: currentUserId,
        hospital: selectedHospitalId,
        review: reviewText,
        rate: currentRatingScore
      })
    });

    const result = await res.json();
    if (result.success) {
      resetReviewForm();
      loadReviews(selectedHospitalId);
      getinfo(selectedHospitalId, true);
    }
  } catch (err) {
    console.error('Error submitting review:', err);
  }
}

async function deleteReview() {
  if (!selectedHospitalId) return;

  try {
    const res = await fetch(`/server/user/deleteReview?hos_id=${selectedHospitalId}&my_id=${currentUserId}`);
    const result = await res.json();
    if (result.success) {
      resetReviewForm();
      loadReviews(selectedHospitalId);
      getinfo(selectedHospitalId, true);
    }
  } catch (err) {
    console.error('Error deleting review:', err);
  }
}

// Navigation Tab Switching
function switchNav(nav) {
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.view-section').forEach(s => s.style.display = 'none');

  if (nav === 'hospitals') {
    document.getElementById('navHospitals').classList.add('active');
    document.getElementById('hospitalsView').style.display = 'flex';
  } else if (nav === 'blood') {
    document.getElementById('navBlood').classList.add('active');
    document.getElementById('bloodView').style.display = 'flex';
    initBloodView();
  } else if (nav === 'about') {
    document.getElementById('navAbout').classList.add('active');
    document.getElementById('aboutView').style.display = 'flex';
  }
}

// Blood Requests View Logic
async function initBloodView() {
  if (!bloodMap) {
    bloodMap = L.map('bloodMap').setView([userLat, userLng], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap contributors'
    }).addTo(bloodMap);
  }

  loadBloodRequests();
}

async function loadBloodRequests() {
  const matchBlood = document.getElementById('matchBloodGroup').checked;
  const endpoint = matchBlood
    ? `/server/user/loadBHospitalByFilter?my_id=${currentUserId}`
    : `/server/user/loadBHospital`;

  try {
    const res = await fetch(endpoint);
    const hospitals = await res.json();

    // Clear blood markers
    bloodMarkers.forEach(m => bloodMap.removeLayer(m));
    bloodMarkers = [];

    const feedList = document.getElementById('bloodRequestFeed');
    feedList.innerHTML = '';

    if (hospitals.length === 0) {
      feedList.innerHTML = '<p class="empty">No matching blood requests found at this time.</p>';
      return;
    }

    const myInterestsRes = await fetch(`/server/user/getMyInterests?my_id=${currentUserId}`);
    const myInterests = await myInterestsRes.json();

    for (const h of hospitals) {
      const marker = L.marker([h.lat, h.lng], { icon: bloodIcon }).addTo(bloodMap);
      marker.bindTooltip(h.name, { permanent: false, direction: 'top' });
      bloodMarkers.push(marker);

      const reqEndpoint = matchBlood
        ? `/server/user/getRequestByFilter?hos_id=${h.id}&my_id=${currentUserId}`
        : `/server/user/getRequest?hos_id=${h.id}`;

      const reqRes = await fetch(reqEndpoint);
      const requests = await reqRes.json();

      requests.forEach(req => {
        const isInterested = myInterests.includes(req.id);
        const card = document.createElement('div');
        card.className = 'blood-card';
        card.innerHTML = `
          <div class="blood-card-header">
            <h4 class="blood-card-title"><i class="fa fa-hospital-o" style="color:var(--primary); margin-right:6px;"></i>${req.hospital_name}</h4>
            <span class="blood-badge">${req.blood_group}</span>
          </div>
          <div class="blood-card-details">
            <div class="blood-detail-item">
              <i class="fa fa-tint"></i>
              <span><strong>Blood Group:</strong> <span style="color:var(--accent-red); font-weight:700;">${req.blood_group}</span> Needed</span>
            </div>
            <div class="blood-detail-item">
              <i class="fa fa-shopping-bag"></i>
              <span><strong>Quantity:</strong> ${req.quantity} Bag(s)</span>
            </div>
            <div class="blood-detail-item">
              <i class="fa fa-calendar"></i>
              <span><strong>Required By:</strong> ${req.date} at ${req.time}</span>
            </div>
          </div>
          <p class="blood-card-description">"${req.description}"</p>
          <button class="btn-interest ${isInterested ? 'active' : ''}" onclick="toggleInterest(${req.id}, this)">
            <i class="fa ${isInterested ? 'fa-check-circle' : 'fa-heart'}"></i>
            <span>${isInterested ? 'Interested Donor Registered' : 'I am Interested'}</span>
          </button>
        `;
        feedList.appendChild(card);
      });
    }
  } catch (err) {
    console.error('Error loading blood requests:', err);
  }
}

function toggleMatchBlood(checkbox) {
  loadBloodRequests();
}

async function toggleInterest(reqId, btnElement) {
  try {
    const res = await fetch(`/server/user/interested?req_id=${reqId}&my_id=${currentUserId}`);
    const data = await res.json();

    if (data.status === 'added') {
      btnElement.classList.add('active');
      btnElement.innerHTML = '<i class="fa fa-check-circle"></i> Interested Donor Registered';
    } else {
      btnElement.classList.remove('active');
      btnElement.innerHTML = '<i class="fa fa-heart"></i> I am Interested';
    }
  } catch (err) {
    console.error('Error toggling interest:', err);
  }
}

// Search
async function search() {
  const query = document.getElementById('searchInput').value.trim();
  const dropdown = document.getElementById('searchResults');

  if (query.length < 2) {
    dropdown.style.display = 'none';
    return;
  }

  try {
    const res = await fetch(`/server/user/searchEnhanced?search=${encodeURIComponent(query)}`);
    const results = await res.json();

    if (results.length === 0) {
      dropdown.innerHTML = '<div class="search-item"><p style="padding:12px; color:#64748b; text-align:center; width:100%;">No hospitals found</p></div>';
    } else {
      dropdown.innerHTML = results.map(r => {
        const emergencyBadge = r.emergency ? `<span class="search-badge search-badge-emergency"><i class="fa fa-ambulance"></i> Emergency 24/7</span>` : '';
        const typeClass = r.type && r.type.toLowerCase() === 'public' ? 'search-badge-public' : 'search-badge-private';
        return `
          <div class="search-item" onclick="selectSearchHospital(${r.id})">
            <div class="search-item-img-wrapper">
              <img src="${r.image}" alt="${r.name}">
            </div>
            <div class="search-item-content">
              <div class="search-item-header">
                <span class="search-badge ${typeClass}">${r.type}</span>
                ${emergencyBadge}
              </div>
              <strong class="search-item-title">${r.name}</strong>
              <p class="search-item-contact"><i class="fa fa-phone" style="color:var(--primary);"></i> ${r.contact || 'N/A'}</p>
              <div class="search-item-stats">
                <span class="search-stat-badge" title="Wards"><i class="fa fa-bed"></i> ${r.ward_count} Wards</span>
                <span class="search-stat-badge" title="Doctors"><i class="fa fa-user-md"></i> ${r.doctor_count} Doctors</span>
                <span class="search-stat-badge" title="Tests"><i class="fa fa-flask"></i> ${r.test_count} Tests</span>
              </div>
              <div class="search-item-footer">
                <div class="search-item-rating">
                  <i class="fa fa-star"></i>
                  <span>${r.rating.toFixed(1)}</span>
                  <span class="review-count">(${r.review_count} reviews)</span>
                </div>
                <span class="search-view-link">View Details <i class="fa fa-chevron-right"></i></span>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }
    dropdown.style.display = 'block';
  } catch (err) {
    console.error('Error in search:', err);
  }
}

function selectSearchHospital(hosId) {
  document.getElementById('searchResults').style.display = 'none';
  document.getElementById('searchInput').value = '';
  switchNav('hospitals');
  getinfo(hosId);
}

// Profile Modal Toggle & Update
function toggleProfile() {
  const modal = document.getElementById('profileDropdown');
  modal.style.display = modal.style.display === 'none' ? 'flex' : 'none';
}

function previewProfileImage(event) {
  const reader = new FileReader();
  reader.onload = function() {
    document.getElementById('profilePreview').src = reader.result;
  };
  if (event.target.files[0]) {
    reader.readAsDataURL(event.target.files[0]);
  }
}

async function updateProfile() {
  const form = document.getElementById('profileForm');
  const formData = new FormData(form);
  formData.append('id', currentUserId);

  try {
    const res = await fetch('/server/user/updateProfile', {
      method: 'POST',
      body: formData
    });
    const result = await res.json();
    if (result.success) {
      alert('Profile updated successfully!');
      initUser();
      toggleProfile();
    }
  } catch (err) {
    console.error('Error updating profile:', err);
  }
}

function logout() {
  window.location.href = '/user/login/userLogin.html';
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}
