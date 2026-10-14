---
name: oms-package-exception
description: 通过 OMS MCP 办理包裹拦截、地址更正和包裹调查工单，收集订单、跟踪号、附件及改址资料，用户确认后创建或提交，并按需查询工单状态和处理反馈。
---

# OMS 包裹异常工单管家

使用 `describe_oms_package_exception_operation`、`create_oms_package_exception`、
`submit_oms_package_exception`，查询使用 `describe_oms_query` 和 `query_oms`，附件上传使用 `upload_oms_attachment`。
工具可能带 MCP 服务名前缀；缺少时提示连接新版服务，不调用 OMS Web 或数据库。
只办理包裹拦截、地址更正和包裹调查。接口名称及枚举见 [工单说明](references/work-orders.md)。

## 整理办理资料

- 按用户业务意图选择工单类型。订单取消和承运商包裹拦截是不同动作，不相互替代。
  包裹调查的类型不明确时，让用户选择催件、未收到、站点取件、退回、索取POD或其他问题。
- 先查看对应创建操作的实时参数定义。`businessOrderList` 必须包含真实 `businessOrderNo`
  和 `trackNo`；用户只给参考号或跟踪号时，先查询关联订单，确认实际订单号。
  候选不唯一或缺少跟踪号时请用户补充，不把参考号当业务订单号，不编造跟踪号。
- 拦截和调查需要说明。改址需要用户提供新地址，并按接口要求补齐地址1、邮编、城市、州/省。
  收件人、电话、国家等其他字段按用户实际更正内容填写，不自行从旧地址补齐或更改用户未指定的资料。
  展示拟提交的新收件信息，明确提醒用户核对。
- 三类工单都至少需要一个附件，最多五个。已有可用URL可直接使用；实际文件通过
  当前Skill按 [附件上传说明](references/attachment-upload.md) 调用 `upload_oms_attachment`，
  用途为 `WORK_ORDER`，取得原始文件名和真实URL后填写 `orderFileList` 并继续办理。
  大文件使用当前Skill自带的上传脚本，不要求用户安装或切换到独立上传Skill。
  上传失败或结果未确认时，先补齐附件，不提交缺少必需附件的工单。
  `chat` 是上传业务标识，不是 `fileCategory`；附件分类可省略，明确需要分类时按实际内容填写。

## 创建及处理已有工单

1. 查询关联订单及同类工单，让用户看到实际单号、跟踪号、工单状态和反馈。
   使用对应工单分页查询，按订单号精确筛选时 `orderNoType4ExactMatch=1`，
   `orderNoList4ExactMatch` 填业务订单号列表。查看查询定义后再传参，按需翻页。
2. 默认创建并提交（`submitFlag=2`）；用户要求只保存时使用1。
   展示工单类型、关联订单及跟踪号、说明/调查类型、新地址和附件，确认所选动作。
   用户已明确授权具体资料及动作时沿用授权，不重复询问。
3. 调用 `create_oms_package_exception(operation, request, confirmed: true)`。
   服务端会重新查询同类工单；`EXISTS` 表示本次没有创建，展示已有工单并停止。
   不自动跳过某些订单、修改、复用或提交已有工单。
4. 用户查看已有工单后仍明确要求另开新工单时，才传 `allowNewWhenExists: true`。
   核对需要新建的订单及资料后执行，是否允许创建由 OMS 继续校验。
   多个订单的说明、新地址或附件不同，应分别整理请求，不能共用不适用的资料。
5. 返回原始 `data.serviceOrderNoList` 及结果。用户只要求保存草稿时不再自动提交。
   `SUCCESS` 表示OMS接口确认本次操作成功，不表示承运商已完成拦截、改址或调查。
   若未返回工单号，用关联订单查询核实，不重复创建。

## 提交草稿和查询进度

- 用户要求提交已有草稿时，先按工单号精确查询：`orderNoType4ExactMatch=5`，
  `orderNoList4ExactMatch` 填真实服务工单号。确认工单类型、最新资料和 `orderStatus=1`。
  用户同意后调用 `submit_oms_package_exception(operation, serviceOrderNo, confirmed: true)`。
  服务端会核对当前客户的待提交工单；已提交或处理中不重复提交，不通过创建来提交旧草稿。
- 创建直接提交成功后只查询处理进度，不再调用草稿提交工具。
- 展示实际工单号、业务订单号、跟踪号、`orderStatus`、`processResolved` 和
  `processRecordList` 返回的处理内容、时间、附件及反馈。状态按相应工单枚举解释，未知值保留原码。
  没有返回反馈或附件时就说明未返回，不根据物流状态另行判断工单处理结果。
- `ERROR` 展示接口或校验原因，补充资料后再由用户决定继续。
  `UNKNOWN` 先按业务订单号（创建）或工单号（提交）查询最新结果；不自动重发写请求。
  未查到也不能据此断定上次创建失败，向用户说明并由用户决定下一步。
- 本期按需办理和查询，不生成每日台账，不做定时催办、后台轮询或通知发送。
