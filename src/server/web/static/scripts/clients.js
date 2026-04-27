let _activeClientId = null;
let _activeClientName = null;

// ── Client selection ──────────────────────────────────────────
function selectClient(clientId) {
    _activeClientId = clientId;
    _activeClientName = document.querySelector(`.client-item[data-client-id="${clientId}"] .client-id`)?.textContent || clientId;
    document.getElementById('deleteClientBtn').disabled = false;

    fetch(`/clients?client_id=${clientId}`, {headers: {'X-Requested-With': 'XMLHttpRequest'}})
        .then(r => r.text())
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newDetails = doc.getElementById('clientDetails');
            if (newDetails) document.getElementById('clientDetails').innerHTML = newDetails.innerHTML;
        });
    document.querySelectorAll('.client-item').forEach(el =>
        el.classList.toggle('active', el.dataset.clientId === clientId));
}

function connectClient(clientId) {
    console.log(`Connecting to client ${clientId}`);
}

function openFileManager(clientId) {
    console.log(`Opening file manager for client ${clientId}`);
}

function openTerminal(clientId) {
    console.log(`Opening terminal for client ${clientId}`);
}

function showLogs(clientId) {
    console.log(`Showing logs for client ${clientId}`);
}

function disconnectClient(clientId) {
    console.log(`Disconnecting client ${clientId}`);
}

// ── Multi-select ──────────────────────────────────────────────
function toggleSelectAll(cb) {
    document.querySelectorAll('.client-select').forEach(el => { el.checked = cb.checked; });
    onClientCheckboxChange();
}

function onClientCheckboxChange() {
    const selected = getSelectedClientIds();
    const masterCb = document.getElementById('select-all-clients');
    const all = document.querySelectorAll('.client-select');
    if (masterCb) masterCb.indeterminate = selected.length > 0 && selected.length < all.length;
    document.querySelectorAll('.btn-configure-selected').forEach(btn => {
        btn.style.opacity = selected.length > 0 ? '1' : '0.5';
    });
}

function getSelectedClientIds() {
    return Array.from(document.querySelectorAll('.client-select:checked')).map(el => el.value);
}

// ── Config push ───────────────────────────────────────────────
function _readConfigForm(clientId) {
    const interval = parseInt(document.getElementById(`cfg-interval-${clientId}`)?.value || '300', 10);
    const keys = ['cpu', 'memory', 'disk', 'network', 'processes'];
    const collect = {};
    keys.forEach(k => {
        const el = document.getElementById(`cfg-${k}-${clientId}`);
        collect[k] = el ? el.checked : true;
    });
    return { interval, collect };
}

function pushConfig(clientIds, formSourceId) {
    const settings = _readConfigForm(formSourceId);
    const statusEl = document.getElementById(`cfg-status-${formSourceId}`);

    fetch('/api/clients/config', {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ client_ids: clientIds, settings })
    })
    .then(r => r.json())
    .then(data => {
        if (statusEl) {
            statusEl.textContent = data.message || JSON.stringify(data);
            statusEl.className = 'config-status success';
            setTimeout(() => { statusEl.textContent = ''; statusEl.className = 'config-status'; }, 4000);
        }
    })
    .catch(err => {
        if (statusEl) {
            statusEl.textContent = 'Error: ' + err.message;
            statusEl.className = 'config-status error';
        }
    });
}

function pushConfigToSelected(formSourceId) {
    const ids = getSelectedClientIds();
    if (ids.length === 0) { alert('No clients selected. Use the checkboxes in the list.'); return; }
    pushConfig(ids, formSourceId);
}

function openBulkConfig() {
    const ids = getSelectedClientIds();
    if (ids.length === 0) { alert('Select at least one client first.'); return; }
    const activeItem = document.querySelector('.client-item.active');
    if (activeItem) {
        pushConfigToSelected(activeItem.dataset.clientId);
    } else {
        alert(`${ids.length} client(s) selected. Open a client to configure, then click "Apply to all selected".`);
    }
}

function toggleFilter() {}

