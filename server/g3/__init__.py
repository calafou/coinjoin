"""

"""
import sys, os
import json
from werkzeug.utils import html
from flask import Response
#from g3.backend.mongo import db

root_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
sys.path.insert(0, os.path.join(root_dir, 'lib'))

from flask import Flask

Flask.secret_key = "foo"

app = Flask(__name__,
            template_folder=os.path.join(root_dir, 'templates'),
            static_folder=os.path.join(root_dir, 'static'))
app.debug = True
#app.jinja_env.add_extension('pyjade.ext.jinja.PyJadeExtension')

config = app.config

#from blinker import signal
#from g3.backend.mongo import db

import g3.server

def jsonify(data, status=200):
    return Response(json.dumps(data),
                    status = status,
                    mimetype = 'application/json') 


