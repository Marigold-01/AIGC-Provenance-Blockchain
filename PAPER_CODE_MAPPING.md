# 论文与代码对应说明

## 第3.3 系统功能模块设计

### 3.3.1 图片特征提取模块
对应代码：`src/aigc_trace/feature_extractor.py`

系统对输入图片提取 SHA256、pHash、dHash 和颜色直方图。SHA256 用于判断文件是否完全一致，pHash 和 dHash 用于识别压缩、裁剪、加文字、水印等操作后的视觉相似性，颜色直方图作为辅助视觉特征。

### 3.3.2 多特征融合相似度计算模块
对应代码：`src/aigc_trace/similarity.py`

系统使用加权融合方式计算图片同源相似度：

```text
fusion_score = 0.20 * sha256_score + 0.35 * phash_score + 0.35 * dhash_score + 0.10 * histogram_score
```

该公式可以在 `config.json` 中调整权重。

### 3.3.3 区块链可信存证模块
对应代码：`src/aigc_trace/blockchain.py`

系统将图片版本编号、图片摘要、父版本编号、时间戳、治理标签等信息写入区块。每个区块包含 `previous_hash` 和 `block_hash`，用于保证链式关联与篡改检测。

### 3.3.4 版本关系识别模块
对应代码：`src/aigc_trace/version_tracker.py`

新图片上传后，系统会与历史图片逐一比较，选择融合相似度最高的历史图片作为候选父版本。若最高相似度超过阈值，则记录为当前图片的 `parent_id`。

### 3.3.5 内容演化治理模块
对应代码：`src/aigc_trace/governance.py`

系统根据相似度与 SHA256 是否一致生成治理标签，包括原创存证、重复传播、轻度编辑传播、疑似二次创作和弱关联传播。

## 第3.4 系统工作流程设计

对应代码：`main.py` 与 `src/aigc_trace/version_tracker.py`

系统流程为：

```text
图片输入 → 特征提取 → 相似度计算 → 父版本判断 → 治理标签生成 → 区块链存证 → 传播链输出
```

## 第4章 实验分析

对应输出：`results/`

可放入论文的结果包括：

1. `experiment_result.csv`：实验结果表。
2. `similarity_matrix.csv`：图片两两相似度表。
3. `blockchain_records.json`：区块链存证记录。
4. `version_graph.png`：传播链可视化图。
