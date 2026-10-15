---
name: oms-inbound-managed
description: 通过 OMS MCP 办理入库预约、预约审核后的入库建单与提交，按需查看收货、上架和库存进度。用于约仓、预报SKU、提交入库草稿及查看入库全程状态；重复单据先展示给用户再决定下一步。
---

# OMS 智能入库托管

使用 OMS MCP 的 `describe_oms_inbound_operation`、`create_oms_inbound_appointment`、
`create_oms_inbound`、`submit_oms_inbound` 以及现有 `describe_oms_query`、`query_oms`。
工具名称可能包含 MCP 服务前缀。缺少工具时提示重新连接新版服务，不直接调用 OMS 或数据库。
MCP 提供按需能力；持续跟踪、定时执行、看板接入和通知由 Agent 层按客户需要定制脚本。

仅查预约状态时直接用 `inbound_appointment_query` 的 `inboundAppointmentNo` 或 `reference`；
仅查入库状态时直接用 `inbound_inbound_query` 的 `inboundNo`（单号或参考号），不先查目录、仓库或写操作定义。
其它只读查询字段不确定才查看schema，同一会话复用，翻页不重复获取。

新任务仅查已有单据时优先只读查询；办理预约、入库或在本流程中查进度时使用本Skill。
本次回执说明已执行动作、真实预约/入库编号、当前业务阶段及未完成步骤；
创建、提交成功与审核成功、收货完成、上架完成分别表述，不能跨阶段推断。

## 整理预约和货物资料

1. 查询 `common_get_warehouse_by_customer` 获取可用仓库；用户给仓库名称时匹配实际代码。
   SKU按需通过 `common_get_goods_info` 或商品详情核实，保留用户的箱号、托号、批次和序列号。
   未知过滤字段使用 `describe_oms_query` 核对，同一会话复用；不猜测 SKU 或客户范围。
2. 通过 `describe_oms_inbound_operation(operation)` 查看对应写操作的完整 `inputSchema`，
   严格按其字段、枚举和日期格式整理 `request`，不传凭据、`dataBelong` 或客户代码。
   业务信息不足时只询问本次必需内容，未明确的业务处理先询问用户。
3. 预约、建单的参考号均非必填。优先用用户提供的值；没有参考号时先询问，
   用户没有或不需要提供也可以继续，不自动生成，不强制用户补一个参考号。
4. 展示目的仓、头程、运输方式、ETA/ETD、货物类型、柜型、SKU和数量，以及准备执行的步骤。
   明确默认创建入库单会直接提交，用户要求只保存时使用 `inboundStatus: "0"`。
   用户已明确授权整个预约和建单流程时，按授权继续，不为同一操作重复确认；
   只授权预约时，不自动建入库单。仅查询或整理资料时不执行写操作。

## 创建预约并查看审核

- 调用 `create_oms_inbound_appointment(request, confirmed: true)`。
  必填及条件必填由实时schema和OMS校验：整柜需要柜型，拼箱/散货需要体积。
  `skuNum`为不同SKU数量，`packages`为件数，不能混用。
- 成功返回 `data.inboundAppointmentNo`，它是预约订单号。
  用 `query_oms` 的 `inbound_appointment_query` 查询该编号，条件字段为 `inboundAppointmentNo`；
  用户提供参考号时也可按 `reference` 查询。
- `inboundAppointmentStatus`：0待提交、1预约中、2审核成功、3审核失败、4已作废。
  只有状态2且实际返回 `appointmentNo` 时才继续建单；`inboundAppointmentNo`不能当作`appointmentNo`。
  审核中时展示当前状态和预约订单号，待用户再次查询或Agent定制脚本继续；不在对话中无限轮询。
  审核失败时展示实际返回原因，不自动修改资料、重新预约或作废单据。

## 创建入库单或提交草稿

- 使用已审核成功预约返回的 `appointmentNo`，目的仓应与预约一致。
  通过 `create_oms_inbound` 提交资料和 `inboundDetailTmpList`，每条包含真实 `wydSkuNo`、`goodsNum`。
  快递需要跟踪号；整柜/拼箱的柜号条件，以及拼箱/散货按箱或按托送仓的数量，遵循schema。
  不替用户选择收费的拆箱理货等服务；OMS默认不拆箱、需要上架。
- 默认 `inboundStatus: "1"` 表示创建并提交，成功后不再调用提交工具。
  用户明确只要草稿时设置 `"0"`，之后用户同意提交，再调用 `submit_oms_inbound(inboundNo, confirmed: true)`。
  工具会查询确认当前客户的单据仍为待提交状态0。
- 保存实际返回的 `inboundNo`、`inboundAppointmentNo`、`appointmentNo`，展示本次完成的步骤。
  预约与入库单是不同实体，不能以预约成功推断入库单已创建。

## 重复、作废重建和不确定结果

- `EXISTS`：展示返回的已有有效单据，本次没有重复创建；停止当前流程，由用户决定下一步。
  即使原请求授权整个流程，也不能自动复用已有单据、改资料或提交其草稿。
- 原单已作废、用户要求重新安排时，沿用原参考号，不自动加后缀或换号；
  新预约/入库单使用真实新编号，是否允许创建及一个预约关联一个入库单的规则由OMS校验。
  返回业务失败时展示错误，不能自行更换参考号绕过校验。
- `SUCCESS`：OMS确认操作成功，提交响应data为空仍代表成功；显示实际返回编号。
- `ERROR`：展示失败原因；已有前序成功步骤时保留其编号，只处理失败步骤，不能整段重跑。
- `UNKNOWN`：结果未确认，不直接重试。预约按参考号或已知预约订单号查询；
  建单按参考号查详情，或按真实预约号查入库列表；提交按入库单号查状态。
  无参考号且未收到预约订单号时，无法唯一查询本次预约，应说明并由用户在OMS核实。
  未查到或结果仍不明确时停止本次写操作，不将查询空结果直接当作创建失败。

## 按需查看收货、上架和库存

`inbound_inbound_query` 用 `inboundNo` 查询单号或参考号；列表可用 `inbound_inbound_query_page`
按 `billNum` 查询预约号、预约订单号、入库单号、柜号、跟踪号或参考号。
仅展示列表当前页时，结果下主动说明本页实际条数、页码、实际返回的总数及是否还有下一页；
有后续页提示可以说“下一页”，末页明确说明。分页信息缺失时说明后续页尚未确认，不编造总数。
用户要求全部列表或完整明细时保留条件继续翻页并说明进度，不逐页等待用户指令。

详情 `inboundStatus`：0待提交、1在途中、2收货中、3收货完成、4作废、5待处理、6处理中、
7处理完成、8已生成上架单、9上架完成、10上架中、11待上架；未知值保留原码。
状态3不代表已上架，主单状态9才表示上架完成。

保留预报 `boxingInfoApi`、实收 `receiptInfoApi` 各自的分页信息；明细不完整时继续翻页，
不要只凭主单状态宣称所有SKU和数量无差异。按实际SKU明细展示预报、实收、上架数量及
`warehouseExceptionInboundDTOList`，有分批收货时采用实际返回的累计口径，不重复加总。
涉及组件或无法匹配的明细时展示原始数据，不擅自按名称归并或调整数量。

需要最新库存时按实际仓库及SKU查询 `stock_warehouse_inventory_query`，
分开展示可用、在途、待上架、冻结及待出库数量；当前库存不是仅属于本入库单的库存。
结果在对话中展示；外部看板或自动上架通知需另行在Agent层定制，不修改OMS页面。
