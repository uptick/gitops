import json
import random
import string
from invoke import run

CACHE = {}


def gen_secret(length=64):
    return ''.join(
        random.SystemRandom().choice(
            string.ascii_uppercase + string.digits
        ) for _ in range(length)
    )


def get_account_id():
    if 'ACCOUNT_ID' not in CACHE:
        # This is not ideal, as it makes an assumption that the account_id of interest is the
        # one the user is currently sitting in. Ideally, should ask the cluster (though that is
        # messy in its own right, since we don't necessarily want the cluster that's in the
        # current context either).
        caller_identity = run('aws sts get-caller-identity', hide=True).stdout.strip()
        CACHE['ACCOUNT_ID'] = json.loads(caller_identity)['Account']
    return CACHE['ACCOUNT_ID']
