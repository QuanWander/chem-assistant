"""AstrBot 适配器：化学助教。

薄壳原则：解析、配平、计量、知识检索全部在 chemcore，这里只做：
1. 危险请求的确定性拦截；
2. 往 LLM 请求里注入「严谨规则 + 相关知识卡」；
3. 把 chemcore 暴露成 LLM 工具。

AstrBot 版本要求 >= 4.24.2（需要 TextPart.mark_as_temp）。
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star, register

try:
    from astrbot.core.agent.message import TextPart
except Exception:  # pragma: no cover - 老版本兜底
    TextPart = None  # type: ignore[assignment]

try:
    # AstrBot 以包模块加载插件时走相对导入：chemcore 会随插件一起卸载/重载，
    # 不会留在 sys.modules 里变成旧代码。
    from .chemcore import ChemError, acidbase, balance_equation, parse_formula, stoich
    from .chemcore.policy import check_safety, lab_safety_note
    from .chemcore.retrieval import search
    from .chemcore.service import build_context, card_to_text, looks_like_chemistry
    from .chemcore.study_mode import is_study_related, should_guard
except ImportError:  # 直接跑 main.py / 冒烟测试时没有包上下文
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from chemcore import ChemError, acidbase, balance_equation, parse_formula, stoich
    from chemcore.policy import check_safety, lab_safety_note
    from chemcore.retrieval import search
    from chemcore.service import build_context, card_to_text, looks_like_chemistry
    from chemcore.study_mode import is_study_related, should_guard


@register(
    "astrbot_plugin_chem_assistant",
    "大肥鱼",
    "化学助教：初三/高中，人教版，会算、会查、不确定会直说",
    "0.1.9",
)
class ChemAssistant(Star):
    def __init__(self, context: Context, config: AstrBotConfig | None = None) -> None:
        super().__init__(context)
        self.config = config or {}

    # ------------------------------------------------------------------ 配置
    def _level(self) -> str:
        return str(self.config.get("level") or "高中").strip()

    def _textbook(self) -> str:
        return str(self.config.get("textbook") or "人教版").strip()

    def _max_cards(self) -> int:
        try:
            return max(0, min(5, int(self.config.get("max_cards", 2))))
        except (TypeError, ValueError):
            return 2

    def _strict(self) -> bool:
        return bool(self.config.get("strict_mode", True))

    def _in_study_scope(self, event: AstrMessageEvent) -> bool:
        return should_guard(self.config, event.get_group_id(), event.get_sender_id())

    def _effective_level(self, question: str) -> str:
        """问题里明确说了「初三/初中」就按初中答，说了「高考/选必」就按高中答。"""
        text = question or ""
        if any(word in text for word in ("初三", "初中", "中考", "九年级")):
            return "初三"
        if any(word in text for word in ("高三", "高考", "选修", "选择性必修")):
            return "高中"
        return self._level()

    # ------------------------------------------------------------------ 注入
    @staticmethod
    def _append_part(req: ProviderRequest, text: str) -> bool:
        if not text.strip() or TextPart is None:
            return False
        try:
            part = TextPart(text=text)
            mark = getattr(part, "mark_as_temp", None)
            if not callable(mark):
                logger.warning("[chem] 当前 AstrBot 不支持 mark_as_temp，跳过注入")
                return False
            part = mark()
            req.extra_user_content_parts.append(part)
            return True
        except Exception as exc:  # pragma: no cover - 防御
            logger.warning(f"[chem] 追加内容块失败: {exc}")
            return False

    @filter.on_llm_request()
    async def inject_chemistry_context(
        self, event: AstrMessageEvent, req: ProviderRequest
    ) -> None:
        if not bool(self.config.get("enabled", True)):
            return
        question = str(req.prompt or "")
        study_scope = self._in_study_scope(event)
        mode_block = (
            "【只聊学习模式】当前群/用户被设置为只聊学习：只回答学习、化学、作业、考试相关问题；"
            "遇到闲聊、情绪、游戏、八卦，简短拒绝并把话题拉回学习，不展开，不主动闲聊。"
            if study_scope
            else ""
        )
        if not looks_like_chemistry(question):
            if mode_block and is_study_related(question):
                self._append_part(req, mode_block)
            return

        ctx = build_context(
            question,
            level=self._effective_level(question),
            textbook=self._textbook(),
            max_cards=self._max_cards(),
            show_citations=bool(self.config.get("show_citations", True)),
            strict=self._strict(),
        )
        if ctx.get("refused"):
            return

        blocks = ([mode_block] if mode_block else []) + [ctx["rules"]]
        cards = ctx.get("cards") or []
        if cards:
            blocks.append("【相关知识卡片（来自内置知识库，可直接引用章节）】")
            blocks.extend(cards)
        else:
            blocks.append("【提示】知识库里没有直接匹配的卡片；如果回答涉及具体章节，请明确说「教材未提供依据」。")
        if ctx.get("safety_note"):
            blocks.append(f"【实验安全】{ctx['safety_note']}")

        if self._append_part(req, "\n\n".join(blocks)):
            logger.info("[chem] 注入 %d 张知识卡（%s）", len(cards), self._level())

    # ------------------------------------------------------------------ 拦截
    @filter.event_message_type(filter.EventMessageType.ALL, priority=120)
    async def study_only_guard(self, event: AstrMessageEvent):
        """只聊学习模式：命中的群/用户，非学习话题直接拒答。"""
        if not bool(self.config.get("enabled", True)):
            return
        if not self._in_study_scope(event):
            return
        text = str(event.message_str or "").strip()
        if not text or text.startswith(("/", "／")):
            return
        if is_study_related(text):
            return
        event.stop_event()
        logger.info("[chem] 只聊学习模式拦截非学习消息")
        yield event.plain_result(
            str(self.config.get("study_only_message") or "这里只聊学习相关的问题，其他话题先放一放。")
        )

    @filter.event_message_type(filter.EventMessageType.ALL, priority=100)
    async def refuse_dangerous(self, event: AstrMessageEvent):
        """危险化学品请求直接拒答，不交给模型。"""
        if not bool(self.config.get("enabled", True)):
            return
        verdict = check_safety(event.message_str or "")
        if not verdict.refused:
            return
        event.stop_event()
        logger.info("[chem] 拦截危险请求：%s", verdict.category)
        yield event.plain_result(
            f"{verdict.message}\n{verdict.hint}\n\n安全提示：涉及危险化学品时，请以实验室安全规范和专业教师指导为准。"
        )

    # ------------------------------------------------------------------ 工具
    @filter.llm_tool()
    async def chem_search(self, event: AstrMessageEvent, question: str, level: str = ""):
        """检索人教版化学知识卡片，返回概念、要点、方程式与易错点。

        Args:
            question(string): 要查的化学问题或关键词，例如「氧化还原的实质」。
            level(string): 学段，初三 / 高中；留空用插件配置。
        """
        hits = search(question, k=self._max_cards(), stage=None)
        if not hits:
            return "内置知识库里没有匹配的卡片。不要编造章节；如果回答，请说明依据不足。"
        return "\n\n".join(card_to_text(card) for card in hits)

    @filter.llm_tool()
    async def chem_molar_mass(self, event: AstrMessageEvent, formula: str):
        """计算化学式的摩尔质量（g/mol），支持括号、结晶水和电荷。

        Args:
            formula(string): 化学式，例如 H2SO4、Ca(OH)2、CuSO4·5H2O、SO4^2-。
        """
        try:
            comp = parse_formula(formula)
        except ChemError as exc:
            return f"计算失败：{exc.message}。{exc.hint}"
        return f"{formula} 的摩尔质量 = {comp.molar_mass():.3f} g/mol（原子数 {comp.atoms()}，电荷 {comp.charge:+d}）。"

    @filter.llm_tool()
    async def chem_balance(self, event: AstrMessageEvent, equation: str):
        """配平化学方程式，返回最小整数系数并校验原子/电荷守恒。

        Args:
            equation(string): 未配平的方程式，用 -> 或 → 连接，例如「Fe + O2 -> Fe3O4」。
        """
        try:
            result = balance_equation(equation)
        except ChemError as exc:
            return f"配平失败：{exc.message}。{exc.hint}"
        checks = result.checks
        note = "原子守恒" if checks.get("balanced") else "原子不守恒"
        if checks.get("charge_balanced") is False:
            note += "，电荷不守恒"
        return f"配平结果：{result.formatted()}（{note}）"

    @filter.llm_tool()
    async def chem_calculate(
        self,
        event: AstrMessageEvent,
        kind: str,
        formula: str = "",
        a: float = 0,
        b: float = 0,
    ):
        """化学计量计算。kind 取值：moles_from_mass / mass_from_moles / gas_volume_stp / moles_from_gas_volume_stp / concentration / moles_from_concentration。

        Args:
            kind(string): 计算类型。
            formula(string): 化学式，涉及质量/摩尔质量时必填。
            a(float): 第一个输入量（质量 g、物质的量 mol、体积 L、浓度 mol/L）。
            b(float): 第二个输入量（溶液体积 L 等）。
        """
        try:
            if kind == "moles_from_mass":
                value = stoich.moles_from_mass(a, formula)
                return f"n = {value:.4f} mol（{a} g ÷ {stoich.molar_mass(formula):.3f} g/mol）"
            if kind == "mass_from_moles":
                value = stoich.mass_from_moles(a, formula)
                return f"m = {value:.4f} g（{a} mol × {stoich.molar_mass(formula):.3f} g/mol）"
            if kind == "gas_volume_stp":
                value = stoich.gas_volume_stp(a)
                return f"V = {value:.4f} L（{a} mol × 22.4 L/mol，标准状况）"
            if kind == "moles_from_gas_volume_stp":
                value = stoich.moles_from_gas_volume_stp(a)
                return f"n = {value:.4f} mol（{a} L ÷ 22.4 L/mol，标准状况）"
            if kind == "concentration":
                value = stoich.concentration(a, b)
                return f"c = {value:.4f} mol/L（{a} mol ÷ {b} L）"
            if kind == "moles_from_concentration":
                value = stoich.moles_from_concentration(a, b)
                return f"n = {value:.4f} mol（{a} mol/L × {b} L）"
            return f"不支持的计算类型：{kind}"
        except ChemError as exc:
            return f"计算失败：{exc.message}。{exc.hint}"

    @filter.llm_tool()
    async def chem_ph(
        self,
        event: AstrMessageEvent,
        kind: str,
        c: float,
        ka: float = 0,
        kb: float = 0,
    ):
        """计算 25 ℃ 溶液的 pH。kind 取值：strong_acid / strong_base / weak_acid / weak_base；弱酸必须给 Ka，弱碱必须给 Kb。

        Args:
            kind(string): 溶液类型。
            c(float): 浓度，mol/L。
            ka(float): 一元弱酸的 Ka；weak_acid 必填。
            kb(float): 一元弱碱的 Kb；weak_base 必填。
        """
        try:
            if kind == "strong_acid":
                r = acidbase.ph_strong_acid(c)
            elif kind == "strong_base":
                r = acidbase.ph_strong_base(c)
            elif kind == "weak_acid":
                if ka <= 0:
                    return "计算失败：弱酸必须提供 Ka（题目没给就不能算，不能替它假设）。"
                r = acidbase.ph_weak_acid(c, ka)
            elif kind == "weak_base":
                if kb <= 0:
                    return "计算失败：弱碱必须提供 Kb（题目没给就不能算，不能替它假设）。"
                r = acidbase.ph_weak_base(c, kb)
            else:
                return f"不支持的 pH 类型：{kind}"
        except ChemError as exc:
            return f"计算失败：{exc.message}。{exc.hint}"
        notes = "；".join(r.assumptions)
        return f"pH = {r.ph:.2f}（[H+] = {r.h_concentration:.3e} mol/L；{notes}）"

    @filter.llm_tool()
    async def chem_safety_check(self, event: AstrMessageEvent, question: str):
        """判断一个问题是否涉及危险化学品操作，并给出实验安全提示。

        Args:
            question(string): 用户的问题或实验描述。
        """
        verdict = check_safety(question)
        if verdict.refused:
            return f"必须拒绝：{verdict.message}。{verdict.hint}"
        note = lab_safety_note(question)
        return f"可以回答。{('实验安全：' + note) if note else '未识别到特别危险的实验操作。'}"
