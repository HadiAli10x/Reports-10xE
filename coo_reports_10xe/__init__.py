from . import hooks
from . import models


def post_init_assign_ayesha(env):
    return hooks.post_init_assign_ayesha(env)
