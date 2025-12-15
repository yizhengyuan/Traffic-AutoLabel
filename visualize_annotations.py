#!/usr/bin/env python3
"""
可视化标注结果 - 在图片上绘制矩形框
"""

import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# 类别颜色定义 (RGB)
CATEGORY_COLORS = {
    "pedestrian": (255, 0, 0),      # 红色 - 行人
    "vehicle": (0, 255, 0),         # 绿色 - 车辆
    "traffic_sign": (0, 0, 255),    # 蓝色 - 交通标志
    "construction": (255, 165, 0),  # 橙色 - 施工标志
}

CATEGORY_NAMES = {
    "pedestrian": "行人",
    "vehicle": "车辆",
    "traffic_sign": "交通标志",
    "construction": "施工标志",
}


def visualize_annotations(image_path: str, json_path: str, output_path: str):
    """在图片上绘制标注框"""
    
    # 读取图片
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    # 读取标注
    with open(json_path, "r", encoding="utf-8") as f:
        annotation = json.load(f)
    
    # 绘制每个目标
    for shape in annotation.get("shapes", []):
        label = shape["label"]
        points = shape["points"]
        
        x1, y1 = points[0]
        x2, y2 = points[1]
        
        # 获取颜色
        color = CATEGORY_COLORS.get(label, (128, 128, 128))
        
        # 绘制矩形框
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        
        # 绘制标签背景
        label_text = CATEGORY_NAMES.get(label, label)
        text_bbox = draw.textbbox((x1, y1 - 20), label_text)
        draw.rectangle([text_bbox[0] - 2, text_bbox[1] - 2, text_bbox[2] + 2, text_bbox[3] + 2], fill=color)
        draw.text((x1, y1 - 20), label_text, fill=(255, 255, 255))
    
    # 保存
    img.save(output_path)
    print(f"  💾 保存: {output_path}")


def main():
    images_dir = Path("test_images/extracted_frames")
    annotations_dir = Path("output/d1_annotations")
    output_dir = Path("output/d1_visualized")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("🎨 可视化标注结果")
    print("=" * 70)
    
    # 处理所有已标注的图片
    json_files = list(annotations_dir.glob("*.json"))
    
    for json_path in json_files:
        image_name = json_path.stem + ".jpg"
        image_path = images_dir / image_name
        
        if image_path.exists():
            output_path = output_dir / f"{json_path.stem}_annotated.jpg"
            print(f"\n📷 {image_name}")
            visualize_annotations(str(image_path), str(json_path), str(output_path))
    
    print("\n" + "=" * 70)
    print(f"✅ 可视化完成! 结果保存在: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
