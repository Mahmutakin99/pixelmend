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
