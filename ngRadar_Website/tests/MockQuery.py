class MockQuery:
    def __init__(self, items):
        self._items = list(items)

    def __getitem__(self, key):
        # key will be an array slice
        if isinstance(key, slice):
            return MockQuery(self._items[key])
        
    # def len(self):
    #     return len(self._items)
        
    def first(self):
        return self._items[0] if self._items else None

    def exists(self):
        return bool(self._items)

    def __iter__(self):
        return iter(self._items)

    def __bool__(self):
        return bool(self._items)

    def aggregate(self, agg_expression):
        # Example agg_expression: Avg('latency_ms')
        field_name = None

        # Django expressions typically store the field in .source_expressions[0]
        # and that object often has .name (for F('field') or similar).
        if hasattr(agg_expression, "source_expressions") and agg_expression.source_expressions:
            first = agg_expression.source_expressions[0]
            field_name = getattr(first, "name", None)

        # Fallback: sometimes the expression stringifies to the field name
        if field_name is None:
            # Last resort if you want to hard-code behavior for your test
            field_name = "latency_ms"

        values = []
        for item in self._items:
            v = getattr(item, field_name, None)
            if v is not None:
                values.append(v)

        avg = (sum(values) / len(values)) if values else None
        return {"latency_ms__avg": avg}