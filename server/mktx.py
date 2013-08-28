import tempfile
from util import call

AMOUNT = 1000000

def first_unspent_output(address, min_amount):
    data = call("sx history %s | grep 'spend: Unspent' -B 3 | grep -v output_height | grep -v spend" % address)
    for section in data.split("--"):
        lines = [line for line in section.split("\n") if line != '']
        output = lines[0].split(":", 1)[1].strip()
        assert len(output.split(":")[0]) == 64
        value = int(lines[1].split(":", 1)[1].strip())
        if value >= min_amount:
            return output
    return None

def query_unspent_outputs(addr_list, min_amount):
    unspent = []
    for address in addr_list:
        prevout = first_unspent_output(address, min_amount)
        if prevout is None:
            return None
        unspent.append(prevout)
    assert len(unspent) == len(addr_list)
    return unspent

def mktx(input_addrs, output_addrs, amount=AMOUNT):
    tf = tempfile.NamedTemporaryFile()
    command = "sx mktx %s" % tf.name
    inputs = query_unspent_outputs(input_addrs, amount)
    if inputs is None:
        return None
    for tx_input in inputs:
        command += " --input %s" % tx_input
    for address in output_addrs:
        command += " --output %s:%s" % (address, amount)
    call(command)
    return tf.read()

if __name__ == '__main__':
    print mktx(["1PbCQ3nY87HVHnpajmnSEMtPBVayvcUrvM"], ["1DB9AzUjwcK21MhEvGbJYph3C9ki9PzWHx"])

