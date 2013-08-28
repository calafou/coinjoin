import sys
import hashlib
import subprocess
from PyQt4 import Qt, QtCore
from PyQt4.QtGui import *
from urllib2 import urlopen
from urllib import urlencode
from decimal import Decimal
import json
import time
import socket

TOR_PASSWORD = 'yourpassword'

MAX_FEE = 100000 # 0.001
DEFAULT_AMOUNT = '0.01' # can be overriden through command line

def add_fee(amount):
    fee = amount / 100
    if fee > MAX_FEE:
        fee = MAX_FEE
    return amount + fee

def parse_amount(amount):
    return int(Decimal(amount)*Decimal('100000000'))

def restart_tor_connection(password, host='127.0.0.1', port=9051):
    """
    Instruct tor to establish a new circuit
    """
    # can't do it from within torify..
    return
    sock = socket.socket()
    sock.connect((host, port))

    password = password.encode('hex')

    sock.send('AUTHENTICATE %s\r\n' % (password,))

    res = sock.recv(1024)
    code, text = res.split(' ', 1)
    if not code == '250':
        raise Exception('Could not authenticate tor control connection. Check README for configuration details.')

    sock.send('signal NEWNYM\r\n')
    res, text = sock.recv(1024).split(' ', 1)
    if not code == '250':
        raise Exception('Could not reset tor circuit')


class WorkThread(QtCore.QThread):
  def __init__(self, url, output_addr, wallet, amount):
        QtCore.QThread.__init__(self)
        self._url = url
        self._amount = amount
        self._output_addr = output_addr
        self._input_addr = wallet.address()
        self._wallet = wallet

  def emit_status(self, text):
        self.emit( QtCore.SIGNAL('status(QString)'), text )

  def emit_amount(self, amount):
        self.emit( QtCore.SIGNAL('amount(QString)'), str(amount) )

  def run(self):
        # Begin stage 1
        amount = self._amount
        interface = ServerInterface(str(self._url), self.emit_status, self._amount)

        self.emit_status('Stage: Disco')
        data = interface.stage1()
        curr_state = data['status']
        self.emit_amount(amount)
        self.emit_status('Entering room (%s)' % curr_state)

        # Send output address
        if curr_state == 'outputs':
            self.emit_status('Stage: Outputs')
            interface.send_output_address(self._output_addr)

	    restart_tor_connection(TOR_PASSWORD)

            data = interface.wait_for_outputs()
            curr_state = data['status']

	restart_tor_connection(TOR_PASSWORD)

        # Begin stage 2
	if curr_state == 'inputs':
            self.emit_status('Stage: Inputs')
            interface.stage2()
            interface.send_input_address(self._input_addr)

        # Now get the transaction for signing
        unsigned_tx, input_index = interface.wait_for_tx()

        # Save tx to file.
        self.emit_status('Stage: save tx')
        tx = Transaction(unsigned_tx)
        # Check our output is in the outputs list.
        if not tx.contains(self._output_addr):
            self.emit_status('Tx missing')
            raise Exception("Our output address is missing from the server's transaction!")
        # Check the outputs are for AMOUNT BTC.
        if not tx.outputs_all_equal(amount):
            self.emit_status('Outs dont equal')
            raise Exception("Some outputs don't equal %.4f BTC." % (AMOUNT/100000000))

        if curr_state != 'final':
            self.emit_status('Stage: Signing')
            # Sign tx input.
            tx.sign_input(self._wallet.filename, input_index)
            # Read back data and send to server.
            interface.send_tx(tx.signed_tx_data())


        self.emit_status('Stage: Final')
        data = interface.wait_for_signed_inputs()

        final_tx = data['final-transaction']
        self.emit_status('Done')

        self.emit( QtCore.SIGNAL('finished(QString)'), final_tx )

def call(command):
    return subprocess.check_output(command, shell=True).rstrip("\n")

class Wallet:

    def __init__(self, filename):
        try:
            with open(filename): pass
        except IOError:
            call("sx newkey > " + filename)
        self.filename = filename

    def address(self):
        return call("cat %s | sx addr" % self.filename)

class ServerInterface:

    def __init__(self, url, emit, amount):
        self._url = url
        self._emit = emit
        self._amount = amount

    def throw_error(self, message):
        self._emit(message)
        raise Exception(message)

    # Utility functions
    def send(self, data=None):
        if data: 
            data = urlencode(data)
	res = urlopen(self._url, data)
        res = json.loads(res.read())
        if data and res['status'] == -1:
            if 'error' in res:
                self.throw_error(res['error'])
            else:
                self.throw_error("Could not send %s. Review your address." % str(data))
        return res

    def wait_for(self, next_state, what):
        data = self.send()
        while not data['status'] in next_state:
            if data['status'] == 'error':
                self._emit("Error on server: %s" % data['error'])
            else:
                self._emit("wait for %s %s/%s" % (what, data[what], data['target']))
            time.sleep(4)
            data = self.send()
        return data

    def check_state(self, state):
        data = self.send()
        if not data['status'] == state:
            self.throw_error("Group is not in %s stage!" % (state,))
        return data

    # Stages
    def stage1(self):
        #data = self.check_state('outputs')
        data = self.send()
        room_amount = parse_amount(data['amount'])
        if not room_amount == self._amount:
            self.throw_error("Amounts don't match %d != %d" % (room_amount, self._amount))
        return data

    def send_output_address(self, address):
        data = self.send({'output': address})

    def wait_for_outputs(self):
        return self.wait_for(['inputs'], 'outputs')

    def wait_for_inputs(self):
        return self.wait_for(['signatures', 'final'], 'inputs')

    def stage2(self):
        self.check_state('inputs')

    def send_input_address(self, address):
        data = self.send({'input': address})
        self._client_index = data['status']

    def wait_for_tx(self):
        data = self.wait_for_inputs()
        if not 'transaction' in data:
            self.throw_error('Server sent no transaction to sign!!')
        tx = data['transaction']
        idx = self._client_index
        # Returns (tx, input_index)
        return (tx, idx)

    def send_tx(self, tx):
        data = self.send({'sig': tx, 'sig_idx': self._client_index})

    def wait_for_signed_inputs(self):
        return self.wait_for(['final'], 'signatures')

