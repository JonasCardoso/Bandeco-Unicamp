"""Locks por chave com liberação automática quando deixam de ser utilizados."""

import asyncio
from weakref import WeakValueDictionary


def user_lock(state: dict, user_id):
    locks = state.setdefault("user_locks", WeakValueDictionary())
    key = str(user_id)
    lock = locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        locks[key] = lock
    return lock
