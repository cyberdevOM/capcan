// Must match CLIENT_BCRYPT_SALT in src/server/utils/encryptors.py
const SETTINGS_BCRYPT_SALT = '$2a$10$j/gmYAk9AYTEYpeiiIYueu';

// ── User role save ────────────────────────────────────────────────────────────

function saveUserRole(userId) {
    const select = document.getElementById('role-select-' + userId);
    const feedback = document.getElementById('role-feedback-' + userId);
    const role = select.value;

    fetch(`/api/v1/users/${userId}/role`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ role })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            const badge = document.getElementById('role-badge-' + userId);
            if (badge) {
                badge.className = `role-badge role-${role.replace('-', '')}`;
                badge.textContent = role;
            }
            showRoleFeedback(feedback, 'Saved', true);
        } else {
            showRoleFeedback(feedback, data.message || 'Failed', false);
        }
    })
    .catch(() => showRoleFeedback(feedback, 'Error', false));
}

function showRoleFeedback(el, msg, success) {
    if (!el) return;
    el.textContent = msg;
    el.className = 'user-role-feedback ' + (success ? 'feedback-ok' : 'feedback-err');
    clearTimeout(el.dismiss_timer);
    el.dismiss_timer = setTimeout(() => { el.textContent = ''; el.className = 'user-role-feedback'; }, 3000);
}

// ── Add User modal ────────────────────────────────────────────────────────────

function openAddUserModal() {
    reset_add_user_modal();
    document.getElementById('addUserModal').classList.add('active');
    document.getElementById('modal-username').focus();
}

function closeAddUserModal() {
    document.getElementById('addUserModal').classList.remove('active');
}

function handleAddUserOverlayClick(e) {
    if (e.target === document.getElementById('addUserModal')) closeAddUserModal();
}

function reset_add_user_modal() {
    ['modal-username', 'modal-email', 'modal-password', 'modal-confirm'].forEach(id => {
        document.getElementById(id).value = '';
    });
    document.getElementById('modal-role').value = 'read-only';
    ['modal-username-error', 'modal-email-error', 'modal-password-error', 'modal-confirm-error'].forEach(id => {
        modal_field_error(id, '');
    });
    document.getElementById('modal-feedback').textContent = '';
    document.getElementById('addUserSubmitBtn').disabled = false;
}

function modal_field_error(id, msg) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = msg;
    el.style.display = msg ? 'block' : 'none';
}

async function submitAddUser() {
    const username = document.getElementById('modal-username').value.trim();
    const email    = document.getElementById('modal-email').value.trim();
    const password = document.getElementById('modal-password').value;
    const confirm  = document.getElementById('modal-confirm').value;
    const role     = document.getElementById('modal-role').value;

    let valid = true;
    modal_field_error('modal-username-error', '');
    modal_field_error('modal-email-error', '');
    modal_field_error('modal-password-error', '');
    modal_field_error('modal-confirm-error', '');

    if (!username) {
        modal_field_error('modal-username-error', 'Username is required.');
        valid = false;
    }

    const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!email) {
        modal_field_error('modal-email-error', 'Email is required.');
        valid = false;
    } else if (!emailPattern.test(email)) {
        modal_field_error('modal-email-error', 'Please enter a valid email address.');
        valid = false;
    }

    if (!password) {
        modal_field_error('modal-password-error', 'Password is required.');
        valid = false;
    }

    if (!confirm) {
        modal_field_error('modal-confirm-error', 'Please confirm your password.');
        valid = false;
    } else if (password && password !== confirm) {
        modal_field_error('modal-confirm-error', 'Passwords do not match.');
        valid = false;
    }

    if (!valid) return;

    const btn = document.getElementById('addUserSubmitBtn');
    btn.disabled = true;

    const clientHash = await dcodeIO.bcrypt.hash(password, SETTINGS_BCRYPT_SALT);

    fetch('/api/v1/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password: clientHash, role })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            closeAddUserModal();
            window.location.reload();
        } else {
            const fb = document.getElementById('modal-feedback');
            fb.textContent = data.message || 'Failed to create user.';
            fb.className = 'modal-feedback modal-feedback-err';
            btn.disabled = false;
        }
    })
    .catch(() => {
        const fb = document.getElementById('modal-feedback');
        fb.textContent = 'Network error. Please try again.';
        fb.className = 'modal-feedback modal-feedback-err';
        btn.disabled = false;
    });
}

// Show/hide password toggles inside the modal
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.modal-toggle-pw').forEach(btn => {
        btn.addEventListener('click', () => {
            const input = document.getElementById(btn.dataset.target);
            if (!input) return;
            const show = input.type === 'password';
            input.type = show ? 'text' : 'password';
            btn.querySelector('i').className = show ? 'fas fa-eye-slash' : 'fas fa-eye';
        });
    });

    // Close modal on Escape key
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') closeAddUserModal();
    });
});
