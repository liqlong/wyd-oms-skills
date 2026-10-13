# 安装与连接 OMS MCP

## 1. 准备客户端和服务

准备支持 Agent Skills 的客户端，以及你已获授权的 OMS MCP 地址和 Token。
服务由业务方部署；本仓库发布 Skills，不包含服务端、数据库配置或客户凭据。
先核对对应 Skill 所需工具是否已经部署，缺少时联系服务维护者。

自动安装需要 Node.js/npm；手动安装不需要 Node.js。运行辅助脚本需要 Python 3。

## 2. 安装 Skills

### 自动安装到 Codex

```bash
npx skills@1.7.2 add liqlong/wyd-oms-skills --skill '*' --agent codex --global
```

安装程序会提示安装方式；推荐保留完整文件夹。执行前查看已有安装，不覆盖其他同名 Skill。
省略 `--global` 可安装到当前项目。只安装一个 Skill 时，将 `'*'` 换成其名称。

安装固定的 `v1.0.0`：

```bash
npx skills@1.7.2 add https://github.com/liqlong/wyd-oms-skills/tree/v1.0.0/skills --skill '*' --agent codex --global
```

每个 Skill 文件夹都包含 [LICENSE](../LICENSE)，安装和备份时请一并保留。

### 手动安装及国内下载

1. 从 [Releases](https://github.com/liqlong/wyd-oms-skills/releases) 下载
   `wyd-oms-skills-v1.0.0.zip` 或 `.tar.gz`，以及 `SHA256SUMS`。
2. 在下载目录核对 SHA-256，然后解压版本包。例如 macOS：

   ```bash
   shasum -a 256 wyd-oms-skills-v1.0.0.zip
   ```

   将输出与 `SHA256SUMS` 中该文件对应的值比较。
3. 将解压目录中的每个 `skills/oms-*` 文件夹完整复制到 `~/.agents/skills/`。
   保留 `SKILL.md`、`agents/`、`references/` 和 `scripts/`，并保留版本包的 `LICENSE`。
   Windows 使用用户主目录下的 `.agents/skills/`。
4. 已存在同名目录时，先检查版本并备份；不要混合不同版本的文件。

也可克隆官方仓库后按相同方式复制或创建本机软链接：

```bash
git clone --branch v1.0.0 --depth 1 https://github.com/liqlong/wyd-oms-skills.git
```

网络无法访问 GitHub 时，请向维护者索取同版本包及校验值。
仓库目前不提供国内公共镜像；使用者不得自行公开镜像或再分发。

## 3. 配置 Codex MCP

在本机 `~/.codex/config.toml` 中添加以下配置，替换为业务方提供的 HTTPS 地址。
如已存在 `mcp_servers.oms`，修改原段落并保留其他 MCP 配置。

```toml
[mcp_servers.oms]
url = "https://your-oms-mcp.example.com/mcp"
env_http_headers = { Authorization = "OMS_MCP_TOKEN" }
startup_timeout_sec = 30
tool_timeout_sec = 600
```

将自己的 Token 配置到启动客户端的本机环境变量 `OMS_MCP_TOKEN`。
此 OMS MCP 使用原始 Token 作为 `Authorization` 值，不加 `Bearer `，
不使用自动添加 Bearer 前缀的 `bearer_token_env_var`。

macOS/zsh 中可隐藏输入后启动 CLI：

```zsh
read -rs 'OMS_MCP_TOKEN?输入 OMS MCP Token: '
echo
export OMS_MCP_TOKEN
codex
```

桌面应用从 Finder 启动通常不会继承终端环境变量。需要直接配置时，可将
`env_http_headers` 替换为以下本机配置，两种方式择一：

```toml
http_headers = { Authorization = "填写自己的原始 Token" }
```

Token 仅保存在自己的客户端配置或本机环境，不写入本仓库、Skill、聊天消息或问题反馈。
配置变化后重新连接 MCP 或重启客户端。此服务不使用 OAuth，无需 `codex mcp login oms`。

## 4. 确认安装和连接

- 在 Codex 中用 `/skills` 查看安装结果，CLI 中可用 `codex mcp list` 或 `/mcp` 查看连接。
- 先输入 `$oms-order-query 查看当前可用的 OMS 查询类型`，验证只读查询工具连接。
- 按真实单号或参考号进行只读查询；不要通过创建测试订单验证连通性。
- 新安装未出现时，重新开启会话或重启 Codex。

辅助脚本使用说明位于相应 Skill：订单表脚本需要 `--order-type TOC` 或 `TOB`；
附件上传脚本需要设置 `OMS_MCP_URL`（完整 `/mcp` 地址）和 `OMS_MCP_TOKEN`。
两者必须与已授权的 MCP 连接一致，只有用户已授权上传时才执行上传脚本。

## 5. 更新与排查

自动安装可使用 `npx skills@1.7.2 update -g`，按提示选择要更新的 Skills；
此命令会检查全部全局安装项目，注意核对选择。固定版本用户可下载新版包后完整替换相应目录。
更新前查看 [CHANGELOG](../CHANGELOG.md)，并核对新版 MCP 工具要求。

| 问题 | 处理方式 |
| --- | --- |
| 安装工具找不到 Skills | 用 `--list` 检查仓库；手动安装时确认没有多套一层目录 |
| Skill 未出现 | 核对目录和客户端版本，重新开启会话或重启 |
| MCP 认证失败 | 核对业务方提供的地址、原始 Token 及启用状态 |
| 缺少业务工具 | 部署相应版本的 OMS MCP，再重新连接 |
| 退件图片未展示 | 核对 `view_oms_return_image` 和客户端图片块支持；保留原图链接 |
| 文件脚本无法运行 | 安装 Python 3，并从 Skill 目录执行或使用脚本绝对路径 |

参考：[OpenAI 官方 Skills 文档](https://learn.chatgpt.com/docs/build-skills)、
[Codex MCP 配置](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)、
[Skills CLI](https://github.com/vercel-labs/skills)。
