#!/usr/bin/env python3
"""将本次未认领退件查询中的图片缓存到本机，供 Codex Markdown 预览。"""

import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_ATTACHMENTS = 100
NON_IMAGE_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".zip"}


class PreviewError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def validate_url(source):
    if not isinstance(source, str) or len(source) > 8192 or any(ord(c) < 32 for c in source):
        raise PreviewError("图片地址无效")
    parsed = urllib.parse.urlsplit(source)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise PreviewError("图片地址必须是 HTTP/HTTPS 地址")
    if parsed.username or parsed.password or parsed.fragment:
        raise PreviewError("图片地址不能包含账号、密码或片段")
    # 原地址和每一次重定向都校验；不访问本机及内网地址。
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise PreviewError("图片地址指向本机、内网或保留地址")


def image_extension(data):
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return ".gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    raise PreviewError("附件不是支持的图片（JPG、PNG、WebP、GIF）")


def download_image(source):
    started = time.monotonic()
    opener = urllib.request.build_opener(NoRedirect())
    address = source
    for redirect in range(4):
        validate_url(address)
        # 文件请求不携带 MCP Token、OMS 凭据或浏览器 Cookie。
        request = urllib.request.Request(address, headers={"Accept": "image/*"})
        try:
            response = opener.open(request, timeout=5)
        except urllib.error.HTTPError as error:
            try:
                location = error.headers.get("Location")
                if error.code in (301, 302, 303, 307, 308) and location and redirect < 3:
                    address = urllib.parse.urljoin(address, location)
                    continue
                raise PreviewError("文件服务返回 HTTP {}，无法预览".format(error.code)) from None
            finally:
                error.close()
        with response:
            if response.status != 200:
                raise PreviewError("文件服务未返回完整图片")
            length = response.headers.get("Content-Length")
            if length and int(length) > MAX_IMAGE_BYTES:
                raise PreviewError("图片超过10MiB，请使用原文件链接")
            content = bytearray()
            while True:
                if time.monotonic() - started > 30:
                    raise PreviewError("图片读取超时")
                chunk = response.read(min(8192, MAX_IMAGE_BYTES + 1 - len(content)))
                if not chunk:
                    break
                content.extend(chunk)
                if len(content) > MAX_IMAGE_BYTES:
                    raise PreviewError("图片超过10MiB，请使用原文件链接")
            data = bytes(content)
            return data, image_extension(data)
    raise PreviewError("图片地址重定向过多")


def query_records(result):
    if not isinstance(result, dict) or result.get("queryName") != "inbound_center_query":
        raise PreviewError("请传入 query_oms 的 inbound_center_query 原始查询结果")
    if result.get("status") not in ("SUCCESS", "EMPTY"):
        raise PreviewError("招领查询未成功，不能生成预览")
    data = result.get("data")
    records = data.get("records") if isinstance(data, dict) else None
    if result.get("status") == "EMPTY" and records is None:
        return []
    if not isinstance(records, list) or len(records) > 100:
        raise PreviewError("请提供当前页的招领 records，最多100单")
    seen = set()
    for order in records:
        if not isinstance(order, dict) or str(order.get("processStatus")) != "0":
            raise PreviewError("候选中存在非未认领退件，请刷新清单")
        order_no = order.get("returnOrderNo")
        if not isinstance(order_no, str) or not order_no.strip() or order_no in seen:
            raise PreviewError("退件单号缺失或重复，请刷新清单")
        seen.add(order_no)
    return records


def attachments(order):
    groups = {"BOX": [], "GOODS": []}
    for file in order.get("fileDTOList") or []:
        groups["BOX"].append((file, {}))
    for detail in order.get("returnOrderDetailList") or []:
        for file in detail.get("fileInfoRspList") or []:
            groups["GOODS"].append((file, {
                "detailId": detail.get("id"), "goodsWydSku": detail.get("goodsWydSku"),
            }))
    return groups


def prepare_previews(records, directory, all_images=False):
    # 先核对整批数量，避免下载过程中才发现范围超限。
    grouped = [(order, attachments(order)) for order in records]
    if sum(len(files) for _, groups in grouped for files in groups.values()) > MAX_ATTACHMENTS:
        raise PreviewError("当前批次附件超过100个，请缩小查询范围")
    results = []
    for order, groups in grouped:
        item = {"returnOrderNo": order["returnOrderNo"], "previews": [],
                "attachmentCounts": {kind: len(files) for kind, files in groups.items()}}
        for kind, files in groups.items():
            for index, (file, detail) in enumerate(files, 1):
                source = file.get("src") if isinstance(file, dict) else None
                preview = {"imageType": kind, "imageIndex": index, **detail,
                           "fileName": file.get("oldName") if isinstance(file, dict) else None,
                           "sourceUrl": source}
                try:
                    # 明确的非图片附件只保留链接；未知扩展名由文件内容判断。
                    suffix = Path(urllib.parse.urlsplit(source or "").path).suffix.lower()
                    if suffix in NON_IMAGE_EXTENSIONS:
                        raise PreviewError("非图片附件，请使用原文件链接")
                    data, extension = download_image(source)
                    identity = "{}\n{}\n{}\n{}".format(order["returnOrderNo"], kind, index, source)
                    name = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24] + extension
                    path = directory / name
                    with path.open("xb") as output:
                        os.chmod(path, 0o600)
                        output.write(data)
                    preview.update(status="CACHED", localPath=str(path), size=len(data))
                except PreviewError as error:
                    preview.update(status="ERROR", message=str(error))
                except (OSError, ValueError, urllib.error.URLError):
                    # 底层异常可能带签名地址，不输出原始异常文本。
                    preview.update(status="ERROR", message="图片读取失败，请使用原文件链接核对")
                item["previews"].append(preview)
                if preview["status"] == "CACHED" and not all_images:
                    break
        results.append(item)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="查询结果 JSON 文件；默认从 stdin 读取")
    parser.add_argument("--output-dir", type=Path, help="缓存父目录；默认使用系统临时目录")
    parser.add_argument("--all-images", action="store_true", help="缓存所选退件的全部图片")
    args = parser.parse_args()
    try:
        if args.input:
            with args.input.open("rb") as stream:
                raw = stream.read(MAX_INPUT_BYTES + 1)
        else:
            raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise PreviewError("查询结果过大，请缩小范围")
        records = query_records(json.loads(raw))
        parent = args.output_dir.resolve() if args.output_dir else None
        if parent:
            parent.mkdir(parents=True, exist_ok=True)
        # 每次生成独立私有目录，防止翻页或刷新后展示旧批次图片。
        directory = Path(tempfile.mkdtemp(prefix="oms-return-previews-", dir=parent)).resolve()
        orders = prepare_previews(records, directory, args.all_images)
        cached = sum(preview["status"] == "CACHED" for item in orders for preview in item["previews"])
        failed = sum(preview["status"] == "ERROR" for item in orders for preview in item["previews"])
        print(json.dumps({"cacheDirectory": str(directory), "cachedImages": cached,
                          "failedAttachments": failed, "orders": orders}, ensure_ascii=False, indent=2))
        return 0
    except PreviewError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, AttributeError):
        print("无法生成退件预览，请检查当前页查询结果及本机目录。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
