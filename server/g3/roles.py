from flask import request, redirect, url_for, abort, session
from functools import wraps
import urllib

def get_current_user_role():
    #print urllib.unquote(request.cookies['connect.sid'])
    #print request.cookies
    if 'session' in request.cookies:
        print urllib.unquote(request.cookies['session'])
    if not session.permanent:
        session.permanent = True
        session['mydata'] = 'foo'
    #print session.new, session.modified, session.permanent
    return 'user'

def requires_roles(*roles):
    def wrapper(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if get_current_user_role() not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapped
    return wrapper


