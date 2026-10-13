# 工单操作和查询

| 工单类型 | 创建操作 | 草稿提交操作 | 查询名称 |
| --- | --- | --- | --- |
| 包裹拦截 | `create_oms_package_interception` | `submit_oms_package_interception` | `csc_package_interception_page_query` |
| 地址更正 | `create_oms_address_correction` | `submit_oms_address_correction` | `csc_address_correction_page_query` |
| 包裹调查 | `create_oms_package_trace` | `submit_oms_package_trace` | `csc_package_trace_page_query` |

写操作全部通过 `/openapi/csc/v2/` 接入，不使用Web内部接口。
用 `describe_oms_package_exception_operation` 查看当前字段定义，不能只根据本参考猜参数。

`submitFlag=1` 仅保存，`submitFlag=2` 创建并提交，默认2。
`orderStatus=1` 是工单待提交，不能与业务订单的待提交状态0混用。

三类工单的状态1待提交、2待处理、3提交服务商、4处理成功、5处理失败、9处理中、
10已提交-未受理、11已提交-已受理；包裹调查另有6待客户运营处理。
这些含义来自工单枚举，不依据收件、物流或订单主状态推导。
`processResolved` 和每条反馈的 `singleProcessResolved` 按原始响应展示，未核实的码不自行翻译。

调查类型：1催件与查询、2未收到包裹、3站点取件、4包裹退回、5索取POD签收凭证、6其他问题。

附件结构：`fileName`、`fileUrl`，以及可选 `fileCategory`。
常用分类1发票或平台交易截图、2物流截图、3客户未收到聊天截图、4收件人未收到声明、
5POD派送证明、6外包装破损照片、7箱内商品破损照片、8外箱面单照片。
上传回执中 `businessCode=chat` 不能填入附件分类。资料不能唯一确定分类时询问用户或省略可选分类。

分页查询以 `records` 返回工单，保留原始数据及分页信息。
精确查询类型：1业务订单号、2跟踪号、5服务工单号；单号列表配套填写。
日期类型4创建时间、5提交时间，时间范围为毫秒时间戳，按用户实际时区转换。
查询不会自行添加OMS未提供的状态或超时筛选条件。

拦截、改址的附件按实际 `orderFileList` 展示；调查反馈的附件位于实际返回的处理记录中。
业务订单查询复用ToC/ToB详情及列表，先查看查询定义，拿到真实订单号和跟踪号后再填建单资料。
