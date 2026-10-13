#!/usr/bin/env python3
"""离线读取订单表并归并同一序号的 SKU，不访问 OMS、不执行建单。"""

import argparse
import csv
import io
import json
import posixpath
import re
import zipfile
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.etree import ElementTree as ET

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# OMS 模板字段名和中文表头。按表头映射，避免模板调整列序后错填收件资料。
TOC_FIELDS = {
    "序号": "serialNumber", "发货方式": "deliveryMethod",
    "自动分仓状态": "retailOrder.automaticWareHouseStatus",
    "自动分仓匹配规则": "retailOrder.automaticWareHouseStatus",
    "发货仓代码": "retailOrder.warehouse", "库存类型": "retailOrder.bizInventoryType",
    "订单备注": "retailOrder.remarks", "加急订单": "retailOrder.urgentChannel",
    "目的国家/地区": "retailAddressee.country", "姓名": "retailAddressee.name",
    "公司名称": "retailAddressee.companyName", "地址1": "retailAddressee.oneAddress",
    "地址2": "retailAddressee.twoAddress", "门牌号": "retailAddressee.houseNo",
    "邮政编码": "retailAddressee.postalCode", "城市": "retailAddressee.city",
    "州/省": "retailAddressee.province", "电子邮件": "retailAddressee.eMail",
    "联系电话": "retailAddressee.contactNo", "面单获取方式": "retailLogistics.faceSheetType",
    "快递服务": "retailLogistics.expressDeliveryService", "物流服务商": "retailLogistics.serviceProvider",
    "物流产品": "retailLogistics.product", "快递保险金额": "retailLogistics.insurance",
    "是否购买快递保险": "insuranceFlagFromSheet", "币种": "retailLogistics.insuranceCurrency",
    "签名服务": "retailLogistics.signatureService", "退货面单服务": "retailLogistics.needReturnLabel",
    "平台订单号": "retailLogistics.platformOrderNo", "电商平台": "retailLogistics.commercePlatform",
    "平台账号": "retailLogistics.accountName", "店铺号": "retailLogistics.shopNo",
    "ebay平台交易id": "retailLogistics.ebayTradeId", "ebay平台交易号": "retailLogistics.ebayTradeNo",
    "参考号1": "retailLogistics.oneReference", "参考号2": "retailLogistics.twoReference",
    "SKU": "goods.skuNo", "数量": "goods.goodsNum", "生产批次号": "goods.bnNo",
    "产品序列号": "goods.snNo", "追踪号": "file.trackingNo", "面单地址": "file.fileAddress",
    "分销账号": "distributorUserName", "提交状态": "orderStatus",
}
TOB_FIELDS = {
    "序号": "serialNumber", "出库类型": "deliveryType", "发货方式": "deliveryStyle",
    "发货仓代码": "deliveryWarehouseCode", "平台": "platForm", "库存类型": "bizInventoryType",
    "仓库代码": "deliveryAddreVO.warehouseCode", "目的国家/地区": "deliveryAddreVO.countryRegion",
    "邮政编码": "deliveryAddreVO.postCode", "州/省": "deliveryAddreVO.province",
    "城市": "deliveryAddreVO.city", "地址1": "deliveryAddreVO.addressOne",
    "地址2": "deliveryAddreVO.addressTwo", "门牌号": "deliveryAddreVO.houseNum",
    "公司名称": "deliveryAddreVO.corporateName", "姓名": "deliveryAddreVO.name",
    "联系电话": "deliveryAddreVO.contactNum", "电子邮件": "deliveryAddreVO.email",
    "发货号": "sendNo", "参考号": "referenceNo", "订单备注": "remarks",
    "SKU": "goods.wydSkuNo", "数量": "goods.goodsNum", "生产批次号": "goods.bnNo",
    "产品序列号": "goods.snNo", "Code": "goods.remarkCode", "提交状态": "deliveryStatus",
    "物流服务商": "deliveryExpressDTO.serviceProvider", "物流产品": "deliveryExpressDTO.product",
    "签名服务": "deliveryExpressDTO.signatureService", "是否购买快递保险": "deliveryExpressDTO.insuranceFlag",
    "快递保险金额": "deliveryExpressDTO.insurance", "币种": "deliveryExpressDTO.insuranceCurrency",
    "平台账号": "deliveryExpressDTO.accountName", "店铺号": "deliveryExpressDTO.shopNo",
}
INTEGER_FIELDS = {"goodsNum", "bizInventoryType", "needReturnLabel", "totalNumberLabels", "coveredNumberLabels"}
NUMBER_FIELDS = {"insurance", "cod"}
ENUM_VALUES = {
    "deliveryMethod": {"普通发货": "0", "自动分仓": "1", "自动分仓发货": "1"},
    "automaticWareHouseStatus": {"价格优先": "1", "时效优先": "2", "先进先出": "3"},
    "faceSheetType": {"系统生成面单": "0", "系统生成": "0", "自己上传": "1", "自上传": "1"},
    "expressDeliveryService": {"我司快递": "0", "无忧达快递": "0", "第三方平台快递": "1"},
    "deliveryType": {"普通出库": "0", "FBA出库": "1", "转仓出库": "2"},
    "deliveryStyle": {"我司卡车": "0", "我司快递": "1", "自提卡车": "2", "自上传快递": "3", "第三方快递": "4"},
    "signatureService": {"普通签名": "0", "不需要": "1", "成人签名": "2"},
    "bizInventoryType": {"仅退件": "1", "仅良品": "2", "退件优先": "11", "良品优先": "12"},
    "needReturnLabel": {"不需要": "0", "需要": "1"},
    "orderStatus": {"保存": "0", "提交": "1"}, "deliveryStatus": {"保存": "0", "提交": "1"},
    "insuranceFlag": {"不购买": "0", "购买": "1", "不需要": "0", "需要": "1", "NO": "0", "YES": "1"},
    "insuranceFlagFromSheet": {"不购买": "0", "购买": "1", "不需要": "0", "需要": "1", "NO": "0", "YES": "1"},
}


