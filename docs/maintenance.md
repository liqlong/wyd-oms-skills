# 发布维护

本指南供权利人及获授权的维护者使用，不扩大 [LICENSE](../LICENSE) 授予使用者的权限。

## 更新 Skills

以 `oms-mcp-server/skills/` 为业务指令来源，保留所有辅助资源。
先检查源项目未提交改动，按本次发布范围复制当前快照，不更改源项目或复制服务端配置。
更新后核对所有 MCP 工具与部署版本的兼容性，并在变更记录中说明新依赖。

`SOURCE.json` 记录源提交及已发布 Skill 文件的 SHA-256；源提交有未提交 Skill 改动时必须注明，
不能声称文件完全等同于源提交。通过实际文件哈希确认快照。
发布时如替换可能关联真实业务的示例编号，须记录 `publicationAdjustments`、
原始 `sourceFiles` 和发布后的 `files` 哈希；不修改源项目的业务指令。

## 校验与版本

在临时虚拟环境安装维护依赖后运行：

```bash
python3 -m venv /tmp/wyd-oms-skills-validate
/tmp/wyd-oms-skills-validate/bin/python -m pip install -r requirements-dev.txt
/tmp/wyd-oms-skills-validate/bin/python scripts/validate_skills.py
/tmp/wyd-oms-skills-validate/bin/python scripts/build_release.py
```

维护依赖只用于仓库校验；用户安装 Skills 不需要 PyYAML。
校验包含格式、元数据、资源引用、业务指令快照和 Python 语法，不代表已完成真实 OMS 业务测试。
修改辅助脚本时，应另行验证真实输入行为；不要用线上建单测试发布包。

当前处于开发阶段，统一使用初始版本 `1.0.0`，同步 Skills 时不升级版本号、不更新 `CHANGELOG.md`。
保持 `SOURCE.json` 的来源提交、实际文件哈希及快照日期与当前内容一致。

## GitHub Release

1. 完成本地校验，将最新 Skills 和发布快照提交到 `main`，保留初始版本号。
2. Skills、配套文档、构建脚本或发布配置变化时自动触发 Release 工作流。
3. Release 工作流再次校验并构建 ZIP、TAR.GZ 及 `SHA256SUMS`，将 `v1.0.0` 标签和下载包刷新到该提交。
4. 从 Release 下载实际包，核对校验值、6 个 Skill 及资源完整性，再验证公开仓库的安装。

工作流只将 `skills/`、安装文档、许可、版本、更新记录和来源快照打包。
下载包不包含维护依赖、CI 配置、凭据或本机临时验证资料。
国内下载包由权利人提供，使用同一份 Release 文件和校验值。
也支持维护者手动推送版本标签触发发布；标签须与 `VERSION` 一致。
开发阶段由 `DEVELOPMENT_RELEASE=true` 控制初始版本刷新；工作流串行执行，避免并发替换下载包。
进入稳定交付阶段后，应关闭该选项，恢复正式版本管理；关闭时已发布版本不会被覆盖。
