# 论文与代码对应说明

## 第3.3 系统功能模块设计

### 3.3.1 新闻图片输入与 AIGC 元数据模块

对应：`src/aigc_trace/metadata.py`、`data/image_metadata.json`

系统接收研究者准备的 8 张新闻图片，不在系统内部自动生成或修改图片。元数据记录图片来源、编辑类型、AIGC 编辑模型、来源平台、声明父版本和生成提示词摘要。

### 3.3.2 多维图片特征提取模块

对应：`src/aigc_trace/feature_extractor.py`

系统提取 SHA256、pHash、dHash、RGB 颜色直方图和 ORB 局部特征。ORB 保留关键点坐标与二进制描述子，用于处理裁剪、局部变化和 AIGC 背景编辑。

### 3.3.3 多特征融合相似度模块

对应：`src/aigc_trace/similarity.py`、`config.json`

默认融合公式：

```text
S_fusion
= 0.05S_sha256
+ 0.22S_pHash
+ 0.18S_dHash
+ 0.15S_histogram
+ 0.40S_ORB
```

ORB 先进行 KNN 匹配和 Lowe 比率检验，再使用 RANSAC 检查几何一致性，最终综合匹配覆盖率、几何内点比例和描述子质量得到 ORB 相似度。

### 3.3.4 同源阈值自动寻优模块

对应：`src/aigc_trace/evaluation.py`、`main.py`、`optimize_thresholds.py`

系统在设定搜索区间内逐步扫描阈值，以 F1 为首要指标，并依次参考平衡准确率和 Accuracy。若多个阈值并列最佳，则选择最佳区间的中点。课程实验直接使用当前标注集演示；正式研究应使用独立验证集选阈值。

### 3.3.5 区块链可信存证模块

对应：`src/aigc_trace/blockchain.py`

系统将图片摘要、AIGC 来源元数据、父版本、融合相似度、ORB 相似度、治理标签和时间戳写入区块，并通过 `previous_hash` 和 `block_hash` 支持完整性验证。

### 3.3.6 版本关系识别模块

对应：`src/aigc_trace/version_tracker.py`

新图片与历史图片逐一比较，选择融合相似度最高的历史图片作为候选父版本；若相似度达到自动选出的阈值，则建立父子版本关系，否则作为独立源内容存证。

### 3.3.7 内容演化治理模块

对应：`src/aigc_trace/governance.py`

根据文件摘要、融合相似度和父子关系输出“原创存证”“重复传播”“轻度编辑传播”“疑似二次创作”和“弱关联传播”等标签。

### 3.3.8 传播链可视化模块

对应：`src/aigc_trace/visualization.py`

将版本节点、父子边、融合相似度和治理关系绘制为有向传播演化图。

## 第3.4 系统工作流程设计

对应：`main.py`、`src/aigc_trace/version_tracker.py`

```text
8张实验图片输入
→ 读取 AIGC 来源与编辑元数据
→ 提取 SHA256 / pHash / dHash / 颜色直方图 / ORB
→ 计算历史版本多特征融合相似度
→ 根据真实标签自动搜索同源阈值
→ 使用最佳阈值重新识别父版本
→ 生成治理标签
→ 写入链式存证结构
→ 导出传播链、相似度矩阵和实验结果
→ 完整性校验与评价指标计算
```

## 第4章 系统实现与实验分析

### 4.1 实验数据

对应：`data/news_images/`、`data/image_metadata.json`、`data/ground_truth.json`

实验共 8 张：原图、压缩、加标题、裁剪、AIGC 二次编辑、亮度调整、模糊和非同源对照图。

### 4.2 评价指标

对应：`src/aigc_trace/evaluation.py`、`evaluate_results.py`

计算 Accuracy、Precision、Recall、Specificity、Balanced Accuracy、F1 和父版本准确率。

### 4.3 对比方案

对应输出：`results/method_comparison.csv`、`results/optimized_method_thresholds.csv`

对比 SHA256、pHash、dHash、颜色直方图、ORB 局部特征和多特征融合方法。

### 4.4 阈值实验

对应输出：`results/threshold_optimization.json`、`results/threshold_optimization_curve.csv`

展示阈值搜索范围、最佳阈值区间、推荐阈值，以及不同阈值下的 Accuracy、F1 等指标。

### 4.5 区块链完整性验证

对应：`verify_blockchain.py`

独立读取 `blockchain_records.json`，重新计算每个区块哈希，并检查前序哈希链接是否一致。

### 4.6 主要实验输出

| 文件 | 用途 |
|---|---|
| `experiment_result.csv` | 8 张图片的父版本识别、各特征分数和治理结果 |
| `similarity_matrix.csv` | 图片两两 SHA256、pHash、dHash、直方图、ORB 和融合相似度 |
| `threshold_optimization_curve.csv` | 阈值扫描曲线数据 |
| `version_graph.png` | 内容传播演化图 |
| `blockchain_records.json` | 链式存证结构 |
| `evaluation_report.json` | 总体评价指标和自动寻优结果 |
| `optimized_method_thresholds.csv` | 各单一特征和融合方法的最优阈值 |
