# 常用订单查询

先用 `describe_oms_query` 核对实际参数，再执行 `query_oms`。下列 JSON 是工具参数，
不是 OMS 加密信封；MCP 会负责认证和加解密。

## 入库单和预约

“查下入库单状态，参考号：用户提供的参考号”（示例占位值，实际调用须使用用户提供的值）：

```json
{"queryName":"inbound_inbound_query","filters":{"inboundNo":"用户提供的参考号"}}
```

`inboundNo` 同时支持入库单号和参考号，不要改传不受支持的 `reference` 字段。
`inbound_inbound_query_page` 按 `billNum` 查询多个参考号、柜号、跟踪号或订单号，
按 `skuNo`、`inboundStatus`、`dateType`、`startDate`、`endDate` 组合筛选。
`dateType`: `"0"` 创建、`"1"` 提交、`"2"` ETA、`"3"` ETD、`"4"` 收货、`"5"` 更新。

入库预约使用 `inbound_appointment_query`，条件是 `inboundAppointmentNo` 或 `reference`。
预约和入库单属于不同实体，不能以预约成功推断收货或上架完成。

响应 `inboundStatus`: `0` 待提交、`1` 在途中、`2` 收货中、`3` 收货完成、
`4` 已作废、`5` 待处理、`6` 处理中、`7` 处理完成、`8` 已生成上架单、
`9` 上架完成、`10` 上架中、`11` 待上架，按当前入库中心实际枚举解释。
收货完成不能直接解释成所有 SKU 已上架；详情返回 `9` 才可按主单上架完成解释。
响应 `inboundAppointmentStatus`: `0` 待提交、`1` 预约中、`2` 预约成功、`3` 预约失败、`4` 作废。

## ToC 出库

单条详情使用 `outbound_to_c_query`；`orderNo` 和 `reference` 至少一个，同时传时 OMS 优先参考号。
通过 `query_oms` 查询，响应保留原始 `orderStatus`，按下方 ToC 状态映射解读。

```json
{"queryName":"outbound_to_c_query","filters":{"reference":"REF-001"}}
```

列表使用 `outbound_to_c_query_page`，多订单的详细信息使用 `outbound_to_c_query_details`。
条件包括 `orderNo`、`reference`、`skuNo`、`dateType`、`startDate`、`endDate`、
`orderStatus`、`checkStatus`、`pickingStatus`、`logisticsStatus`、`platForm`。
`dateType`: `"0"` 创建、`"1"` 提交、`"3"` 拣货、`"4"` 发货。
该列表没有通用 `warehouseCode` 参数，不能冒充支持按仓库直接筛选。

常用子状态与对应主状态：

| 子状态条件 | 必须搭配的 `orderStatus` | 可选子状态 |
| --- | --- | --- |
| `checkStatus` | `"0"` 待提交 | `"1"` 待审核、`"2"` 审核通过、`"3"` 审核驳回 |
| `holdType` | `"2"` 已提交 | `"2"` 截单失败 |
| `pickingStatus` | `"3"` 拣货 | `"1"` 待拣货、`"2"` 拣货中、`"3"` 已拣货、`"4"` 拣货异常 |
| `logisticsStatus` | `"4"` 派送 | `"0"` 已签出、`"1"` 已扫描、`"2"` 运输中、`"3"` 派送成功、`"4"` 派送失败 |

“查 2026-10-01 到 2026-10-08 创建、包含 SKU-001 的异常 ToC 订单”：

```json
{"queryName":"outbound_to_c_query_page","filters":{"skuNo":"SKU-001","orderStatus":"7","dateType":"0","startDate":"2026-10-01","endDate":"2026-10-08","pageNo":1,"pageSize":20}}
```

响应 `orderStatus`: `0` 待提交、`1` 提交中、`2` 已提交、`3` 已拣货、`4` 已发货、
`5` 已作废、`6` 生成拣货单、`7` 异常订单数据、`8` MQ服务异常订单数据。
某些响应码不在列表筛选枚举中，不自行把它们传给列表查询。

## ToB 出库

详情 `outbound_tob_query` 的 `orderNo` 支持 ToB 订单号或参考号。
列表 `outbound_tob_query_page` 用 `order` 查询单号或参考号，多个用逗号隔开；
SKU 条件为 `carefreeSku`，状态为 `deliveryStatus`，日期为 `timeType`、`startTime`、`endTime`。
`timeType`: `"0"` 创建、`"1"` 审核、`"2"` 拣货、`"3"` 发货、`"5"` 更新。
响应 `deliveryStatus`: `0` 待提交、`1` 已提交、`2` 已拣货、`3` 已签出、
`4` 已作废、`5` 异常出库单、`6` 已派送、`7` 截单中、`8` 已截单。
不要使用 ToC 的 `orderStatus` 码解释 ToB。

## 虚拟订单、退件及工单

- 虚拟详情 `outbound_virtual_query` 使用 `orderNumber` 或 `referenceNumber`。
  带附件详情使用 `outbound_virtual_query_with_file`，列表为 `outbound_virtual_page_query`。
- 退件 `inbound_return_query` 使用 `noStr` 查询退件单号、跟踪号或关联订单号，
  另有 `goodsWydSku`、`warehouseCode`、`processStatus` 和日期条件。
  响应 `processStatus`: `1` 已认领、`2` 处理中、`3` 处理完成、`4` 已过期。
  当前退件中心还可能返回 `0` 待认领、`5` 已作废、`6` 待仓库处理、`9` 待初审；
  这些是响应状态，退件列表筛选仍以 schema 当前允许的值为准。
- 退件预报使用 `inbound_return_forecast_query_page`；未认领招领清单使用
  `inbound_center_query`，`processStatus: "0"` 为未认领，`"4"` 为已过期，`"-1"` 为全部。
  查看可认领退件时固定使用 `processStatus: "0"`，单号筛选和翻页时也保留此条件。
- 拦截、改址、调查工单分别使用 `csc_package_interception_page_query`、
  `csc_address_correction_page_query`、`csc_package_trace_page_query`。
  `orderNoType4ExactMatch` 是数字：`1` 订单号、`2` 跟踪号、`5` 工单号；
  `orderNoList4ExactMatch` 是字符串数组。日期范围字段是毫秒时间戳。
- 增值服务单使用 `vas_to_bservice_page_query` 或 `vas_to_bservice_detail`。
  列表日期为毫秒时间戳，仓库列表的原字段名为 `warehosueCodeList`，保留这一拼写。

## 关联信息

按问题需要查询公共仓库、商品、库存、出入库流水或费用；完整类型见
[查询目录](query-catalog.md)。关联时使用接口实际返回的 SKU、单号及仓库代码，
不把名称当代码。只有问及费用时才增加费用查询；库存异常不等于订单异常。

查询有数据就按实际响应展示，没有数据就提示按本次条件未查到；接口报错时展示错误信息。
