# Satellite Simulation

Satellite Simulation 是一个基于 PySide6、PyVista 和 SGP4 的卫星网络仿真工具。它提供三维地球与卫星链路可视化、Walker 星座生成、TLE 文件加载、链路表格查看、Redis 实时链路指标查询，以及离线链路状态数据集导出。

## 功能概览

- 三维可视化卫星位置、星间链路和选中链路。
- 支持从 TLE 文件加载真实卫星轨道。
- 支持生成 Walker 星座，参数包括卫星总数、轨道面数、相位因子、高度和倾角。
- 使用 Grid Delta 拓扑策略生成星间链路。
- 可启用纬度熔断，在高纬区域断开异轨链路。
- 链路表格展示链路端点、延迟、Redis 查询状态等信息。
- 支持 Redis 或 SSH 隧道 Redis 查询链路指标。
- 支持导出 Walker 星座的离线链路状态数据集。

## 环境安装

项目提供 Conda 环境文件：

```bash
conda env create -f environment.yml
conda activate satsim
```

如果环境已存在，可以更新依赖：

```bash
conda env update -f environment.yml --prune
```

主要依赖包括：

- Python 3.11
- NumPy
- PySide6
- VTK
- PyVista
- PyVistaQt
- sgp4
- redis
- sshtunnel

## 启动

```bash
python main.py
```

Linux Wayland 环境下，程序会自动尝试切换到 X11 后端以提升 Qt/VTK 兼容性。

## 基本使用

### 生成 Walker 星座

菜单路径：

```text
数据 -> 生成 Walker 星座
```

可设置：

- `Total Satellites (T)`：卫星总数
- `Orbital Planes (P)`：轨道面数量
- `Phase Factor (F)`：相位因子
- `Altitude`：轨道高度，单位 km
- `Inclination`：轨道倾角，单位度

注意：卫星总数必须能被轨道面数整除。

### 加载 TLE 文件

菜单路径：

```text
数据 -> 加载 TLE
```

支持 `.txt` 和 `.tle` 文件。程序会解析两行根数，并用 SGP4 推进卫星位置。

### 设置拓扑

菜单路径：

```text
拓扑 -> 拓扑设置
```

当前拓扑策略为 `Grid Delta`。可选开启 `Latitude Fuse`，当链路端点处于指定纬度阈值以上时，异轨链路会被熔断。

### 运行仿真

菜单路径：

```text
仿真 -> 开始
仿真 -> 步长设置
```

`开始` 会按固定时间间隔推进仿真。`步长设置` 用于设置每次推进的仿真时间步长，单位秒。

## 导出链路状态数据集

菜单路径：

```text
仿真 -> 导出数据集
```

该功能只支持 Walker 星座。导出前需要先通过 `生成 Walker 星座` 生成星座。

导出参数：

- `时间片数量`：导出的时间片数量
- `仿真总时长`：总仿真时长，单位秒
- `Enable Random Link Failure`：是否启用随机链路失效
- `Down Probability / Slice`：每个时间片的链路失效概率
- `Random Seed`：随机种子
- `Save To`：输出目录

输出目录格式：

```text
LinkDataset_YYYYMMDD_HHMMSS/
  satellite_10101.txt
  satellite_10102.txt
  ...
```

每个卫星一个文件，记录该卫星固定 4 个邻居在各时间片的链路状态。链路可用时写入延迟，链路不可用时写入：

```text
down
```

示例文件结构：

```text
Time
Satellite_10102 Satellite_10201 Satellite_10199 Satellite_10103
------------------------------------------------------------
0 12.34567890 down 10.12345678 11.23456789
1 12.45678901 down 10.23456789 11.34567890
```

导出限制：

- 轨道面数量至少为 3。
- 每轨卫星数量至少为 3。
- 轨道面数量和每轨卫星数量最多为 99，用于生成两位编号格式。

## Redis 链路指标

菜单路径：

```text
Redis -> 启用 Redis 查询
Redis -> Redis 设置
```

Redis 查询默认关闭。可以在 GUI 中启用，也可以通过环境变量启用。

常用环境变量：

```bash
SATNET_REDIS_ENABLED=1
SATNET_REDIS_HOST=127.0.0.1
SATNET_REDIS_PORT=6379
SATNET_REDIS_DB=0
SATNET_REDIS_PASSWORD=
SATNET_REDIS_KEY_PREFIX=link
SATNET_REDIS_LOSS_ENABLED=1
SATNET_REDIS_LOSS_SCALE=1.0
SATNET_REDIS_SOCKET_TIMEOUT=0.05
SATNET_REDIS_QUERY_INTERVAL=2
```

SSH 隧道相关变量：

```bash
SATNET_REDIS_USE_SSH=1
SATNET_SSH_HOST=
SATNET_SSH_PORT=22
SATNET_SSH_USERNAME=
SATNET_SSH_PASSWORD=
SATNET_SSH_PRIVATE_KEY=
SATNET_SSH_PRIVATE_KEY_PASSPHRASE=
```

Redis key 默认格式：

```text
link:<src_id>:<tgt_id>:<metric>
link:<tgt_id>:<src_id>:<metric>
```

程序会同时尝试正向和反向 key，并读取列表中的最新值。

## 项目结构

```text
satellite-simulation/
  main.py                       # 程序入口
  environment.yml               # Conda 环境
  assets/                       # 贴图和图标资源
  core/
    calculator.py               # TLE 解析、Walker 生成和轨道推进
    strategies.py               # 链路拓扑策略
    link_dataset_exporter.py    # 链路状态数据集导出
    redis_latency.py            # Redis 链路指标读取
    models.py                   # 数据模型
  gui/
    main_window.py              # 主窗口和菜单逻辑
    dialogs.py                  # 参数对话框
    visualizer.py               # 三维可视化
    table_panel.py              # 链路表格
    topology_registry.py        # 链路状态注册表
    redis_worker.py             # Redis 后台查询线程
```

## 开发检查

可用以下命令做基础检查：

```bash
python3 -m pyflakes .
python3 -m compileall -q .
```
