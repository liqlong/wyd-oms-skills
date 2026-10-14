#!/usr/bin/env python3
"""读取用户文件并调用 MCP 上传工具；不打印文件内容或认证信息。"""

import argparse
import base64
import http.client
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.parse
import urllib.request

MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_RESPONSE_BYTES = 1024 * 1024
PROTOCOL_VERSION = "2025-06-18"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        # 避免重定向将 MCP Token 发送到另一个服务。
        return None


class McpUploadClient:
    def __init__(self, url, token):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in ("https", "http") or not parsed.hostname:
            raise ValueError("OMS_MCP_URL 必须是完整的 HTTP/HTTPS MCP 地址")
        if parsed.username or parsed.password or parsed.fragment:
            raise ValueError("MCP 地址不能包含账号、密码或片段")
        if not token or "\r" in token or "\n" in token:
            raise ValueError("请在本机环境配置有效的 OMS_MCP_TOKEN")
        self.url = url
        self.token = token
        self.session_id = None
        self.protocol_version = None
        self.opener = urllib.request.build_opener(NoRedirect())

    def send(self, message):
        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        if self.protocol_version:
            headers["MCP-Protocol-Version"] = self.protocol_version
        request = urllib.request.Request(
            self.url,
            data=json.dumps(message, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with self.opener.open(request, timeout=60) as response:
            session_id = response.headers.get("Mcp-Session-Id")
            if session_id:
                self.session_id = session_id
            if "id" not in message:
                return None
            content_type = response.headers.get("Content-Type", "")
            if "text/event-stream" in content_type:
                return self.read_event_response(response, message["id"])
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise ValueError("MCP 回执超过预期大小")
            return self.check_response(json.loads(body), message["id"])

    def read_event_response(self, response, expected_id):
        data_lines = []
        size = 0
        for line in response:
            size += len(line)
            if size > MAX_RESPONSE_BYTES:
                raise ValueError("MCP 回执超过预期大小")
            line = line.decode("utf-8").rstrip("\r\n")
            if line.startswith("data:"):
                data_lines.append(line[5:].lstrip(" "))
            elif not line and data_lines:
                event = json.loads("\n".join(data_lines))
                data_lines = []
                if event.get("id") == expected_id:
                    return self.check_response(event, expected_id)
        raise ValueError("未收到对应的 MCP 回执")

    @staticmethod
    def check_response(message, expected_id):
        if not isinstance(message, dict):
            raise ValueError("MCP 回执格式不正确")
        if message.get("id") != expected_id:
            raise ValueError("MCP 回执编号不匹配")
        if "error" in message:
            raise ValueError("MCP 调用失败，请检查连接、认证和工具版本")
        if "result" not in message:
            raise ValueError("MCP 回执缺少 result")
        return message["result"]

    def upload(self, file_name, content, purpose):
        initialized = self.send({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "oms-business-attachment-upload", "version": "1.0.0"},
            },
        })
        version = initialized.get("protocolVersion")
        if version not in ("2025-06-18", "2025-03-26", "2024-11-05"):
            raise ValueError("MCP 协议版本不兼容，请更新上传脚本")
        self.protocol_version = version
        self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return self.send({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {
                "name": "upload_oms_attachment",
                "arguments": {
                    "fileName": file_name,
                    "contentBase64": base64.b64encode(content).decode("ascii"),
                    "purpose": purpose,
                    "confirmed": True,
                },
            },
        })


def attachment_result(tool_result):
    if not isinstance(tool_result, dict):
        raise ValueError("MCP 上传回执格式不正确")
    if tool_result.get("isError"):
        raise ValueError("MCP 上传工具执行失败，请检查认证及服务配置")
    data = tool_result.get("structuredContent")
    if not isinstance(data, dict) or "status" not in data:
        for block in tool_result.get("content", []):
            if block.get("type") == "text":
                try:
                    candidate = json.loads(block.get("text", ""))
                except (ValueError, TypeError):
                    continue
                if isinstance(candidate, dict) and "status" in candidate:
                    data = candidate
                    break
    if not isinstance(data, dict) or data.get("status") not in ("SUCCESS", "ERROR", "UNKNOWN"):
        raise ValueError("未收到有效上传回执，不要自动重试")
    return {key: data.get(key) for key in (
        "status", "fileName", "fileUrl", "businessCode", "size", "code", "message"
    )}


def main():
    parser = argparse.ArgumentParser(description="通过 OMS MCP 上传用户授权的实际附件")
    parser.add_argument("file", type=Path)
    parser.add_argument("--purpose", required=True,
                        choices=("WORK_ORDER", "TOB_ATTACHMENT", "SHIPPING_LABEL"))
    parser.add_argument("--confirmed", action="store_true", help="用户已明确授权上传此文件")
    args = parser.parse_args()
    if not args.confirmed:
        parser.error("需要用户授权后才能传 --confirmed")
    try:
        if not args.file.is_file() or args.file.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("请提供单个实际文件，大小不能超过10MiB")
        with args.file.open("rb") as stream:
            content = stream.read(MAX_FILE_BYTES + 1)
        if not content or len(content) > MAX_FILE_BYTES:
            raise ValueError("文件不能为空，大小不能超过10MiB")
        client = McpUploadClient(os.environ.get("OMS_MCP_URL", ""), os.environ.get("OMS_MCP_TOKEN", ""))
        result = attachment_result(client.upload(args.file.name, content, args.purpose))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "SUCCESS" else 1
    except urllib.error.HTTPError as error:
        print("MCP HTTP 调用失败，状态码：{}；不自动重试。".format(error.code), file=sys.stderr)
    except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException):
        print("MCP 连接或响应异常，上传结果未确认，不要自动重试。", file=sys.stderr)
    except ValueError as error:
        print(str(error) + "；不要自动重试。", file=sys.stderr)
    except OSError:
        print("无法读取文件或完成上传，请检查本机文件及连接；不要自动重试。", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
