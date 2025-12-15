"""
JSON 处理工具

处理 LLM 输出的 JSON 解析、标注文件读写等。
"""

import json
import re
from pathlib import Path
from typing import Optional, Union, List, Dict, Any


def parse_llm_json(text: str) -> Optional[List[Dict]]:
    """
    解析 LLM 输出的 JSON
    
    处理各种格式问题：
    - Markdown 代码块包裹
    - 截断的 JSON
    - 空响应
    
    Args:
        text: LLM 原始输出文本
        
    Returns:
        解析后的列表，失败返回 None
    """
    if not text or not text.strip():
        return None
    
    text = text.strip()
    
    # 提取 JSON 部分
    json_str = _extract_json_string(text)
    
    if not json_str or json_str == "[]":
        return []
    
    # 尝试修复截断的 JSON
    json_str = _fix_truncated_json(json_str)
    
    try:
        result = json.loads(json_str)
        if isinstance(result, list):
            return result
        return [result]
    except json.JSONDecodeError:
        return None


def _extract_json_string(text: str) -> str:
    """从文本中提取 JSON 字符串"""
    # 尝试提取 ```json ... ``` 代码块
    if "```json" in text:
        match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if match:
            return match.group(1).strip()
    
    # 尝试提取 ``` ... ``` 代码块
    if "```" in text:
        match = re.search(r'```\s*([\s\S]*?)\s*```', text)
        if match:
            return match.group(1).strip()
    
    # 尝试直接提取 JSON 数组
    if "[" in text:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            return text[start:end+1]
    
    return text.strip()


def _fix_truncated_json(json_str: str) -> str:
    """修复被截断的 JSON 数组"""
    if not json_str:
        return json_str
    
    # 如果不以 ] 结尾，尝试修复
    if not json_str.rstrip().endswith("]"):
        # 找到最后一个完整的对象
        last_complete = json_str.rfind("},")
        if last_complete > 0:
            json_str = json_str[:last_complete+1] + "]"
        else:
            # 尝试找最后一个 }
            last_brace = json_str.rfind("}")
            if last_brace > 0:
                json_str = json_str[:last_brace+1] + "]"
    
    return json_str


def save_annotation(
    annotation: Dict[str, Any],
    output_path: Union[str, Path],
    ensure_ascii: bool = False,
    indent: int = 2
) -> Path:
    """
    保存标注文件
    
    Args:
        annotation: 标注数据字典
        output_path: 输出路径
        ensure_ascii: 是否转义非 ASCII 字符
        indent: 缩进空格数
        
    Returns:
        保存的文件路径
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(annotation, f, ensure_ascii=ensure_ascii, indent=indent)
    
    return output_path


def load_annotation(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """
    加载标注文件
    
    Args:
        file_path: 标注文件路径
        
    Returns:
        标注数据字典，失败返回 None
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def to_xanylabeling_format(
    detections: List[Dict],
    image_path: str,
    image_width: int,
    image_height: int
) -> Dict[str, Any]:
    """
    转换为 X-AnyLabeling 兼容格式
    
    Args:
        detections: 检测结果列表，每个元素需包含 label, category, bbox
        image_path: 图片路径（用于提取文件名）
        image_width: 图片宽度
        image_height: 图片高度
        
    Returns:
        X-AnyLabeling 格式的标注字典
    """
    shapes = []
    for det in detections:
        shapes.append({
            "label": det["label"],
            "text": det["label"],
            "points": [
                [det["bbox"][0], det["bbox"][1]],
                [det["bbox"][2], det["bbox"][3]]
            ],
            "group_id": None,
            "shape_type": "rectangle",
            "flags": {"category": det.get("category", "unknown")}
        })
    
    return {
        "version": "0.4.1",
        "flags": {},
        "shapes": shapes,
        "imagePath": Path(image_path).name,
        "imageData": None,
        "imageHeight": image_height,
        "imageWidth": image_width
    }
