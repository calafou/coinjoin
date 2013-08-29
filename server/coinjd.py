#!/usr/bin/env python
import re
import random
from decimal import Decimal

from flask import request
from g3 import app, jsonify, server

import mktx
import mix_inputs
import util


##################################
# Memory of ongoing transactions

transactions = {}

def is_public_tx(tx_key):
    # consider public if secret starts with 'public' and is still
    # gathering participants
    transaction = transactions[tx_key]
    if tx_key.startswith('public') and transaction.status == 'outputs':
        return True

def get_public_tx():
    return filter(is_public_tx, transactions.keys())


##################################
# Simple CoinJoin Mechanism

class SimpleCoinJoin(object):
    def __init__(self, nparticipants, amount):
        self._nparticipants = nparticipants
        self._tx = None
        self._amount = amount
        self._error = None
        self._final_tx = None
        self._sets = ['outputs', 'inputs', 'signatures']
        self.messages = set()
        self.outputs = list()
        self.inputs = list()
        self.signatures = list()

        self.status = self._sets[0]

    def add_message(self, text):
        """Add a short message to this join

        Args:
           text: the text to show
        """
        if len(text) < 128:
            self.messages.add(text)

    def enter_final_stage(self):
        """
         Enter the final stage
        """
        signed = [""]*self._nparticipants
        for sig in self.signatures:
            signed[sig[0]] = str(sig[1]).strip()
        res = mix_inputs.mix(signed, self._tx)
        self._final_tx = res.strip()
        print "--- FINAL TX -----"
        print self._final_tx
        print "------------------"
        util.call('echo %s | sx ob-broadcast-tx -' % self._final_tx)
        util.call('echo %s | sx bci-pushtx -' % self._final_tx)

    def enter_signing_stage(self):
        """
         Enter the signing stage
        """
        # shuffle outputs on state changes
        # its also randomized by network jitter
        random.shuffle(self.outputs)

        # generate the transaction so clients can sign it
        amount = util.parse_amount(self._amount)
        res = mktx.mktx(list(self.inputs), self.outputs, amount)
        if not res:
            self._error = 'Could not create transaction'
            return
        self._tx = res

    def next_state(self, curr_state):
        """
         Go to next state

        Args:
           curr_state: current state name
        """
        curr_idx = self._sets.index(curr_state)
        if curr_idx == len(self._sets)-1:
            self.enter_final_stage()
            return 'final'
        else:
            state = self._sets[curr_idx+1]
            # if entering signing stage generate the transaction
            if state == 'signatures':
                self.enter_signing_stage()
            return state

    def add_input(self, data):
        if self.status == 'outputs':
            return -1
        dest_set = self.inputs
        if len(dest_set) < self._nparticipants and not data in dest_set:
            dest_set.append(data)
            if len(dest_set) == self._nparticipants:
                self.status = self.next_state('inputs')
        if data in dest_set:
            return dest_set.index(data)
        else:
            return -1

    def add(self, curr_state, data):
        """
         Add a data item for given state

        Args:
           curr_state: current state name
           data: item to add
        """
        # check if we're in correct state for adding this kind
        # of data
        if not self.status == curr_state:
            return -1

        if curr_state == 'outputs':
            if not util.validate_address(data):
                return -1

        # add data to the set, and change state if we're done
        # collecting information for this stage.
        dest_set = getattr(self, curr_state)
        if len(dest_set) < self._nparticipants:
            if not data in dest_set:
                dest_set.append(data)
            if len(dest_set) == self._nparticipants:
                self.status = self.next_state(curr_state)
            return dest_set.index(data)
        return -1

    def report_status(self):
        """
         Report known information for the coinjoin
        """
        status = {}
        if self._error:
            status['status'] = 'error'
            status['error'] = self._error
        else:
            status['status'] = self.status

        # print set lengths
        for set_name in self._sets:
            status[set_name] = len(filter(lambda s: not s == '', getattr(self, set_name)))

        status['target'] = self._nparticipants
        status['amount'] = self._amount
        status['messages'] = list(self.messages)
        if self._tx:
            status['transaction'] = self._tx
        if self._final_tx:
            status['final-transaction'] = self._final_tx

        # if final or signatures show all data
        if self.status in ['final', 'signatures']:
            status['data'] = {}
            for set_name in self._sets:
                status['data'][set_name] = list(getattr(self, set_name))
        return status


##################################
# Routes

@app.route('/g/<secret>', methods=['GET'])
@app.route('/g/<secret>/<participants>', methods=['GET'])
@app.route('/g/<secret>/<participants>/<amount>', methods=['GET'])
def coinj_get(secret, participants=3, amount='0.01'):
    """
     GET information for a CoinJoin
    """
    if secret in transactions:
        t = transactions[secret]
    else:
        # validate but keep as str for now
        amount = str(Decimal(amount))
        t = SimpleCoinJoin(int(participants), amount)
        transactions[secret] = t
    return jsonify(t.report_status())

@app.route('/g/<secret>', methods=['POST'])
@app.route('/g/<secret>/<participants>', methods=['POST'])
@app.route('/g/<secret>/<participants>/<amount>', methods=['POST'])
def coinj_post(secret, participants=3, amount='0.01'):
    """
     POST information into a CoinJoin
    """
    if secret in transactions:
        t = transactions[secret]

        # collect post arguments
        input = request.form.get('input')
        output = request.form.get('output')
        sig = request.form.get('sig')
        message = request.form.get('message')

        # Add a message
        if message:
            t.add_message(message)
        # Execute commands
        if input and input.isalnum():
            return jsonify({'status': t.add_input(input)})
        elif output and output.isalnum():
            return jsonify({'status': min(t.add('outputs', output), 0)})
        elif sig:
            # only alphanumeric and colon
            sig = re.sub(r'[^a-zA-Z0-9:]', '', sig)
            sig_idx = int(request.form.get('sig_idx'))
            return jsonify({'status': min(t.add('signatures', [sig_idx, sig]), 0)})
        # if no command return error
        return jsonify({'error': 'Invalid command', 'status': -1}, 402)
    # group not found
    return jsonify({'error': 'Group does not exist'}, 400)


@app.route('/')
def page():
    """
    Print public transactions
    """
    public_open_tx = get_public_tx()
    descriptions = map(lambda s: "<a href='/g/%s'>%s</a> %s/%s (%s btc)" % (s, s[6:], len(transactions[s].outputs), transactions[s]._nparticipants, transactions[s]._amount), public_open_tx)
    return "<h3>Mixer Lobby</h3><li>"+"</li><li>".join(descriptions)+"</li>"

@app.route('/public')
def page_json():
     """
     Print public transactions in json format
     """
     return jsonify({'links': map(lambda s: transactions[s].report_status(), get_public_tx())})

@app.route('/status')
def status_page():
    return jsonify({'status': "ALL SYSTEMS GO GO", 'transactions': len(transactions)})


##################################
# Main

if __name__ == '__main__':
    server.serve_forever('', 8001)

