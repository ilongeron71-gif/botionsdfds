_dirty = False


def mark_dirty():
    global _dirty
    _dirty = True


def is_dirty() -> bool:
    return _dirty


def clear_dirty():
    global _dirty
    _dirty = False