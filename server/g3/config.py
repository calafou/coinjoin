import os
import sys
import json

rundir = os.path.dirname(os.path.realpath(sys.argv[0]))

if os.path.exists('config.json'):
    config_file = 'config.json'
elif os.path.exists(os.path.join(rundir, 'config.json')):
    config_file = os.path.join(rundir, 'config.json')
else:
    config_file = '/etc/pbxcore/config.json'

with open(config_file) as f:
    config = json.load(f)

config['root'] = rundir
def clean_dict(adict):
    for key in adict.keys():
        value = adict[key]
        if value.__class__ == dict:
            clean_dict(value)
        else:
            value = str(value)
        del adict[key]
        adict[str(key)] = value

clean_dict(config)
config['rundir'] = rundir
