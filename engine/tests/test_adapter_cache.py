from pixelmend_engine.adapter_cache import AdapterCache


def test_adapter_cache_reuses_one_adapter_for_a_model_profile():
    cache = AdapterCache()
    made = []
    first = cache.get(('model', 'CoreMLExecutionProvider'), lambda: made.append(object()) or made[-1])
    second = cache.get(('model', 'CoreMLExecutionProvider'), lambda: object())
    assert first is second
    assert len(made) == 1


def test_adapter_cache_evicts_least_recently_used_adapter():
    closed = []
    cache = AdapterCache(max_entries=1)
    cache.get(('a', 'CPU'), lambda: type('Adapter', (), {'close': lambda self: closed.append('a')})())
    cache.get(('b', 'CPU'), lambda: object())
    assert closed == ['a']


def test_adapter_cache_releases_old_session_before_loading_replacement():
    events = []
    cache = AdapterCache(max_entries=1)
    cache.get('large-a', lambda: type('Adapter', (), {'close': lambda self: events.append('closed-a')})())
    cache.get('large-b', lambda: events.append('loaded-b') or object())
    assert events == ['closed-a', 'loaded-b']


def test_adapter_cache_does_not_retain_failed_replacement():
    cache = AdapterCache(max_entries=1)
    cache.get('old', lambda: object())

    def fail():
        raise RuntimeError('model allocation failed')

    try:
        cache.get('new', fail)
    except RuntimeError:
        pass
    else:
        raise AssertionError('replacement factory must fail')
    assert len(cache._items) == 0


def test_eviction_drops_adapter_without_close_before_factory():
    import weakref
    class Adapter:
        pass
    cache = AdapterCache(max_entries=1)
    old = weakref.ref(cache.get('old', Adapter))
    def replace():
        assert old() is None
        return Adapter()
    cache.get('new', replace)
