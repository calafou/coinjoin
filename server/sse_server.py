#!/usr/bin/env python
import os, sys, json

import gevent, gevent.monkey
#gevent.monkey.patch_all()

import g3

from flask import Response
from flask import request, redirect, url_for, abort, session
from flask import render_template, jsonify
from werkzeug.utils import html

from g3 import app
from g3.roles import requires_roles
import g3.views.errors
import g3.views.introspection

import mktx

def JsonResponse(data):
    return Response(json.dumps(data),
                    status = 200,
                    mimetype = 'application/json') 


@app.route('/j/<secret>', methods=['GET'])
def coinj_get(secret):
    return Response(json.dumps({'secret': secret}),
                    status = 200,
                    mimetype = 'application/json') 

@app.route('/j/<secret>', methods=['POST'])
def coinj_get(secret):
    return Response(json.dumps({'secret': secret}),
                    status = 200,
                    mimetype = 'application/json') 

@app.route('/')
@requires_roles('admin', 'user')
def page():
    return JsonResponse({'status': "ALL SYSTEMS GO GO"})

def render_list(limit=5, offset=0):
    # 4.8 ms / request
    model = Model()
    accounts = model.query(Account).offset(offset).limit(limit)
    data = map(lambda s: s.to_dict(), accounts)
    return [data, model.query(Account).count()]

def render_list_mongo(limit=5, offset=0):
    # 1.5 ms / request
    data = map(lambda s: s, contacts.find(limit=limit, skip=offset))
    return [data, contacts.count()]

def event_stream():
    count = 0
    while True:
        gevent.sleep(2)
        yield 'data: %s\n\n' % count
        count += 1

@app.route('/sse')
def sse_request():
    return Response(
            event_stream(),
            mimetype='text/event-stream')

@app.route('/test_form')
def test_form():
    return html.form(action='/form_apply', method='POST',
                     *[html.input(name='bla', value='foo', type='text'),
                       html.input(type='submit')])
    return "<form action='/form' method='POST'><input name='bla' value='foo' type='text'><input type='submit' /></form>"

if __name__ == '__main__':
    g3.server.serve_forever('', 8001)

