"""异常层级（O2 步 1：从 modify_save.py L62-74 1:1 平移）。

所有 Deterline 异常的唯一定义点。模块无内部依赖（分层最底）。
调用方以模块属性形式引用：`errors.ValidationError(...)`。

（A P3-6 注记：transactions/sandbox 的少量内部防线仍抛裸 RuntimeError
——历史 1:1 平移，行为等价（cli.py 异常兜底一并接住）；收编为
DeterlineError 子类属后续清理项，不在本层强制。）
"""


class DeterlineError(Exception):
    """Base exception for all Deterline errors."""

class ValidationError(DeterlineError):
    """Invalid argument or parameter."""

class NotFoundError(DeterlineError):
    """File, room, or object not found."""
