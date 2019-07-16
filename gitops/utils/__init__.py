import random
import string


def gen_secret(length=64):
    return ''.join(
        random.SystemRandom().choice(
            string.ascii_uppercase + string.digits
        ) for _ in range(length)
    )
