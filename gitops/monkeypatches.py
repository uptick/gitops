"""
REMOVE WHEN: https://github.com/pyinvoke/invoke/commit/8f6c0617c7dc59b105dd1b92fb417e75adc21bea is released.
"""
import inspect

if not hasattr(inspect, "getargspec"):
    inspect.getargspec = inspect.getfullargspec
