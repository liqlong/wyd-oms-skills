# 退件操作、状态和数量口径

先用 `describe_oms_return_operation` 查看实时参数定义；查询先用 `describe_oms_query`。

| 业务动作 | MCP工具/查询 | OMS OpenAPI |
| --- | --- | --- |
| 创建退件预报 | `create_oms_return_forecast` | `/openapi/inbound/v1/returnForecast/create` |
| 预报和入仓查询 | `inbound_return_forecast_query_page` | `/openapi/inbound/v1/returnForecast/queryPage` |
| 未认领候选及图片 | `inbound_center_query` | `/openapi/inbound/v1/center/query` |
| 原生图片查看 | `view_oms_return_image` | 招领查询核对归属后，读取返回的原图地址 |
| 认领 | `claim_oms_return` | `/openapi/inbound/v1/center/receive` |
| 退件明细与进度 | `inbound_return_query` | `/openapi/inbound/v1/return/query` |
| 提交客户处置指令 | `process_oms_return` | `/openapi/inbound/v1/return/deal` |

预报的 `operateInstruct`：字符串1产品检查、4销毁，可省略，没有MCP默认值。
处置明细的 `processType`：字符串0上架、1销毁、2上架并暂存。
两者不是同一套枚举，不能将预报指令1误认为上架或将处置类型1误认为产品检查。

预报单号是 `rwcForecastNo`；招领及处置使用 `returnOrderNo`。
预报创建参考号必填，最多35字符；商品明细1至25条，数量须为正整数。
参考号或跟踪号已有预报时停止，由用户决定下一步；不自动重建已作废预报或生成新号。
用户明确要求新预报时使用其提供的新资料，是否允许创建继续由OMS校验。

退件主状态以现有退件中心枚举为准：0未认领、1已认领、2处理中、3处理完成、
5已作废、6待仓库处理、9待初审；接口兼容值4已过期按实际响应展示。
处理指令仅对当前客户的已认领状态1单据提交；其他状态查询进度，不重复处理。
注意查询接口的原生状态筛选仅支持其schema中列出的值；查看最新状态时可不传状态筛选。

查询明细中 `goodsStatus`：-1暂无检查、0货物良好、1外包装破损、2内容物破损。
`processResult`：0未操作、1已上架、2已销毁。
主单处理完成可能包含已上架和已销毁的不同明细，不能据此说全部商品都已上架。

处理请求只传 `returnOrderNo` 和完整 `detailList`；每项包括明细 `id`、`goodsWydSku`、
用户指定的 `processType`，备注按接口定义传入并以实际结果为准。
OMS核对当前整单明细，使用每条当前实际退回数量，不接受数量拆分参数。
明细ID须保留完整字符串，不能转成JavaScript浮点数；其他单据的ID不能混入。

上架指令提交后，仓库仍需实际执行。普通上架形成可用库存，上架并暂存形成暂存库存。
如用户后续发起寄回，由现有批量发货Skill办理，ToC在 `retailOrder.bizInventoryType`、
ToB在根字段 `bizInventoryType` 明确填整数1（仅退件）。查询并确认可用量，不默认使用良品或退件优先。
本招领Skill不等待仓库、不自动发货，也不根据库存或在售情况生成处置建议。