def header_key(value):
    return re.sub(r"[\s*＊]", "", value).casefold()


def coordinate(value):
    match = re.fullmatch(r"([A-Z]+)([1-9]\d*)", value)
    if not match:
        raise ValueError("XLSX 单元格位置无效")
    col = 0
    for letter in match[1]:
        col = col * 26 + ord(letter) - ord("A") + 1
    return int(match[2]), col - 1


def read_xlsx(path, sheet_name):
    with zipfile.ZipFile(path) as archive:
        if sum(entry.file_size for entry in archive.infolist()) > 100 * 1024 * 1024:
            raise ValueError("订单表解压后超过100MB，请拆分文件")
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        sheets = workbook.findall("s:sheets/s:sheet", NS)
        if not sheets:
            raise ValueError("XLSX文件没有可读取的工作表")
        selected = next((s for s in sheets if s.attrib["name"] == sheet_name), None) if sheet_name else sheets[0]
        if selected is None:
            raise ValueError("未找到指定工作表")
        relations = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rid = selected.attrib["{" + REL_NS + "}id"]
        target = next(r.attrib["Target"] for r in relations if r.attrib["Id"] == rid)
        member = target.lstrip("/") if target.startswith("/") else posixpath.normpath("xl/" + target)
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in item.iterfind(".//s:t", NS)) for item in strings]
        formats = {}
        styles = []
        if "xl/styles.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/styles.xml"))
            formats = {f.attrib["numFmtId"]: f.attrib["formatCode"] for f in root.findall("s:numFmts/s:numFmt", NS)}
            styles = [formats.get(f.get("numFmtId"), "") for f in root.findall("s:cellXfs/s:xf", NS)]
        sheet = ET.fromstring(archive.read(member))
        cells = {}
        for cell in sheet.findall(".//s:sheetData/s:row/s:c", NS):
            row, col = coordinate(cell.attrib["r"])
            if row > 10002 or col > 300:
                raise ValueError("订单表超过10000行或300列，请拆分文件")
            if cell.find("s:f", NS) is not None:
                raise ValueError("订单表含公式，请先保存为值；位置：" + cell.attrib["r"])
            value = cell.findtext("s:v", "", NS)
            if cell.get("t") == "s":
                value = shared[int(value)]
            elif cell.get("t") == "inlineStr":
                value = "".join(t.text or "" for t in cell.iterfind(".//s:t", NS))
            elif value and styles:
                fmt = styles[int(cell.get("s", "0"))]
                # 保留邮编、参考号等纯零占位格式的前导零；其他数字不擅自改变格式。
                if re.fullmatch(r"0+", fmt) and re.fullmatch(r"\d+", value):
                    value = value.zfill(len(fmt))
            cells[(row, col)] = value
        for merged in sheet.findall("s:mergeCells/s:mergeCell", NS):
            start, end = merged.attrib["ref"].split(":")
            r1, c1 = coordinate(start)
            r2, c2 = coordinate(end)
            if r2 > 10002 or c2 > 300:
                raise ValueError("合并单元格范围过大")
            for row in range(r1, r2 + 1):
                for col in range(c1, c2 + 1):
                    cells[(row, col)] = cells.get((r1, c1), "")
        width = max((col for _, col in cells), default=-1) + 1
        height = max((row for row, _ in cells), default=0)
        return [[cells.get((row, col), "") for col in range(width)] for row in range(1, height + 1)]


