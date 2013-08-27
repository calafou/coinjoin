try:
    from _detwallet import pubkey_to_address, DeterministicWallet

    wallet = DeterministicWallet()
    mpk = "28070630d7c5103fc93784facb84113ded4831e73681b821f5799ebfeabeb2611cffc48bb40cf2f7e06300abf780241fa161818e8457f87b798a95beda82a712".decode(
        "hex")
    wallet.set_master_public_key(mpk)

    def get_address(key_id):
        return pubkey_to_address(wallet.generate_public_key(key_id))
except ImportError:
    def get_address(key_id):
        return "lol"