class Transaction:

    def __init__(self, rawtx):
        open("txfile.tx", "w").write(rawtx)

    def contains(self, address):
        output_addrs = call("cat txfile.tx | sx showtx | grep Output -A 3 | grep address")
        return str(address) in output_addrs

    def outputs_all_equal(self, value):
        unmatched = call("cat txfile.tx | sx showtx | grep value | grep -v %s | wc -l" % value)
        return unmatched == "0"

    def sign_input(self, privkey, input_index):
        print "Signing transaction input..."
        decoded_addr = call("cat %s | sx addr | sx decode-addr" % privkey)
        print "Decoded address:", decoded_addr
        prevout_script = call("sx rawscript dup hash160 [ %s ] equalverify checksig" % decoded_addr)
        print "Previous output script:", prevout_script
        signature = call("cat %s | sx sign-input txfile.tx %s %s" % (privkey, input_index, prevout_script))
        print "Signature:", signature
        pubkey = call("cat %s | sx pubkey" % privkey)
        print "Public key:", pubkey
        call("sx rawscript [ %s ] [ %s ] | sx set-input txfile.tx %s > signed-tx" % (signature, pubkey, input_index))
        print "Signed."

    def signed_tx_data(self):
        return open("signed-tx").read()

class MainWindow(QWidget):

    def __init__(self, wallet, url, output_address, amount):
        super(MainWindow, self).__init__()
        self.wallet = wallet
        self.amount = parse_amount(amount)

        self.resize(500, 240)
        self.setWindowTitle("Mixing")
        grid = QGridLayout(self)
        grid.setSpacing(2)
        # Top row
        amount_str = "%.5f" % (add_fee(self.amount)/100000000.0)
        self.send_w = QLabel("Send %s BTC to:" % amount_str)
        grid.addWidget(self.send_w, 0, 0)
        addr_display = QLineEdit(self.wallet.address(), self)
        addr_display.setReadOnly(True)
        grid.addWidget(addr_display, 0, 1)
        # URL row
        grid.addWidget(QLabel("Paste URL here:"), 1, 0)
        self.user_url = QLineEdit(url)
        grid.addWidget(self.user_url, 1, 1)
        # Output address row
        grid.addWidget(QLabel("Output address:"), 2, 0)
        self.user_output = QLineEdit(output_address)
        grid.addWidget(self.user_output, 2, 1)
        # Submit data to server.
        self.anonymize_button = QPushButton("Anonymize!")
        self.connect(self.anonymize_button, Qt.SIGNAL("clicked()"),
                     self.anonymize)
        grid.addWidget(self.anonymize_button, 3, 1)
        self.status = QStatusBar(self)
        grid.addWidget(self.status, 4, 0, 1, 2)
        self.show()

    def anonymize(self):
        self.anonymize_button.setEnabled(False)
        # test restarting tor connection before doing anything
        try:
	    restart_tor_connection(TOR_PASSWORD)
            self.perform_operation()
        except Exception as e:
            self.finish(e.message)
            raise

    def hash_transaction(self, tx):
        tx = str(tx).strip()
        return hashlib.sha256(hashlib.sha256(tx.decode("hex")).digest()).digest()[::-1].encode("hex")

    def operation_finished(self, transaction):
        transaction_hash = self.hash_transaction(transaction)
        print "Transaction:"
        print transaction
        print "Transaction hash:"
        print transaction_hash
        self.finish("Anonymized: "+transaction_hash)
 
    def from_interface(self, message):
        self.status.showMessage(message)
 
    def got_amount(self, amount):
        self.status.showMessage('Locked amount: ' + amount)
 
    def perform_operation(self):
        url = self.user_url.text()
        output_addr = self.user_output.text()
        self.workThread = WorkThread(str(url), str(output_addr), self.wallet, self.amount)
        self.connect( self.workThread, QtCore.SIGNAL("status(QString)"), self.from_interface )
        self.connect( self.workThread, QtCore.SIGNAL("finished(QString)"), self.operation_finished )
        self.connect( self.workThread, QtCore.SIGNAL("amount(QString)"), self.got_amount )
        self.workThread.start()

    def finish(self, message):
        QMessageBox.information(self, "Mixing Result", message)
        QApplication.quit()

def main():
    amount = DEFAULT_AMOUNT
    if len(sys.argv) >= 2:
        amount = sys.argv[1]
    private_key = 'private.key'
    if len(sys.argv) >= 3:
        private_key = sys.argv[2]
    url = ""
    if len(sys.argv) >= 4:
        url = sys.argv[3]
    output_address = ""
    if len(sys.argv) >= 5:
        output_address = sys.argv[4]
    app = QApplication([])
    wallet = Wallet(private_key)
    window = MainWindow(wallet, url, output_address, amount)
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())