def read_rows(path, sheet_name):
    if path.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("订单文件超过20MB，请拆分文件")
    if path.suffix.lower() == ".xlsx":
        return read_xlsx(path, sheet_name)
    if path.suffix.lower() != ".csv":
        raise ValueError("支持XLSX、CSV；旧XLS文件请先另存为XLSX")
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("gb18030")
    rows = list(csv.reader(io.StringIO(text)))
    if len(rows) > 10002 or any(len(row) > 300 for row in rows):
        raise ValueError("订单表超过10000行或300列，请拆分文件")
    return rows


def set_path(target, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


def convert_value(path, value):
    key = path.rsplit(".", 1)[-1]
    value = ENUM_VALUES.get(key, {}).get(value, value)
    if key in INTEGER_FIELDS or key in NUMBER_FIELDS:
        try:
            number = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("需要填写数值") from exc
        if not number.is_finite():
            raise ValueError("数值无效")
        if key in INTEGER_FIELDS:
            if number != number.to_integral_value():
                raise ValueError("需要填写整数")
            return int(number)
        return float(number)
    return value


def parse_orders(rows, order_type, header_row, common):
    fields = TOC_FIELDS if order_type == "TOC" else TOB_FIELDS
    aliases = {header_key(label): path for label, path in fields.items()}
    for path in fields.values():
        aliases[header_key(path)] = path
        aliases[header_key(path.rsplit(".", 1)[-1])] = path
    aliases.update({"serialnu": "serialNumber", "sku": "goods.skuNo" if order_type == "TOC" else "goods.wydSkuNo"})
    if not 1 <= header_row <= len(rows):
        raise ValueError("表头行超出文件范围")
    headers = rows[header_row - 1]
    columns = [aliases.get(header_key(value)) for value in headers]
    mapped = [path for path in columns if path]
    if len(mapped) != len(set(mapped)):
        raise ValueError("多个表头映射到同一字段，请检查重复列")
    if "serialNumber" not in mapped:
        raise ValueError("需要序号列，用于归并同一订单的多行SKU；不会自动按相邻行猜订单")
    ignored = [label for label, path in zip(headers, columns) if label.strip() and not path]
    grouped = {}
    issues = []
    for row_no, row in enumerate(rows[header_row:], header_row + 1):
        if not any(str(value).strip() for value in row):
            continue
        values = {}
        for col, path in enumerate(columns):
            raw = str(row[col]).strip() if col < len(row) else ""
            if not path or not raw:
                continue
            try:
                values[path] = convert_value(path, raw)
            except ValueError as exc:
                issues.append({"row": row_no, "field": path, "message": str(exc)})
        serial = values.pop("serialNumber", None)
        if not serial:
            issues.append({"row": row_no, "field": "serialNumber", "message": "请填写订单序号"})
            continue
        group = grouped.setdefault(serial, {"serialNumber": serial, "rows": [], "fields": {}, "goods": []})
        group["rows"].append(row_no)
        goods = {}
        for path, value in values.items():
            if path.startswith("goods."):
                goods[path[6:]] = value
            elif path in group["fields"] and group["fields"][path] != value:
                issues.append({"row": row_no, "serialNumber": serial, "field": path, "message": "同一序号的订单资料不一致，请确认"})
            else:
                group["fields"][path] = value
        if goods:
            group["goods"].append(goods)
        else:
            issues.append({"row": row_no, "serialNumber": serial, "field": "goods", "message": "本行没有SKU及数量资料"})
    orders = []
    references = {}
    for group in grouped.values():
        request = deepcopy(common)
        flag = group["fields"].pop("insuranceFlagFromSheet", None)
        for path, value in group["fields"].items():
            set_path(request, path, value)
        amount = request.get("retailLogistics", {}).get("insurance")
        if amount is not None and not isinstance(amount, (int, float)):
            issues.append({"serialNumber": group["serialNumber"], "field": "insurance", "message": "保险金额需要填写数值"})
        elif flag is not None and flag not in {"0", "1"}:
            issues.append({"serialNumber": group["serialNumber"], "field": "insuranceFlag", "message": "请确认是否购买保险，不能丢弃该选择"})
        elif (flag == "1" and (amount is None or amount <= 0)) or (flag == "0" and amount is not None and amount > 0):
            issues.append({"serialNumber": group["serialNumber"], "field": "insurance", "message": "保险标识与金额需确认，ToC接口以保险金额决定是否购买"})
        request["retailGoodsTmpList" if order_type == "TOC" else "goodsList"] = group["goods"]
        reference = request.get("retailLogistics", {}).get("oneReference") if order_type == "TOC" else request.get("referenceNo")
        if reference:
            if reference in references:
                issues.append({"serialNumber": group["serialNumber"], "field": "reference", "message": "与序号" + references[reference] + "的参考号重复，整批需由用户决定"})
            else:
                references[reference] = group["serialNumber"]
        orders.append({"serialNumber": group["serialNumber"], "rows": group["rows"], "request": request})
    return {"orderType": order_type, "total": len(orders), "orders": orders, "issues": issues,
            "unmappedColumns": ignored, "message": "仅整理资料，尚未创建订单；请核对未映射列并调用MCP预检查"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--order-type", required=True, choices=["TOC", "TOB"])
    parser.add_argument("--sheet", help="XLSX工作表名称，默认第一张")
    parser.add_argument("--header-row", type=int, default=1)
    parser.add_argument("--common-json", type=Path, help="用户已提供的通用OMS参数JSON；表内非空值优先")
    parser.add_argument("--output", type=Path, help="离线资料JSON输出路径；省略时输出到终端")
    args = parser.parse_args()
    try:
        common = json.loads(args.common_json.read_text(encoding="utf-8")) if args.common_json else {}
        if not isinstance(common, dict):
            raise ValueError("通用参数必须是JSON对象")
        result = parse_orders(read_rows(args.file, args.sheet), args.order_type, args.header_row, common)
    except (ValueError, TypeError, AttributeError, OSError, KeyError, IndexError, StopIteration, zipfile.BadZipFile, ET.ParseError) as exc:
        parser.exit(2, "订单表读取失败：" + str(exc) + "\n")
    content = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(content + "\n", encoding="utf-8")
        print(json.dumps({"output": str(args.output), "orders": result["total"], "issues": len(result["issues"])}, ensure_ascii=False))
    else:
        print(content)


if __name__ == "__main__":
    main()
