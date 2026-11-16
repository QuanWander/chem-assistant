# 可移植性说明

## 核心（可离开 AstrBot）

- `chemcore/`：化学式、配平、计量、知识卡、安全策略
- `adapters/mcp/`：MCP stdio 服务
- `adapters/http/`：HTTP 服务
- `adapters/cli.py`：命令行入口

## AstrBot 壳

- `main.py`：AstrBot 插件入口、命令、学习模式守卫

## DSH 迁移

- 核心不 import AstrBot，可直接作为 MCP 工具运行
- 无 QQ、无平台依赖，优先迁移
- DSH bundle 只做 MCP 接线，不内嵌 Python

## 不迁移

- AstrBot 命令前缀与学习模式配置属于平台壳，DSH 侧用工具参数表达
