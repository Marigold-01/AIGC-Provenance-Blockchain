# AIGC 新闻图片区块链可信溯源与内容演化治理原型系统

本项目是论文《面向 AIGC 动态传播的区块链可信溯源与内容演化治理机制研究》的配套代码原型。系统用于演示：AI 生成新闻图片在上传、转载、编辑、压缩、加水印等传播过程中，如何进行可信存证、同源识别、版本关系记录与治理标记。

## 1. 项目功能

系统包含以下模块：

1. 图片特征提取模块  
   提取 SHA256、pHash、dHash、RGB 颜色直方图等特征。

2. 多特征融合相似度计算模块  
   将文件哈希、感知哈希、差异哈希、颜色直方图进行加权融合，得到图片同源相似度。

3. 区块链可信存证模块  
   使用模拟区块链结构保存图片摘要、时间戳、父版本编号、治理标签等信息，并通过 previous_hash 和 block_hash 形成链式结构。

4. 版本关系识别模块  
   新图片与历史图片逐一比较，若融合相似度超过阈值，则将历史最高相似版本记录为 parent_id。

5. 内容演化治理模块  
   根据 SHA256 是否一致、融合相似度高低、父子版本关系，输出“原创存证”“重复传播”“轻度编辑传播”“疑似二次创作”“弱关联传播”等治理标签。

6. 传播链可视化模块  
   自动生成 version_graph.png，用于论文实验结果展示。

## 2. 环境安装

建议使用 Python 3.10 及以上版本。

```bash
pip install -r requirements.txt
```

如果你在 Windows 上运行，建议先进入项目目录：

```bash
cd aigc_news_trace_chain
```

## 3. 快速运行

### 第一步：生成演示新闻图片

```bash
python generate_demo_images.py
```

该命令会在 `data/news_images/` 下生成若干示例图片，包括原图、压缩图、加文字图、裁剪图、水印图、亮度调整图、模糊图和无关图片。

### 第二步：运行溯源系统

```bash
python main.py --input_dir data/news_images --output_dir results --threshold 0.70
```

运行完成后，终端会输出每张图片的父版本、相似度和治理标签。

## 4. 输出文件说明

运行后，`results/` 文件夹中会生成：

| 文件名 | 含义 | 论文用途 |
|---|---|---|
| trace_records.json | 图片溯源记录 | 第4章系统运行结果 |
| blockchain_records.json | 区块链存证记录 | 第4章区块链存证实验 |
| version_graph.json | 传播链节点和边数据 | 第3.4系统流程或第4章实验 |
| version_graph.png | 传播链可视化图片 | 可直接放入论文 |
| experiment_result.csv | 每张图片最终识别结果 | 可转成论文实验表 |
| similarity_matrix.csv | 图片两两相似度结果 | 可用于分析融合相似度 |
| summary.json | 系统运行摘要 | 辅助检查 |

## 5. 使用自己的新闻图片

把新闻图片放入：

```text
data/news_images/
```

然后运行：

```bash
python main.py --input_dir data/news_images --output_dir results --threshold 0.70
```

建议命名方式：

```text
01_original.png
02_compressed.jpg
03_add_caption.png
04_cropped.png
05_watermark.png
```

这样输出结果更容易阅读。

## 6. 论文对应关系

| 代码文件 | 论文对应部分 |
|---|---|
| feature_extractor.py | 图片特征提取模块 |
| similarity.py | 多特征融合相似度计算模块 |
| blockchain.py | 区块链可信存证模块 |
| version_tracker.py | 版本关系识别模块、系统工作流程 |
| governance.py | 内容演化治理模块 |
| visualization.py | 传播链可视化与实验结果展示 |
| main.py | 系统主流程 |

## 7. 核心流程

系统工作流程如下：

```text
图片输入
  ↓
提取 SHA256 / pHash / dHash / 颜色直方图
  ↓
与历史图片记录进行相似度计算
  ↓
判断是否超过同源阈值
  ↓
生成 parent_id 父版本关系
  ↓
生成治理标签
  ↓
写入模拟区块链
  ↓
导出传播链图和实验结果表
```

## 8. 说明

本项目为了便于课程论文展示，使用 Python 模拟区块链结构，而非部署真实以太坊智能合约。其重点是体现区块链的链式哈希、时间戳、不可篡改校验和内容传播演化记录逻辑。后续可以扩展为智能合约版本，将图片摘要、父版本编号和治理标签写入真实联盟链或以太坊测试链。
