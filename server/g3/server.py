import gevent
import signal
from gevent.pywsgi import WSGIServer
from gevent.pool import Pool

from g3 import app

def serve_forever(host, port):
    pool = Pool(5000)
    gevent.signal(signal.SIGQUIT, gevent.shutdown)
    http_server = WSGIServer((host, port), app, spawn=pool.spawn)
    http_server.serve_forever()

