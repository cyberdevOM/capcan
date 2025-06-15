from flask import Flask, render_template, url_for 
from templates.pre_renders.dashboard_prerender import export_client_list, render_quickstats

app = Flask(__name__, static_folder='static', template_folder='templates')

@app.route('/')
def Dashboard():
    quickstats_html = render_quickstats()
    return render_template(
        'Capcan-html-home.html',
        quickstats_html=quickstats_html,
    )

@app.route('/clients')
def Clients():
    return render_template(
        'Capcan-html-clients.html', 
        clients=export_client_list()
    )

@app.route('/settings')
def Settings():
    return render_template('Capcan-html-settings.html')

# if __name__ == '__main__':
    # app.run(debug=True)