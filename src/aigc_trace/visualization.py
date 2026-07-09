from __future__ import annotations

from pathlib import Path
from typing import Dict

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import networkx as nx

from .storage import ensure_dir


def _set_chinese_font() -> None:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    for font_path in candidates:
        if Path(font_path).exists():
            try:
                fm.fontManager.addfont(font_path)
                prop = fm.FontProperties(fname=font_path)
                plt.rcParams["font.family"] = prop.get_name()
                plt.rcParams["axes.unicode_minus"] = False
                return
            except Exception:
                continue


def draw_version_graph(version_graph: Dict[str, object], output_path: str | Path) -> None:
    """绘制内容传播演化链图。"""
    _set_chinese_font()
    output = Path(output_path)
    ensure_dir(output.parent)

    graph = nx.DiGraph()
    nodes = version_graph.get("nodes", [])
    edges = version_graph.get("edges", [])

    for node in nodes:
        graph.add_node(node["id"], file_name=node["file_name"], label=node["label"])

    for edge in edges:
        graph.add_edge(edge["source"], edge["target"], similarity=edge["similarity"], relation=edge["relation"])

    plt.figure(figsize=(11, 7))
    if len(graph.nodes) == 0:
        plt.text(0.5, 0.5, "No graph data", ha="center", va="center")
        plt.savefig(output, dpi=180, bbox_inches="tight")
        plt.close()
        return

    try:
        pos = nx.nx_agraph.graphviz_layout(graph, prog="dot")
    except Exception:
        pos = nx.spring_layout(graph, seed=42)

    nx.draw_networkx_nodes(graph, pos, node_size=2600, alpha=0.9)
    nx.draw_networkx_edges(graph, pos, arrows=True, arrowstyle="->", arrowsize=18, width=1.6)

    label_map = {
        "原创存证": "Original",
        "重复传播": "Duplicate",
        "轻度编辑传播": "Light Edit",
        "疑似二次创作": "Derivative",
        "弱关联传播": "Weak Link",
        "异常传播": "Abnormal",
    }
    node_labels = {
        node_id: f"{node_id}\n{data.get('file_name', '')}\n{label_map.get(data.get('label', ''), data.get('label', ''))}"
        for node_id, data in graph.nodes(data=True)
    }
    nx.draw_networkx_labels(graph, pos, labels=node_labels, font_size=8)

    edge_labels = {
        (u, v): f"{data.get('similarity', 0):.2f}"
        for u, v, data in graph.edges(data=True)
    }
    nx.draw_networkx_edge_labels(graph, pos, edge_labels=edge_labels, font_size=8)

    plt.title("AIGC News Image Version Evolution Graph")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output, dpi=180, bbox_inches="tight")
    plt.close()
