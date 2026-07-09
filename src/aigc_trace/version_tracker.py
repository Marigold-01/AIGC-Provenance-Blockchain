from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .blockchain import SimpleBlockchain
from .feature_extractor import FeatureExtractor
from .governance import GovernanceEngine
from .models import ImageFeature, SimilarityResult, TraceRecord
from .similarity import SimilarityCalculator
from .storage import list_images


class VersionTracker:
    """版本关系识别与传播链构建。

    论文对应：版本关系识别模块、系统工作流程模块。
    核心逻辑：新图片与历史图片逐一比较，选择融合相似度最高的历史版本作为候选父版本。
    """

    def __init__(
        self,
        threshold: float = 0.72,
        weights: Dict[str, float] | None = None,
        uploader: str = "system_user",
    ) -> None:
        self.threshold = threshold
        self.uploader = uploader
        self.extractor = FeatureExtractor()
        self.similarity = SimilarityCalculator(weights=weights)
        self.governance = GovernanceEngine()
        self.blockchain = SimpleBlockchain()
        self.features: List[ImageFeature] = []
        self.records: List[TraceRecord] = []
        self.similarity_rows: List[dict] = []

    def process_directory(self, input_dir: str | Path, supported_ext: List[str]) -> Dict[str, object]:
        image_paths = list_images(input_dir, supported_ext)
        if not image_paths:
            raise ValueError(f"目录中没有可处理图片：{input_dir}")

        for index, image_path in enumerate(image_paths, start=1):
            image_id = f"IMG{index:03d}"
            version_id = f"V{index:03d}"
            feature = self.extractor.extract(image_path, image_id=image_id)
            parent_id, parent_file, best_result = self._find_parent(feature)
            best_similarity = best_result.fusion_score if best_result else 0.0
            label, reason = self.governance.label(parent_id, best_similarity, best_result, self.threshold)

            record = TraceRecord(
                version_id=version_id,
                file_name=feature.file_name,
                file_path=feature.file_path,
                parent_id=parent_id,
                parent_file=parent_file,
                uploader=self.uploader,
                timestamp=datetime.now().replace(microsecond=0).isoformat(),
                sha256=feature.sha256,
                phash=feature.phash,
                dhash=feature.dhash,
                width=feature.width,
                height=feature.height,
                best_similarity=round(best_similarity, 6),
                phash_similarity=best_result.phash_score if best_result else 0.0,
                dhash_similarity=best_result.dhash_score if best_result else 0.0,
                histogram_similarity=best_result.histogram_score if best_result else 0.0,
                governance_label=label,
                governance_reason=reason,
            )

            self.features.append(feature)
            self.records.append(record)
            self.blockchain.add_record(record)

        return {
            "records": [record.to_dict() for record in self.records],
            "similarity_matrix": self.similarity_rows,
            "blockchain": self.blockchain.to_list(),
            "chain_valid": self.blockchain.validate_chain(),
        }

    def _find_parent(self, new_feature: ImageFeature) -> Tuple[Optional[str], Optional[str], Optional[SimilarityResult]]:
        best_record: Optional[TraceRecord] = None
        best_result: Optional[SimilarityResult] = None

        for old_feature, old_record in zip(self.features, self.records):
            result = self.similarity.compare(old_feature, new_feature)
            self.similarity_rows.append({
                "source_version_id": old_record.version_id,
                "source_file": old_feature.file_name,
                "target_image_id": new_feature.image_id,
                "target_file": new_feature.file_name,
                **result.to_dict(),
            })
            if best_result is None or result.fusion_score > best_result.fusion_score:
                best_result = result
                best_record = old_record

        if best_result is None or best_record is None:
            return None, None, None

        if best_result.fusion_score >= self.threshold:
            return best_record.version_id, best_record.file_name, best_result

        return None, None, best_result

    def build_version_graph(self) -> Dict[str, object]:
        nodes = []
        edges = []
        for record in self.records:
            nodes.append({
                "id": record.version_id,
                "file_name": record.file_name,
                "label": record.governance_label,
                "similarity": record.best_similarity,
            })
            if record.parent_id:
                edges.append({
                    "source": record.parent_id,
                    "target": record.version_id,
                    "similarity": record.best_similarity,
                    "relation": record.governance_label,
                })
        return {"nodes": nodes, "edges": edges}
