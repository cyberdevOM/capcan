/*
login.js

Handles login form submission by:
1. Extracting username and password from the .login-form.
2. Hashing the password with bcrypt using the fixed application salt (matching
   the CLIENT_BCRYPT_SALT in encryptors.py) before sending to the backend.
3. The backend then verifies the received hash against its own stored bcrypt hash.
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
