/*
login.js

Handles login form submission by:
1. Extracting username and password from the .login-form.
2. Hashing the password using SHA-256 (crypto.subtle).
3. Sending username and hashed password to the backend via POST.
*/

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
    // Hash password with SHA-256
    const encoder = new TextEncoder();
    const data = encoder.encode(password);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

    // Send to backend
    fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password: hashHex })
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
