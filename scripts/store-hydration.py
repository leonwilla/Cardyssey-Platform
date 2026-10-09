"""Read public Hydrogen SSR metadata as JSON; never execute storefront scripts."""
import json
import re


def loader_data(html):
    blocks = re.findall(r'streamController\.enqueue\(("(?:\\.|[^"\\])*")\)', html)
    if not blocks:
        raise ValueError('public storefront data missing')
    nodes = json.loads(json.loads(blocks[0]).splitlines()[0])
    if not isinstance(nodes, list) or len(nodes) > 100000:
        raise ValueError('invalid storefront data')
    cache = {}

    def resolve(index, depth=0):
        if type(index) is not int:
            raise ValueError('invalid reference')
        if index < 0:
            return None
        if index >= len(nodes) or depth > 40:
            raise ValueError('invalid reference/depth')
        if index in cache:
            return cache[index]
        value = nodes[index]
        if isinstance(value, dict):
            result = {}
            for key, child in value.items():
                if not re.fullmatch(r'_\d+', key):
                    raise ValueError('invalid object key')
                field = resolve(int(key[1:]), depth + 1)
                if not isinstance(field, str):
                    raise ValueError('invalid field name')
                result[field] = resolve(child, depth + 1)
        elif isinstance(value, list):
            # Typed/deferred objects are irrelevant to product/collection metadata.
            result = None if value and isinstance(value[0], str) else [resolve(v, depth + 1) for v in value]
        else:
            result = value
        cache[index] = result
        return result

    data = resolve(0).get('loaderData')
    if not isinstance(data, dict):
        raise ValueError('loader data missing')
    return data
