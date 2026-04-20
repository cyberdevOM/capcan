/*
login-register.js

Handles form submission for both the login and register pages.

Login:
1. Extracts username and password from .login-form.
2. Hashes the password with bcrypt using the fixed application salt (matching
   CLIENT_BCRYPT_SALT in encryptors.py) before sending to the backend.
3. The backend verifies the received hash against its stored bcrypt hash.

Register:
1. Validates all fields client-side (required, email format, password match).
2. Hashes the password with the same fixed client-side bcrypt salt.
3. POSTs { username, email, password } to /api/register.
4. Redirects to /login on success.
*/

// Must match CLIENT_BCRYPT_SALT in src/server/utils/encryptors.py
const CLIENT_BCRYPT_SALT = '$2a$10$j/gmYAk9AYTEYpeiiIYueu';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('.login-form');
  if (!form) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    const username = formData.get('username');
    const password = formData.get('password');
    if (!username || !password) {
      alert('Please enter both username and password.');
      return;
    }

    // Hash with the fixed application salt — same result as pre_hash_client_password() on the backend
    const clientHash = await dcodeIO.bcrypt.hash(password, CLIENT_BCRYPT_SALT);

    fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password: clientHash })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        window.location.href = '/dashboard';
      } else {
        alert('Login failed: ' + (data.message || 'Invalid credentials'));
      }
    })
    .catch(() => alert('Network error.'));
  });
});

// ─── Registration handler ────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('register-form');
  if (!form) return;

  function showError(id, msg) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = msg;
    el.style.display = msg ? 'block' : 'none';
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    let valid = true;

    const username = document.getElementById('reg-username').value.trim();
    const email    = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;
    const confirm  = document.getElementById('reg-confirm').value;

    showError('username-error', '');
    showError('email-error', '');
    showError('password-error', '');
    showError('confirm-error', '');

    if (!username) {
      showError('username-error', 'Username is required.');
      valid = false;
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email) {
      showError('email-error', 'Email is required.');
      valid = false;
    } else if (!emailPattern.test(email)) {
      showError('email-error', 'Please enter a valid email address.');
      valid = false;
    }

    if (!password) {
      showError('password-error', 'Password is required.');
      valid = false;
    }

    if (!confirm) {
      showError('confirm-error', 'Please confirm your password.');
      valid = false;
    } else if (password && password !== confirm) {
      showError('confirm-error', 'Passwords do not match.');
      valid = false;
    }

    if (!valid) return;

    const clientHash = await dcodeIO.bcrypt.hash(password, CLIENT_BCRYPT_SALT);

    fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password: clientHash })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        window.location.href = '/login';
      } else {
        alert('Registration failed: ' + (data.message || 'Unknown error'));
      }
    })
    .catch(() => alert('Network error.'));
  });
});