// ── Add Client Modal ──────────────────────────────────────────
function openAddClientModal() {
    document.getElementById('addUsername').value = '';
    document.getElementById('addIpAddress').value = '';
    document.getElementById('addPassword').value = '';
    document.getElementById('addClientError').textContent = '';
    _setAddLoading(false);
    document.getElementById('addClientModal').classList.add('active');
    document.getElementById('addUsername').focus();
}

function closeAddClientModal() {
    if (document.getElementById('addSubmitBtn').disabled) return;
    document.getElementById('addClientModal').classList.remove('active');
}

function _setAddLoading(loading) {
    document.getElementById('addSubmitBtn').disabled = loading;
    document.getElementById('addCancelBtn').disabled = loading;
    document.getElementById('addBtnLabel').style.display = loading ? 'none' : '';
    document.getElementById('addBtnSpinner').style.display = loading ? '' : 'none';
}

function submitAddClient() {
    const username = document.getElementById('addUsername').value.trim();
    const ip_address = document.getElementById('addIpAddress').value.trim();
    const password = document.getElementById('addPassword').value;
    const errorEl = document.getElementById('addClientError');

    if (!username) { errorEl.textContent = 'Username is required.'; return; }
    if (!ip_address) { errorEl.textContent = 'Client IP is required.'; return; }
    if (!password) { errorEl.textContent = 'Password is required.'; return; }
    errorEl.textContent = '';
    _setAddLoading(true);

    fetch('/api/clients/admin/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ username, ip_address, password })
    })
    .then(r => r.json())
    .then(data => {
        _setAddLoading(false);
        if (data.error) { errorEl.textContent = data.error; return; }
        location.reload();
    })
    .catch(err => {
        _setAddLoading(false);
        errorEl.textContent = 'Error: ' + err.message;
    });
}

// ── Delete Client Modal ───────────────────────────────────────
function openDeleteClientModal() {
    if (!_activeClientId) return;
    document.getElementById('deleteClientMsg').textContent =
        `Are you sure you want to delete client "${_activeClientName}"? This will SSH into the machine and uninstall the service.`;
    document.getElementById('deletePassword').value = '';
    document.getElementById('deleteClientError').textContent = '';
    _setDeleteLoading(false);
    document.getElementById('deleteClientModal').classList.add('active');
    document.getElementById('deletePassword').focus();
}

function closeDeleteClientModal() {
    if (document.getElementById('deleteSubmitBtn').disabled) return;
    document.getElementById('deleteClientModal').classList.remove('active');
}

function _setDeleteLoading(loading) {
    document.getElementById('deleteSubmitBtn').disabled = loading;
    document.getElementById('deleteCancelBtn').disabled = loading;
    document.getElementById('deleteBtnLabel').style.display = loading ? 'none' : '';
    document.getElementById('deleteBtnSpinner').style.display = loading ? '' : 'none';
}

function confirmDeleteClient() {
    if (!_activeClientId) return;
    const password = document.getElementById('deletePassword').value;
    const errorEl = document.getElementById('deleteClientError');

    if (!password) { errorEl.textContent = 'Password is required.'; return; }
    errorEl.textContent = '';
    _setDeleteLoading(true);

    fetch(`/api/clients/admin/${_activeClientId}`, {
        method: 'DELETE',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ password })
    })
    .then(r => r.json())
    .then(data => {
        _setDeleteLoading(false);
        if (data.error) { errorEl.textContent = data.error; return; }
        closeDeleteClientModal();
        location.reload();
    })
    .catch(err => {
        _setDeleteLoading(false);
        errorEl.textContent = 'Delete failed: ' + err.message;
    });
}

// ── Event listeners (deferred until DOM is ready) ─────────────
document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('clientSearch')?.addEventListener('input', function () {
        const q = this.value.toLowerCase();
        document.querySelectorAll('.client-item').forEach(el => {
            const text = el.querySelector('.client-id')?.textContent.toLowerCase() || '';
            el.style.display = text.includes(q) ? '' : 'none';
        });
    });

    document.getElementById('addClientModal')?.addEventListener('click', function (e) {
        if (e.target === this) closeAddClientModal();
    });

    document.getElementById('deleteClientModal')?.addEventListener('click', function (e) {
        if (e.target === this) closeDeleteClientModal();
    });
});
