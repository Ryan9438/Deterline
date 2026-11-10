"""异常层级（O2 步 1：从 modify_save.py L62-74 1:1 平移）。

所有 Deterline 异常的唯一定义点。模块无内部依赖（分层最底）。
调用方以模块属性形式引用：`errors.ValidationError(...)`。
"""


class DeterlineError(Exception):
    """Base exception for all Deterline errors."""

class ValidationError(DeterlineError):
    """Invalid argument or parameter."""

class NotFoundError(DeterlineError):
    """File, room, or object not found."""
