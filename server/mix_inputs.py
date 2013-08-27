import tempfile
from util import call

def count_inputs(txfile):
    return int(call("cat %s | sx showtx | grep Input -A 2 | grep script | wc -l" % txfile))

def extract_script(txfile, i):
    return call("cat %s | sx showtx | grep Input -A 2 | grep script | sed -n %sp | sed 's/^  script: //'" % (txfile, i + 1))

def set_input_script(txfile, i, script):
    tf = tempfile.NamedTemporaryFile()
    call("sx rawscript %s | sx set-input %s %s > %s" % (script, txfile, i, tf.name))
    call("cp %s %s" % (tf.name, txfile))

def mix(rawtx_list, template_tx):
    result_tx = tempfile.NamedTemporaryFile()
    call("echo %s > %s" % (template_tx, result_tx.name))
    for i, rawtx in enumerate(rawtx_list):
        tf = tempfile.NamedTemporaryFile()
        call("echo %s > %s" % (rawtx, tf.name))
        if count_inputs(tf.name) != len(rawtx_list):
            return None
        script = extract_script(tf.name, i)
        set_input_script(result_tx.name, i, script)
    return result_tx.read()

#print mix([call("cat /home/genjix/msig/qwss")], call("cat /home/genjix/msig/qwss"))

