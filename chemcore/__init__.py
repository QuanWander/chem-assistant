"""chemcore: 与平台无关的化学核心。

设计原则：
1. 能用确定性代码算的，不交给模型猜（化学式、摩尔质量、配平、计量）；
2. 所有失败都抛 ChemError，带稳定的 code，方便适配器翻译成人话；
3. 不依赖任何第三方库，纯标准库。
"""

from .errors import ChemError
from .formula import Composition, parse_formula
from .equation import BalanceResult, balance_equation, check_ion_equation
from . import stoich

__all__ = [
    "ChemError",
    "Composition",
    "parse_formula",
    "BalanceResult",
    "balance_equation",
    "check_ion_equation",
    "stoich",
]

__version__ = "0.1.0"
