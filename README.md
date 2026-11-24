# 零售货架陈列图像稽核采集平台

采集货架陈列图像，完成去重、检测、识别与排面计数，对照陈列标准输出缺货价签差异与证据包的图像稽核采集平台

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/WorkbenchView.vue|tsx  全部模块共享工作台
│   ├── src/data/modules.ts              18个业务模块配置
│   ├── src/api/              统一请求封装
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/resource.py  通用查询/导出/登记/动作接口
│   ├── app/services/<key>.py    每个模块独立领域逻辑
│   ├── app/services/base.py     共享服务骨架
│   └── app/store.py          内存数据仓库与示例数据
├── .gitignore
└── docker-compose.yml
```

## 启动

### 后端

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh
```

健康检查：`curl http://127.0.0.1:8000/api/health`

### 前端

```bash
cd frontend
npm ci
npm run dev
```

前端默认监听 `http://127.0.0.1:5173/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端 `http://127.0.0.1:8000`。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 门店名录 | `store_list` | 门店条目 | 门店编号、门店名称、所属区域 |
| 货架稽核任务 | `shelf_task` | 稽核任务 | 任务编号、门店标识、巡检日期 |
| 图像上传通道 | `image_upload` | 上传批次 | 批次编号、任务标识、图像张数 |
| 图像去重 | `image_dedup` | 去重记录 | 记录编号、图像指纹、相似簇号 |
| 货架检测 | `shelf_detect` | 检测记录 | 记录编号、图像指纹、层板数 |
| 商品识别 | `sku_recognize` | 识别记录 | 记录编号、陈列区域、候选商品码 |
| 排面计数 | `facing_count` | 计数记录 | 记录编号、陈列区域、商品码 |
| 陈列标准库 | `planogram_lib` | 陈列标准 | 标准编号、货架区段、商品码序列 |
| 缺货检查 | `gap_check` | 缺货记录 | 记录编号、陈列区域、缺货商品码 |
| 价签核对 | `price_tag_check` | 价签记录 | 记录编号、陈列位置、标价金额 |
| 稽核结果汇总 | `audit_result` | 稽核结论 | 结论编号、任务标识、达标项数 |
| 人工复核台 | `audit_review` | 复核事项 | 事项编号、争议记录、机器结论 |
| 巡检路线规划 | `field_route` | 路线记录 | 路线编号、区域集合、门店顺序 |
| 采集设备管理 | `device_mgr` | 采集设备 | 设备编号、设备型号、绑定巡检员 |
| 上传重试队列 | `upload_retry` | 重试项 | 队列编号、失败原因、重试次数 |
| 稽核证据包 | `evidence_pack` | 证据包 | 包编号、任务标识、图像清单 |
| 稽核导出中心 | `audit_export` | 导出任务 | 导出编号、数据范围、字段清单 |
| 门店得分卡 | `score_card` | 得分记录 | 记录编号、门店标识、稽核周期 |
| 稽核归档 | `audit_archive` | 归档记录 | 记录编号、归档范围、保留期限 |

## 约定

- 全部模块共享`frontend/src/views/WorkbenchView.vue|tsx`和一套资源路由。
- 每个模块仍保留独立`backend/app/services/<模块>.py`；纯前端保留
  `frontend/src/domain/<模块>.ts`，用于承载真实业务差异并维持36题位容量。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。

领域：数据工程
子方向：数据采集、爬虫与RPA
