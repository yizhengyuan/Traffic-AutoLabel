#!/usr/bin/env python3
"""
使用重构后模块的示例脚本

展示如何使用 glm_labeling 包进行标注。
"""

import argparse
from pathlib import Path

# 使用新的模块化导入
from glm_labeling.config import get_config, init_config
from glm_labeling.utils import (
    image_to_base64_url,
    get_image_size,
    convert_normalized_coords,
    parse_llm_json,
    save_annotation,
    to_xanylabeling_format,
    get_category,
    normalize_vehicle_label,
    get_category_emoji,
    get_logger,
    TaskProgress,
    retry_api_call
)

from zai import ZaiClient


def detect_objects(client: ZaiClient, image_path: str, config) -> list:
    """使用新模块的检测函数"""
    logger = get_logger()
    
    base64_url = image_to_base64_url(image_path)
    width, height = get_image_size(image_path)
    
    prompt = """请检测图片中的目标，返回JSON格式。
类别：pedestrian, vehicle, traffic_sign, construction
格式：[{"label": "car", "bbox_2d": [x1, y1, x2, y2]}]"""

    def call_api():
        return client.chat.completions.create(
            model=config.model_name,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": base64_url}},
                    {"type": "text", "text": prompt}
                ]
            }]
        )
    
    try:
        response = retry_api_call(
            call_api,
            max_retries=config.max_retries,
            delay=config.retry_delay,
            on_retry=lambda a, e: logger.warning(f"Retry {a}: {e}")
        )
        
        result_text = response.choices[0].message.content.strip()
        detections = parse_llm_json(result_text)
        
        if not detections:
            return []
        
        processed = []
        for det in detections:
            if "label" not in det or "bbox_2d" not in det:
                continue
            
            bbox = convert_normalized_coords(
                det["bbox_2d"], width, height, 
                base=config.coord_normalize_base
            )
            
            label = det["label"].lower().replace(" ", "_")
            category = get_category(label)
            
            if category == "vehicle":
                label = normalize_vehicle_label(label)
            
            processed.append({
                "label": label,
                "category": category,
                "bbox": bbox
            })
        
        return processed
        
    except Exception as e:
        logger.error(f"Detection failed: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description="示例：使用重构后的模块")
    parser.add_argument("--image", type=str, required=True, help="图片路径")
    parser.add_argument("--output", type=str, default=None, help="输出路径")
    args = parser.parse_args()
    
    # 初始化配置
    config = get_config()
    logger = get_logger()
    
    if not config.api_key:
        logger.error("请设置 ZAI_API_KEY 环境变量")
        return
    
    client = ZaiClient(api_key=config.api_key)
    image_path = args.image
    
    logger.info(f"Processing: {image_path}")
    
    # 检测
    detections = detect_objects(client, image_path, config)
    
    # 输出结果
    for det in detections:
        emoji = get_category_emoji(det["category"])
        logger.info(f"  {emoji} {det['label']} [{det['category']}] {det['bbox']}")
    
    # 保存
    if args.output or detections:
        width, height = get_image_size(image_path)
        annotation = to_xanylabeling_format(detections, image_path, width, height)
        
        output_path = args.output or f"{Path(image_path).stem}.json"
        save_annotation(annotation, output_path)
        logger.info(f"Saved to: {output_path}")


if __name__ == "__main__":
    main()
