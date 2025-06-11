from flask import Flask, render_template, url_for

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def Dashboard():
    return render_template('Capcan-html-home.html')

@app.route('/clients')
def Clients():
    # example client list data
    client_list = [
        {"id": "deb_1985111", "platform": "deb", "status": "online"},
        {"id": "win_1192511", "platform": "win", "status": "online"},
        {"id": "rpm_1134611", "platform": "mac", "status": "offline"},
    ]
    return render_template('Capcan-html-clients.html', clients=client_list)

@app.route('/settings')
def Settings():
    return render_template('Capcan-html-settings.html')

if __name__ == '__main__':
    app.run(debug=True)