# WYD OMS Skills

[![Validate](https://github.com/liqlong/wyd-oms-skills/actions/workflows/validate.yml/badge.svg)](https://github.com/liqlong/wyd-oms-skills/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/liqlong/wyd-oms-skills)](https://github.com/liqlong/wyd-oms-skills/releases)

通过自然语言查询 OMS 订单、分析库存，以及办理入库、出库、退件、附件和包裹异常工单。
本仓库发布 `oms-mcp-server` 配套的全部 6 个 Agent Skills，包含业务指引、引用文档和辅助脚本。

**使用前需要连接已授权的 OMS MCP 服务。** Skill 安装不会部署服务或自动取得业务权限。
本仓库采用[安装与使用许可](LICENSE)，不授予修改、再分发或再许可权利。

## Skills

| Skill | 名称 | 能力 |
| --- | --- | --- |
| [oms-order-query](skills/oms-order-query/SKILL.md) | 订单查询 | 查询入库预约、入库单、ToC/ToB 出库单、退件、工单等 |
| [oms-inventory-health](skills/oms-inventory-health/SKILL.md) | 库存健康 | 查看断货风险、补货数量、库存预警及库龄积压 |
| [oms-inbound-managed](skills/oms-inbound-managed/SKILL.md) | 智能入库 | 办理入库预约、审核后建单、提交及进度查询 |
| [oms-outbound-batch](skills/oms-outbound-batch/SKILL.md) | 批量发货 | 从 XLSX/CSV 或聊天资料办理 ToC/ToB 发货，上传面单及附件，查询回执及取消 |
| [oms-return-recovery](skills/oms-return-recovery/SKILL.md) | 招领中心 | 退件预报、每批 5 单清单及图片预览、认领和明确指令下的处置 |
| [oms-package-exception](skills/oms-package-exception/SKILL.md) | 包裹异常工单 | 上传工单附件，办理拦截、地址更正、包裹调查及查看反馈 |

## 快速安装

需要 Node.js/npm。以下命令使用第三方 [Skills CLI](https://github.com/vercel-labs/skills)，
发布验证使用 `skills@1.7.2`。安装全部 Skills 到当前用户的 Codex：

```bash
npx skills@1.7.2 add liqlong/wyd-oms-skills --skill '*' --agent codex --global
```

先查看可安装列表：

```bash
npx skills@1.7.2 add liqlong/wyd-oms-skills --list
```

安装单个 Skill：

```bash
npx skills@1.7.2 add liqlong/wyd-oms-skills --skill oms-order-query --agent codex --global
```

CLI 也支持 `--agent claude-code` 等客户端；本版本的配置指南以 Codex 为准。
各客户端需要自行配置 OMS MCP；Codex 的 `agents/openai.yaml` 元数据不保证在其他客户端生效。
批量发货和包裹异常工单自带附件上传指引与脚本，在当前业务流程中完成上传并继续办理。

完整步骤、指定版本安装、手动安装、MCP 配置和常见问题见[安装指南](docs/installation.md)。
国内网络无法完成 GitHub 或 npm 下载时，可以使用[版本下载包](https://github.com/liqlong/wyd-oms-skills/releases)
手动安装，或由维护者提供同版本下载包；不需要 npm。

## 使用示例

连接服务后，在 Codex 中输入：

```text
$oms-order-query 查询我指定参考号的入库单状态
$oms-inventory-health 查看哪些 SKU 快断货，以及需要补多少货
$oms-inbound-managed 帮我整理这批到仓货物并办理入库预约
$oms-outbound-batch 读取这份订单表，先检查缺项和重复订单
$oms-return-recovery 每批 5 单查看未认领退件，图片列提供预览链接
$oms-package-exception 上传我提供的附件，并帮我整理指定包裹的地址更正工单
```

Skill 按用户指令及现有授权办理业务。查询请求不触发建单或处置；重复单据、
关键资料变化及未知执行结果按各 Skill 的业务规则处理。以 MCP 实际回执为准。
常用单据及标识明确时直接查询。列表结果会说明当前页和后续数据；要求全部结果或统计时，
Skills 按实际分页信息连续读取并报告进度，分页信息缺失时明确说明未确认范围。

## 服务与版本要求

- 客户端须支持 Agent Skills，并能连接 OMS MCP 的 Streamable HTTP 服务。
- `agents/openai.yaml` 中的 MCP 依赖名称为 `oms`；Codex 配置使用 `mcp_servers.oms`。
- 服务须提供对应 Skill 使用的工具及实时参数定义，业务范围由 MCP 认证决定。
- Codex 桌面端招领中心通过配套脚本将当前页图片缓存到本机，在清单中提供“预览图片”链接，
  默认不展开图片；模型读图可按需使用 `view_oms_return_image`。其他客户端按实际支持提供图片链接。
  本地图片缓存只读取查询返回的文件地址，不需要另行提供 Token；无法预览时保留原文件链接。
- 辅助脚本只需要 Python 3 标准库。订单表脚本离线整理资料；附件上传脚本需要
  与 MCP 连接一致的 `OMS_MCP_URL` 和 `OMS_MCP_TOKEN`。

版本变化见 [CHANGELOG.md](CHANGELOG.md)，当前版本见 [VERSION](VERSION)。
发布快照信息见 [SOURCE.json](SOURCE.json)。维护流程见[发布维护指南](docs/maintenance.md)。

## 反馈与许可

请通过 [GitHub Issues](https://github.com/liqlong/wyd-oms-skills/issues) 提交使用问题，附上版本、
客户端类型、Skill 名称和脱敏后的错误信息。不要提交 Token、客户订单、收件资料或附件原件。

允许从官方仓库或维护者提供的版本包下载、安装和使用，允许为本人或本组织的使用保留必要副本。
不授予修改、再分发、公开镜像、再许可或以本项目内容另行发布产品的权利；其他用途须取得权利人许可。
完整条款见 [LICENSE](LICENSE)。
