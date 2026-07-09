# AIGC 新闻图片区块链可信溯源与内容演化治理原型系统

本项目是论文《面向 AIGC 动态传播的区块链可信溯源与内容演化治理机制研究》的配套代码原型。

系统**不会自动生成或修改图片**。研究者将原始新闻图片及其压缩、加标题、裁剪、AIGC 二次编辑、亮度调整、模糊和非同源对照版本放入 `data/news_images/`，系统负责完成：

- SHA256、pHash、dHash、RGB 颜色直方图和 ORB 局部特征提取；
- 多特征融合相似度计算；
- 同源阈值自动寻优；
- 父子版本识别与传播链构建；
- AIGC 来源和编辑元数据记录；
- 轻量级区块链存证与篡改校验；
- 内容演化治理标记；
- Accuracy、Precision、Recall、F1 和方法对比。

## 1. 项目结构

```text
aigc_news_trace_chain_final/
├── main.py                         # 主程序；默认执行阈值自动寻优
├── optimize_thresholds.py          # 独立阈值寻优，可选写回 config.json
├── evaluate_results.py             # 实验评价和单特征/融合方法对比
├── verify_blockchain.py            # 独立区块链完整性校验
├── config.json                     # 融合权重、阈值搜索范围等配置
├── requirements.txt                # Python 依赖
├── PAPER_CODE_MAPPING.md           # 论文与代码对应关系
├── data/
│   ├── news_images/                # 放入 8 张实验图片
│   ├── image_metadata.json         # 8 张图片的 AIGC 来源与编辑元数据
│   └── ground_truth.json           # 8 张图片的真实同源标签
├── results/                        # 运行结果
├── src/aigc_trace/
│   ├── feature_extractor.py        # SHA256 / pHash / dHash / 直方图 / ORB
│   ├── similarity.py               # ORB 几何校验与多特征融合
│   ├── version_tracker.py          # 父版本识别和传播链构建
│   ├── metadata.py                 # 元数据读取与提示词哈希
│   ├── governance.py               # 治理标签规则
│   ├── blockchain.py               # 链式存证和篡改校验
│   ├── evaluation.py               # 指标与阈值寻优算法
│   ├── visualization.py            # 传播链可视化
│   ├── models.py                   # 数据结构
│   └── storage.py                  # JSON / CSV 读写
└── tests/                           # 基础测试
```

## 2. 安装环境

建议使用 Python 3.10 及以上版本。

```bash
pip install -r requirements.txt
```

Windows 进入项目目录示例：

```bash
cd /d D:\区块链基础期末大作业\aigc_news_trace_chain_final
```

## 3. 放入 8 张实验图片

将以下图片放入：

```text
data/news_images/
```

文件名必须保持一致：

```text
01_original.jpg       原始新闻图片
02_compressed.jpg     JPEG 压缩版本
03_add_caption.jpg    添加新闻标题或说明文字版本
04_cropped.jpg        裁剪版本
05_aigc_edited.jpg    AIGC 二次编辑版本
06_brightness.jpg     亮度调整版本
07_blur.jpg           模糊版本
08_different.jpg      完全不同的非同源新闻图片
```

当前 `data/image_metadata.json` 和 `data/ground_truth.json` 已与这 8 个文件名对齐。

若实际图片扩展名为 `.png`，必须同步修改两个 JSON 文件中的对应文件名，否则会出现“元数据匹配不足”或“未找到标注图片”。

## 4. 8 张图片的元数据说明

`data/image_metadata.json` 已包含：

- 原始图来源；
- 压缩、加标题、裁剪、亮度调整和模糊等编辑类型；
- `05_aigc_edited.jpg` 的 AIGC 编辑声明、模型、平台、提示词摘要和父版本；
- `08_different.jpg` 的非同源负样本标记。

其中 AIGC 字段属于实验声明或上传方元数据，不等同于系统自动证明图片一定由某个模型生成。

