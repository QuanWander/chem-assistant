# chem-assistant · 化学助教

> 面向初三与高中的化学助教。**会用代码算的，不交给模型猜。**

## 为什么做这个

教学场景里，模型最常见的错误不是「不会」，而是「不会还硬答」：

- 配平靠心算，系数差一个；
- 摩尔质量用错原子量；
- 引用「教材说」但根本指不出章节；
- 条件不足也硬算，题目本身错了也不指出。

这个项目的原则是：**确定性的事用代码做，不确定的事必须说出来。**

## 核心能力（与平台无关）

| 模块 | 能力 |
|---|---|
| `chemcore.formula` | 化学式解析、元素计数、摩尔质量、电荷；支持括号、结晶水 |
| `chemcore.equation` | 配平（原子/电荷守恒）、离子方程式检查、多解检测 |
| `chemcore.stoich` | 物质的量、气体体积、浓度、稀释、产率、限量试剂 |
| `chemcore.knowledge` | 人教版章节目录 + 知识点卡片 |
| `chemcore.policy` | 安全拦截、依据分级、不确定三分法 |
| `chemcore.retrieval` | 关键词 + 别名 + 字符重叠检索，不依赖向量模型 |

## 多平台

核心是纯 Python、零第三方依赖，适配器是薄壳：

- `main.py`：AstrBot 插件（工具 + 上下文注入 + 危险请求拦截）
- `adapters/mcp`：MCP server（DSH、Claude 等 agent 可直接接）
- `adapters/http`：HTTP / CLI（QQ 桥接、QQAgent 等）
- `adapters/openai_tools`：标准 function-calling schema

## 在 AstrBot 里安装

插件市场搜索「化学助教」，或：

```bash
cd AstrBot/data/plugins
git clone https://github.com/QuanWander/chem-assistant
```

需要 **AstrBot >= 4.24.2**（上下文注入依赖 `TextPart.mark_as_temp()`）。

## 配置

| 字段 | 类型 | 说明 |
|---|---|---|
| `enabled` | bool | 启用插件 |
| `level` | string | 默认学段：`初三` / `高中` |
| `textbook` | string | 教材版本，v1 只内置人教版 |
| `strict_mode` | bool | 严格模式（必须调工具、必须给依据） |
| `show_citations` | bool | 显示教材依据 |
| `max_cards` | int | 每轮最多注入几张知识卡 |
| `debug_enable` | bool | 调试日志 |

## 内置工具

| 工具 | 作用 |
|---|---|
| `chem_balance` | 配平方程式，校验原子/电荷守恒 |
| `chem_molar_mass` | 计算摩尔质量 |
| `chem_calculate` | 物质的量、气体体积、浓度等计算 |
| `chem_search` | 检索人教版知识卡 |
| `chem_safety_check` | 判断是否涉及危险操作，给实验安全提示 |

## 严谨策略

- **安全**：爆炸物、毒品、化学武器的制作/提纯/使用方法直接拒答（插件层拦截，不经过模型）。
- **依据**：引用教材必须给到书名和章节，指不到就不许说「教材说」。
- **不确定**：分「确定 / 存疑 / 不知道」，存疑列 caveats，不知道给查证路径。
- **错前提**：条件不足、数据矛盾先指出，再谈能不能算。
- **超纲**：可以拓展，但必须标「拓展」。

## 测试

```bash
python -m unittest discover -s tests -v      # 核心 51 个用例
python tests/run_golden.py                   # 确定性 golden set 31 项
python tests/smoke_adapter.py                # 适配器冒烟（需装 AstrBot 依赖）
```

当前 51 个核心用例 + 8 个适配器冒烟 + 31 项 golden set，覆盖解析、配平、计量、安全、检索、回答结构。

## 其他平台怎么接

### HTTP（QQ 桥接 / QQAgent / 其他语言）

```bash
python -m adapters.http.server --port 8765
```

```
GET  /health
POST /v1/ask          {"question": "...", "level": "高中", "textbook": "人教版"}
POST /v1/balance      {"equation": "Fe + O2 -> Fe3O4"}
POST /v1/molar_mass   {"formula": "H2SO4"}
POST /v1/calculate    {"kind": "moles_from_mass", "formula": "H2O", "a": 18}
POST /v1/safety       {"question": "..."}
```

### MCP（DSH / Claude 等 agent）

```bash
python -m adapters.mcp.server
```

暴露 5 个工具：`chem_search`、`chem_balance`、`chem_molar_mass`、`chem_calculate`、`chem_safety_check`。
在 MCP 客户端里把命令配成 `python -m adapters.mcp.server`（工作目录为本仓库）即可。

### CLI

```bash
python -m adapters.cli balance "Fe + O2 -> Fe3O4"
python -m adapters.cli molar "CuSO4·5H2O"
python -m adapters.cli ask "氧化还原的实质是什么"
```

### OpenAI function calling

`adapters/openai_tools/tools.json` 是标准 tool schema，可直接塞进 `tools` 参数。

## 已知限制

- v1 只实现人教版，其他版本留字段不实现；
- 知识卡目前覆盖必修一/二与九年级核心，后续按章节补；
- 不做出题/判题（v2）；
- 不替代实验室安全规范与教师判断。

## License

MIT
