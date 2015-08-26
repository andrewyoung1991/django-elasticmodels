# tasks.py
# author: andrew young
# email: ayoung@thewulf.org

import functools

try:
    from celery import shared_task
except ImportError:
    # user hasn't installed celery... no biggy
    def shared_task(fn):
        @functools.wraps(fn)
        def wrap(*args, **kwargs):
            return fn(*args, **kwargs)
        return wrap


def _queued_task(fn):
    @functools.wraps(fn)
    def wrap(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrap


indexing_task = shared_task(_queued_task)
bulk_indexing_task = shared_task(_queued_task)

