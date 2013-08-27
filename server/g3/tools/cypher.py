"""
Checking gpg signatures
"""

import time
from pyme import core, constants, errors, pygpgme
from pyme.constants.sig import mode

def sign_text(text, key_uid):
    ciphertext = core.Data()
    plaintext = core.Data(text)
  
    ctx = core.Context()
  
    ctx.set_armor(1)
    #ctx.set_passphrase_cb(_passphrase_callback)
  
    ctx.op_keylist_start(key_uid, 0)
    sigkey = ctx.op_keylist_next()
    # print sigkey.uids[0].uid
  
    ctx.signers_clear()
    ctx.signers_add(sigkey)
  
    ctx.op_sign(plaintext, ciphertext, mode.NORMAL)
  
    ciphertext.seek(0, 0)
    signature = ciphertext.read()
  
    return signature

def check_signature(text, fingerprint):
    gpg = core.Context()
    plaintext = core.Data()
    signed = core.Data(text)
    try:
        res = gpg.op_verify(signed, None, plaintext)
    except errors.GPGMEError:
        # incorrect data
        return False
        
    plaintext.seek(0,0)
    result_data = plaintext.read()

    res = gpg.op_verify_result()

    s = res.signatures[0]

    if s.fpr == fingerprint:
        return result_data, s.timestamp
    else:
        print 'invalid fingerprint', s.fpr
        return False


if __name__ == '__main__':
	import json
	import urllib
	import urllib2
	a = """-----BEGIN PGP MESSAGE-----
	Version: GnuPG v1.4.11 (GNU/Linux)
	owGbwMvMwCS4LMb4pltgRhbjad4khsCy2qlJOYlAxNXhxsIgyMTAxsoEEmTg4hSA
	qVz7hmHB3q2f1r1u0jRQ2rve9OTPqUtLFwksZpjD8y/uQfu5r5YX++S/sigd1vob
	KfsUAA==
	=b3hQ
	-----END PGP MESSAGE-----"""

	b = """-----BEGIN PGP MESSAGE-----
	Version: GnuPG v1.4.11 (GNU/Linux)

	owGbwMvMwCS4LMb4pltgRhbjad4khsCyprq0/PykxCKuDjcWBkEmBjZWJpAgAxen
	AEzl7jUMC867RaeH1PMmlU5udzq6UqTjqcy5FQxzuO2XfO4/8T3zq/mZ9EXOs55f
	YrRiBwA=
	=k4rw
	-----END PGP MESSAGE-----"""

	c = """-----BEGIN PGP MESSAGE-----
	Version: GnuPG v1.4.11 (GNU/Linux)

	wGbwMvMwCS4LMb4pltgRhbjad4khsCyprq0/PykxCKuDjcWBkEmBjZWJpAgAxen
	AEzl7jUMC867RaeH1PMmlU5udzq6UqTjqcy5FQxzuO2XfO4/8T3zq/mZ9EXOs55f
	YrRiBwA=
	=k4rw
	-----END PGP MESSAGE-----"""


	check_signature(a, '1090129F33ADC66CA2871654A65C33D94651686A')
	check_signature(b, '1090129F33ADC66CA2871654A65C33D94651686A')
	check_signature(c, '1090129F33ADC66CA2871654A65C33D94651686A')

	args = {'timestamp': time.time(),
                'balance': 1600000000,
                'balance2': 1600000000,
                'address': "1KhD1wqQKDz4SbviDjQEJXLG4pHqEXtcVx"}
	data = json.dumps(args)
	signed = sign_text(data, 'A548D8E2')
	print signed
	result = check_signature(signed, '93823B77B658562DFFFBC11FA44C3DD3A548D8E2')
	if result:
		result_data, timestamp = result
		print result_data

	url = 'http://localhost:8080/privateapi/update_balance'
	args = urllib.urlencode({'data': signed})
	req = urllib2.Request(url, args)
	f = urllib2.urlopen(req)
	response = f.read()
	f.close()
	print response
