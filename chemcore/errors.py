"""chemcore 的统一异常。"""

from __future__ import annotations


class ChemError(ValueError):
    """化学计算/解析错误。

    code 是稳定标识，适配器可以据此决定是提示用户、还是让模型换个说法。
    """

    def __init__(self, code: str, message: str, *, hint: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint

    def to_dict(self) -> dict:
        data = {"code": self.code, "message": self.message}
        if self.hint:
            data["hint"] = self.hint
        return data

    def __str__(self) -> str:  # pragma: no cover - 展示用
        return f"[{self.code}] {self.message}" + (f"（{self.hint}）" if self.hint else "")
