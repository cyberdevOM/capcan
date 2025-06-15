from flask import render_template
from markupsafe import Markup

# shared client list data
# This would typically be fetched from a database or an API in a real application
client_list = [
    {"id": "deb_1985111", "platform": "deb", "status": "online"},
    {"id": "win_1192511", "platform": "win", "status": "online"},
    {"id": "rpm_1134611", "platform": "mac", "status": "offline"},
]

def export_client_list():
    return client_list

def render_quickstats():
    total = len(client_list)
    online = sum(1 for c in client_list if c['status'] == 'online')
    offline = total - online
    # Render the quick stats HTML
    html = f"""
    <ul class="quickstats-list">
        <li><strong>Total Clients:</strong> {total}</li>
        <li style='#27ae60;'><strong>Online Clients:</strong> {online}</li>
        <li style='#c0392b;'><strong>Offline Clients:</strong> {offline}</li>
    </ul>
    """
    return Markup(html)