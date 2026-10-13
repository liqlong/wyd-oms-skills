# 查询目录

本版本包含 52 个有效的只读 OMS OpenAPI 查询。先用 `describe_oms_query` 获取所选
类型的实时参数 schema；下表用于路由选择，不替代 schema。不支持创建、提交或修改单据。

## 单据

| queryName | 用途 |
| --- | --- |
| `inbound_appointment_query` | 入库预约详情 |
| `inbound_inbound_query` | 入库单详情，inboundNo 支持参考号 |
| `inbound_inbound_query_page` | 入库单列表，参考号/SKU/状态/日期 |
| `inbound_return_query` | 退件列表 |
| `inbound_return_forecast_query_page` | 退件预报列表 |
| `inbound_center_query` | 招领中心未认领或过期退件 |
| `outbound_to_c_query_distributor_user_name_list` | ToC 分销账号 |
| `outbound_to_c_query` | ToC 订单详情 |
| `outbound_to_c_query_details` | ToC 批量详情 |
| `outbound_to_c_query_page` | ToC 列表，SKU/状态/日期 |
| `outbound_tob_query` | ToB 订单详情 |
| `outbound_tob_query_page` | ToB 列表，SKU/状态/日期 |
| `outbound_virtual_query` | 虚拟订单详情 |
| `outbound_virtual_page_query` | 虚拟订单列表 |
| `outbound_virtual_query_with_file` | 虚拟订单及附件详情 |
| `csc_package_interception_page_query` | 包裹拦截工单列表，仅查询 |
| `csc_address_correction_page_query` | 地址更正工单列表，仅查询 |
| `csc_package_trace_page_query` | 包裹调查工单列表 |
| `vas_to_bservice_page_query` | 增值服务单列表 |
| `vas_to_bservice_detail` | 增值服务单详情 |

## 库存、商品及费用

| queryName | 用途 |
| --- | --- |
| `stock_adjustment_query_page` | 库存调整单列表 |
| `stock_adjustment_query` | 库存调整单详情 |
| `stock_check_orer_query_check_order_info` | 盘点主单信息 |
| `stock_check_orer_page_query_check_order_details` | 盘点明细分页 |
| `stock_warehouse_in_out_flow_query` | 出入库流水 |
| `stock_warehouse_inventory_flow_query` | 仓库库存流水 |
| `stock_warehouse_inventory_query` | 客户库存列表 |
| `stock_warehouse_inventory_batch_query` | 批次库存列表 |
| `stock_vas_query_inventory_goods` | 增值服务可用商品库存，仅查询 |
| `goods_goods_query` | 产品详情 |
| `goods_goodsgroup_query` | 组件产品详情 |
| `goods_goods_query_page` | 产品列表 |
| `goods_quality_get_column_info_by_id` | 产品类目属性 |
| `fee_query_fee_flow_page` | 费用流水 |
| `fee_query_trial` | 费用试算 |
| `fee_trial_query_logistic` | 试算物流信息 |
| `fee_query_storage_charge` | 仓租费用 |
| `fee_cost_flow_page_query_warehouse_detail_fee` | 仓租费用明细 |

## 公共资料

| queryName | 用途 |
| --- | --- |
| `common_get_warehouse_by_customer` | 客户可用仓库，无业务参数 |
| `common_get_all_warehouse_by_customer` | 客户所有仓库，无业务参数 |
| `common_get_category` | 商品类目，无业务参数 |
| `common_get_country_region` | 国家和地区，无业务参数 |
| `common_get_out_ware_house_goods_info` | 仓库内商品 |
| `common_get_goods_info` | 客户配置产品 |
| `common_get_provider_by_warehouse_code` | 仓库绑定的物流服务商 |
| `common_get_logistics_products` | 服务商物流产品 |
| `common_get_logistics_services` | 物流服务商 |
| `common_get_tb_tob_warehouse_msg` | ToB 仓库信息 |
| `common_get_third_part_account` | 第三方物流账号 |
| `common_get_tob_warehouse_code` | 按国家获取启用的 ToB 仓库 |
| `common_get_check_stock_goods` | 盘点可用产品 |
| `common_get_group_goods_list` | 可用元件商品 |

## 原接口差异

- `checkOrer` 和 `warehosueCodeList` 是原 OMS 接口拼写，不自行纠正。
- `common_get_tob_warehouse_code.type` 使用 schema 中的中文枚举，不能传数字 1/2。
- `common_get_group_goods_list` 的部分字段在原 DTO 中为整数，严格以 schema 为准。
- `hiddenInOmsDocs: true` 表示原文档隐藏但仍有效的接口，不代表废弃接口。
  已废弃的异常查询和旧盘点明细查询未收录。
