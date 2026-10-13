# 建单参数和查询路由

实时 `describe_oms_outbound_operation` 是字段、默认值和条件必填项的依据。
这里说明容易混淆的业务结构，不复制完整schema。

## ToC

`create_oms_toc` 使用 `deliveryMethod`、`retailOrder`、`retailAddressee`、
`retailLogistics`、`retailGoodsTmpList`；数量字段为 `goodsNum`，SKU为 `skuNo`。
发货方式0普通、1自动分仓；面单类型0系统、1自上传。这两个选择没有通用默认值，先询问。

普通发货需要仓库、服务商、产品和平台；普通系统面单还需要快递服务（0我司、1第三方），
第三方需要真实账号。自动分仓仅支持我司快递和系统面单；客户自动分仓配置可以覆盖请求中的
匹配规则和仓库/渠道，由 OMS 执行，不承诺 MCP 指定值能覆盖该配置。
自动分仓规则未传时先沿用 OMS 配置，OMS 报缺失后再询问；不提前固定价格或时效优先。

`orderStatus` 默认1提交，0保存；分销账号普通发货由 OMS 强制提交，不承诺只保存草稿。
`retailLogistics.oneReference` 必填且去重，不自动生成。
`signatureService` 默认1不需要；ToC当前实现会把2转换成0普通签名，不能把2承诺为成人签名。
保险币种未传时由 OMS 按收件国家补全；业务库存类型未传时由 OMS 按客户配置决定。
自上传面单提供 `file.trackingNo` 及 `file.fileAddress` 或 `file.fileBase64`；
`fileStatus=0` 是在 OMS 后续上传面单的特殊保存方式，不能用于系统面单。
箱标附件使用 `packageFileList`；不是 ToB 的 `fileList`。

## ToB

`create_oms_tob` 使用 `deliveryType`、`deliveryStyle`、`deliveryWarehouseCode`、
`deliveryAddreVO`、`goodsList`、`platForm`；数量为 `goodsNum`，SKU为 `wydSkuNo`。
出库类型0普通、1 FBA、2转仓；发货方式0我司卡车、1我司快递、2自提卡车、
3自上传快递、4第三方快递。这些没有通用默认值，应询问或采用用户明确的资料。

`deliveryStatus` 默认1提交，0保存。`referenceNo` 非必填，询问后允许不提供；
不传隐藏兼容字段 `reference`，避免和 `referenceNo` 产生不同的优先级。
托盘数、贴标数默认0；库存类型不固定补12，而由 OMS 使用客户配置。
地址里 countryRegion、addressOne、postCode、city 在入口就必须提供，name在内部必填；
美国/加拿大需要州省，我司卡车或我司快递需要电话。指定收件仓后 OMS 可补全地址，
但不能把仍然必填的入口地址、姓名等当作可省略，不能填占位地址。

已指定快递渠道时按条件补齐服务商、产品；我司快递/第三方快递需要保险标识、签名服务。
它们没有通用默认值，不自动购买服务，也不以接口样例值代替用户选择。
附件用 `fileList`；每项提供类型及文件地址或Base64。BOL还需要BOL号、计划提货起止时间，
其他附件需要备注。自上传快递的面单需求由 OMS 现有校验决定，缺失时补齐实际资料。

## 只读查询

| 用途 | queryName |
| --- | --- |
| 当前客户可用发货仓 | `common_get_warehouse_by_customer` |
| 根据国家查询收件仓 | `common_get_tob_warehouse_code` |
| 收件仓详细资料 | `common_get_tb_tob_warehouse_msg` |
| 发货商品与包装资料 | `common_get_out_ware_house_goods_info`、`common_get_goods_info` |
| 仓库绑定服务商 | `common_get_provider_by_warehouse_code` |
| 服务商物流产品 | `common_get_logistics_products` |
| 第三方账号 | `common_get_third_part_account` |
| 费用试算及其物流列表 | `fee_query_trial`、`fee_trial_query_logistic` |
| ToC详情、列表 | `outbound_to_c_query`、`outbound_to_c_query_page` |
| ToB详情、列表 | `outbound_tob_query`、`outbound_tob_query_page` |

查询先查看实时参数定义。仓库国家筛选用实际响应字段，不向无参数的仓库查询传国家。
第三方账号按 warehouseCode、logisticsCode、productCode、platType 查询，不凭账号名称猜权限。
费用试算 `needSignature`：0不需要、1需要，与ToC/ToB建单 `signatureService` 不同，不能直接复制。
费用按本次试算结果与币种展示，没有真实包装资料不虚构试算。

ToC详情以 `orderNo` 或 `reference` 查询；主状态0待提交、1提交中、2已提交、3已拣货、
4已发货、5作废、6生成拣货单、7异常、8MQ异常。
ToB详情以 `orderNo` 传订单号或参考号；主状态0待提交、1已提交、2拣货、3签出、
4作废、5异常、6派送、7截单中、8已截单、9提交中。未知值保留原码。
跟踪号、面单及附件地址按实际详情响应展示，不以建单响应里的单号推断运单已生成。
