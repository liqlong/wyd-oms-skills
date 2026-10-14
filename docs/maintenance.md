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

按版本变化更新 `VERSION` 和 `CHANGELOG.md`：兼容性破坏升级主版本，新能力升级次版本，
兼容的修正升级补丁版本。初次发布为 `1.0.0`。

## GitHub Release

1. 完成本地校验，更新 `VERSION` 并与全部发布内容一同提交到 `main`。
2. `VERSION` 在 `main` 上变化时自动触发 Release 工作流；首次提交也会触发。
3. Release 工作流再次校验并构建 ZIP、TAR.GZ 及 `SHA256SUMS`，在该提交创建版本标签和 GitHub Release。
4. 从 Release 下载实际包，核对校验值、6 个 Skill 及资源完整性，再验证公开仓库的安装。

工作流只将 `skills/`、安装文档、许可、版本、更新记录和来源快照打包。
下载包不包含维护依赖、CI 配置、凭据或本机临时验证资料。
国内下载包由权利人提供，使用同一份 Release 文件和校验值。
也支持维护者手动推送版本标签触发发布；标签须与 `VERSION` 一致。
已正式发布的版本不会覆盖下载文件，内容修正须升级版本。
