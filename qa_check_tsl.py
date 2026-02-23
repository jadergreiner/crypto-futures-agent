#!/usr/bin/env python
"""Quick QA check for TSL implementatio"""

from risk.trailing_stop import (
    TrailingStopManager,
    TrailingStopConfig,
    TrailingStopState,
    create_tsl_manager,
    init_tsl_state,
)
import inspect

print("📋 DOCSTRING COVERAGE ANALYSIS")
print("=" * 60)

classes = [TrailingStopConfig, TrailingStopState, TrailingStopManager]
functions = [create_tsl_manager, init_tsl_state]

missing_docs = 0

for cls in classes:
    has_doc = cls.__doc__ is not None
    status = "✅" if has_doc else "❌"
    print(f"{status} {cls.__name__}: {cls.__doc__.split(chr(10))[0] if has_doc else 'SEM'}")
    if not has_doc:
        missing_docs += 1

    # Check methods
    public_methods = [m for m in dir(cls) if not m.startswith("_") and callable(getattr(cls, m))]
    for method_name in public_methods:
        method = getattr(cls, method_name)
        has_doc = method.__doc__ is not None
        status = "  ✅" if has_doc else "  ❌"
        print(f"{status} .{method_name}()")
        if not has_doc:
            missing_docs += 1

for func in functions:
    has_doc = func.__doc__ is not None
    status = "✅" if has_doc else "❌"
    print(f"{status} {func.__name__}(): {func.__doc__.split(chr(10))[0] if has_doc else 'SEM'}")
    if not has_doc:
        missing_docs += 1

print()
print(f"Total missing docstrings: {missing_docs}")
print(f"Docstring coverage: {'100% ✅' if missing_docs == 0 else f'{missing_docs} items'}")