## 5. 运行主程序

```bash
python main.py
```

`config.json` 默认开启自动寻优。程序会先根据 `data/ground_truth.json` 扫描阈值，再使用选出的阈值重新完成父版本识别、区块链存证和传播链输出。

运行时会显示：

```text
同源阈值：0.xxx（ground_truth 自动寻优）
自动寻优：F1=...，Accuracy=...，最佳区间=[..., ...]
```

手动指定阈值会覆盖自动寻优：

```bash
python main.py --threshold 0.60
```

关闭自动寻优，直接使用 `config.json` 中的 `similarity_threshold`：

```bash
python main.py --no-auto-threshold
```

运行后主要生成：

| 文件 | 内容 |
|---|---|
| `trace_records.json` | 完整溯源记录、AIGC 元数据、ORB 分数和治理标签 |
| `blockchain_records.json` | 创世区块与图片存证区块 |
| `version_graph.json` | 传播链节点和边 |
| `version_graph.png` | 传播演化关系图 |
| `experiment_result.csv` | 每张图片的识别结果 |
| `similarity_matrix.csv` | 图片两两的各特征相似度 |
| `threshold_optimization.json` | 自动选出的阈值、最佳区间和正负样本边界 |
| `threshold_optimization_curve.csv` | 不同阈值对应的 Accuracy、F1 等指标 |
| `summary.json` | 本次运行摘要 |

## 6. ORB 局部特征说明

ORB 用于增强以下场景的识别：

- 图片被裁剪，但主要主体仍保留；
- 图片局部增加、删除或替换内容；
- AIGC 对背景进行编辑，但主要对象和局部结构未完全改变。

代码先使用 KNN 匹配和 Lowe 比率检验筛选可靠特征点，再使用 RANSAC 单应性估计检查几何一致性。ORB 分数由匹配覆盖率、几何内点比例和描述子质量共同计算。

默认融合权重为：

```text
fusion_score
= 0.05 × SHA256
+ 0.22 × pHash
+ 0.18 × dHash
+ 0.15 × 颜色直方图
+ 0.40 × ORB
```

权重可在 `config.json` 中修改。

## 7. 独立阈值寻优

主程序已经会自动寻优。也可以在已有运行结果上单独执行：

```bash
python optimize_thresholds.py
```

把推荐阈值写回 `config.json`：

```bash
python optimize_thresholds.py --apply
```

阈值选择规则为：

```text
最大 F1 → 最大平衡准确率 → 最大 Accuracy
```

若多个阈值并列最佳，程序选择最佳阈值区间的中点，避免使用过于贴近样本边界的极端阈值。

注意：当前课程实验使用同一标注集寻优和评价。正式研究应划分独立验证集和测试集，避免指标偏乐观。

## 8. 实验评价

主程序运行后执行：

```bash
python evaluate_results.py
```

输出包括：

- Accuracy；
- Precision；
- Recall；
- Specificity；
- Balanced Accuracy；
- F1；
- 父版本准确率；
- SHA256、pHash、dHash、颜色直方图、ORB 和多特征融合方法对比；
- 每种方法的自动最优阈值。

## 9. 区块链独立校验

```bash
python verify_blockchain.py
```

正常输出：

```text
校验结果：通过，未发现链上记录被修改。
```

可复制 `results/blockchain_records.json`，手动修改其中某个区块，再指定修改后的文件进行校验：

```bash
python verify_blockchain.py --file results/blockchain_records_tampered.json
```

## 10. 论文表述边界

本项目使用 Python 实现轻量级链式存证原型，体现区块哈希、前序哈希、时间戳和篡改校验机制，未部署以太坊、FISCO BCOS 或 Hyperledger 等真实区块链网络。

论文建议表述：

> 本文构建了面向 AIGC 新闻图片动态传播的区块链可信溯源原型系统，并采用轻量级链式存证结构验证内容摘要、版本关系和治理信息的不可篡改校验逻辑。
