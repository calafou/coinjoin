import subprocess
from decimal import Decimal

def call(command):
    return subprocess.check_output(command, shell=True).rstrip("\n")

def validate_address(address):
    return "Success" in call("sx validaddr %s" % address)

def parse_amount(amount):
    return int(Decimal(amount)*100000000)

