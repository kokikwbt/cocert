"""Optional retained-count TV comparisons with explicit output semantics."""


def minimum_tv_bounds(query, total=None, **options):
    """Return one-sided bounds between independently specified probability cores."""
    from .minimum_tv.model import bounds
    return bounds(query, total, **options)


def eris_lp(query, epsilon='1/10', total=None, **options):
    """Evaluate the known-total linear TV connection with OSQP."""
    from .eris_tv.model import decide
    return decide(query, epsilon, total, **options)


def conditional_lp(query, epsilon='1/10', total=None, **options):
    """Use a fixed-total LP and nested denominator grids when needed."""
    from .partial_id_tv.model import refine
    return refine(query, epsilon, total, **options)


def adaptive_lp(query, epsilon='1/10', **options):
    """Refine unknown split-total intervals with the original TV LP."""
    from .partial_id_tv.interval_search import search
    return search(query, epsilon, **options)


def mmd_tv(query, epsilon='1/10', total=None, *, bandwidth='fixed', **options):
    """Return one-sided TV certificates from bounded missing-data MMD."""
    if bandwidth == 'fixed':
        from .mmd_miss.model import decide
    elif bandwidth == 'median':
        from .mmd_miss.median import decide
    else:
        raise ValueError('Unknown bandwidth')
    return decide(query, epsilon, total, **options)
