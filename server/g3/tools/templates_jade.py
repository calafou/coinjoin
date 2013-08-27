from pyjade.ext.mako import preprocessor as mako_preprocessor
from mako.lookup import TemplateLookup
from mako.template import Template
import time
import os

from pbxcore.tools.templates import print_template_raw as print_raw_template
from pbxcore.config import config

mylookup = TemplateLookup(directories=[os.path.join(config['root'], 'jade'), config['root']],
                          preprocessor=mako_preprocessor)

cache = {}
do_cache = False

def print_template(name, variables, jade_variables):
    tpl_root = config['root']
    dest_file = os.path.join('jade', name + '.jade')
    if do_cache and dest_file in cache:
        rendered = cache[dest_file]
        return str(print_raw_template(rendered, variables))
    t = Template(filename=dest_file,
         preprocessor=mako_preprocessor,
         lookup=mylookup)

    rendered = t.render(**jade_variables)
    cache[dest_file] = rendered
    
    return str(print_raw_template(rendered, variables))

