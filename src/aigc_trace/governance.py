from __future__ import annotations

from typing import Optional, Tuple

from .models import SimilarityResult


class GovernanceEngine:
    """内容演化治理规则引擎。

    论文对应：内容演化治理模块。
    本原型使用可解释规则，不追求复杂机器学习模型，便于论文展示和老师查看。
    """

    def label(
        self,
        parent_id: Optional[str],
        best_similarity: float,
        best_result: Optional[SimilarityResult],
        threshold: float,
    ) -> Tuple[str, str]:
        if parent_id is None or best_result is None:
            return "原创存证", "未发现高相似历史版本，作为新的原始图片写入链上。"

        if best_result.sha256_equal:
            return "重复传播", "SHA256 完全一致，说明图片文件未发生变化，属于重复上传或重复传播。"

        if best_similarity >= 0.78:
            return "轻度编辑传播", "融合相似度很高但 SHA256 不同，说明图片可能经过压缩、格式转换或轻微编辑。"

        if best_similarity >= 0.74:
            return "疑似二次创作", "图片与历史版本高度相似，但存在明显编辑差异，可能加入文字、水印或局部修改。"

        if best_similarity >= threshold:
            return "弱关联传播", "图片达到同源阈值，但相似度不高，建议人工复核其来源关系。"

        return "异常传播", "未达到同源阈值却声称存在关联，可能存在伪造来源或错误关联。"
