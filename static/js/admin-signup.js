function previewImage(event) {
  const reader = new FileReader();
  reader.onload = function() {
    const output = document.getElementById('imgPreview');
    output.src = reader.result;
  };
  if (event.target.files[0]) {
    reader.readAsDataURL(event.target.files[0]);
  }
}

async function adminSignup() {
  const form = document.getElementById('adminSignupForm');
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }

  const formData = new FormData(form);

  try {
    const response = await fetch('/admin/signup', {
      method: 'POST',
      body: formData,
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    });

    const result = await response.json();
    if (result.success) {
      document.getElementById('assignedId').innerText = '#' + result.lastInsertedID;
      document.getElementById('successModal').style.display = 'flex';
    } else {
      alert('Registration failed: ' + (result.error || 'Unknown error'));
    }
  } catch (error) {
    console.error('Admin signup error:', error);
    alert('An error occurred during registration. Please try again.');
  }
}

function goToLogin() {
  window.location.href = '/admin/login/adminLogin.html';
}
