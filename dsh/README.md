# 化学助教 · DSH bundle

把 `chem-assistant` 的 MCP stdio server 接到 DSH。

## 前置

- Python 3.10+
- 仓库可导入 `chemcore` / `adapters`

## 配置

`cordis.patch.yml` 默认使用本机路径：

- 解释器：`E:\QQ机器人\AstrBot\.venv\Scripts\python.exe`
- 工作目录：`E:\QQ机器人\发布\chem-assistant`

换机器时改这两处。

## 工具

- `mcp__chem_assistant__chem_search`
- `mcp__chem_assistant__chem_balance`
- `mcp__chem_assistant__chem_molar_mass`
- `mcp__chem_assistant__chem_calculate`
- `mcp__chem_assistant__chem_ph`
- `mcp__chem_assistant__chem_safety_check`
