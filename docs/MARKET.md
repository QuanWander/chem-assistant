# 市场提交信息

Cloud 提交页如果要填表，可以直接抄下面这些。

| 字段 | 内容 |
|---|---|
| 仓库 | https://github.com/QuanWander/chem-assistant |
| 插件名 | `astrbot_plugin_chem_assistant` |
| 显示名 | 化学助教 |
| 短描述 | 初三与高中化学答疑，会算、会查、不确定会直说 |
| 作者 | 大肥鱼 |
| 版本 | 0.1.2 |
| 最低 AstrBot | >=4.24.2 |
| 支持平台 | aiocqhttp / qq_official / qq_official_webhook |
| 标签 | 化学、教学、教育 |
| 图标 | 仓库根目录 `logo.png` |

长描述：

> 面向初三和高中的化学助教。化学式解析、摩尔质量、方程式配平、物质的量与浓度计算都走确定性代码，不靠模型心算；知识卡按人教版章节索引，引用给到书名和章节；遇到条件不足、数据矛盾或超纲内容会明确说明，不编造；危险化学品的制作、提纯、使用方法直接拒答。核心与平台无关，同一仓库还提供 MCP、HTTP、CLI、OpenAI tools 适配器。

## 提交步骤

1. 打开 https://cloud.astrbot.app ，用 GitHub 登录（QuanWander）；
2. 进入「提交插件 / 我的插件」，填仓库地址并授权；
3. 选择最新 release（v0.1.2）或让 Cloud 从默认分支构建；
4. 等待构建完成，管理员审核；
5. 审核通过后，市场里会出现「化学助教」，AstrBot 就能搜到安装。

新仓库第一次上架通常需要手动提交一次，之后才会跟着 release 自动更新。
