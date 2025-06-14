from flask import Flask, render_template, url_for

app = Flask(__name__, static_folder='static', template_folder='templates')

# shared client list data
# This would typically be fetched from a database or an API in a real application
client_list = [
        {"id": "deb_1985111", "platform": "deb", "status": "online"},
        {"id": "win_1192511", "platform": "win", "status": "online"},
        {"id": "rpm_1134611", "platform": "mac", "status": "offline"},
    ]

@app.route('/')
def Dashboard():
    total = len(client_list)
    online = sum(1 for c in client_list if c['status'] == 'online')
    offline = total - online
    return render_template(
        'Capcan-html-home.html',
        total_clients=total,
        online_clients=online,
        offline_clients=offline,
    )

@app.route('/clients')
def Clients():
    return render_template(
        'Capcan-html-clients.html', 
        clients=client_list
    )

@app.route('/settings')
def Settings():
    return render_template('Capcan-html-settings.html')

# if __name__ == '__main__':
    # app.run(debug=True)