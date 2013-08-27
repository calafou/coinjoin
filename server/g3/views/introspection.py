import sys
from g3 import app, html

################################################
# Introspection views

@app.route('/modules')
def print_modules():
    return html.pre(str(sys.modules))

@app.route('/routes')
def print_routes():
    return html.pre(str(app.url_map))


