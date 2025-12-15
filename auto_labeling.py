#!/usr/bin/env python3
"""
GLM-4.6V 数据标注脚本
检测四类物体：行人、车辆、交通标志、施工标志
输出 X-AnyLabeling 兼容的 JSON 格式
"""

import os
import json
import base64
from pathlib import Path
from PIL import Image
from zai import ZaiClient

# API Key
API_KEY = os.getenv("ZAI_API_KEY", "")

# 类别定义和颜色
CATEGORIES = {
    "pedestrian": {"color": "#FF0000", "display": "行人"},      # 红色
    "vehicle": {"color": "#00FF00", "display": "车辆"},         # 绿色
    "traffic_sign": {"color": "#0000FF", "display": "交通标志"}, # 蓝色
    "construction": {"color": "#FFA500", "display": "施工标志"}  # 橙色
}

# 类别映射（中文 -> 英文）
LABEL_MAPPING = {
    # 行人
    "行人": "pedestrian",
    "人": "pedestrian", 
    "路人": "pedestrian",
    "骑车人": "pedestrian",
    "骑自行车的人": "pedestrian",
    "骑手": "pedestrian",
    
    # 车辆
    "车": "vehicle",
    "车辆": "vehicle",
    "汽车": "vehicle",
    "轿车": "vehicle",
    "小汽车": "vehicle",
    "货车": "vehicle",
    "卡车": "vehicle",
    "公交车": "vehicle",
    "巴士": "vehicle",
    "摩托车": "vehicle",
    "电动车": "vehicle",
    "自行车": "vehicle",
    "三轮车": "vehicle",
    "面包车": "vehicle",
    "SUV": "vehicle",
    "越野车": "vehicle",
    "出租车": "vehicle",
    "白色车辆": "vehicle",
    "黑色车辆": "vehicle",
    "前方车辆": "vehicle",
    
    # 交通标志
    "交通标志": "traffic_sign",
    "交通标识": "traffic_sign",
    "标志": "traffic_sign",
    "标识": "traffic_sign",
    "限速牌": "traffic_sign",
    "限速标志": "traffic_sign",
    "指示牌": "traffic_sign",
    "路牌": "traffic_sign",
    "红绿灯": "traffic_sign",
    "交通灯": "traffic_sign",
    "信号灯": "traffic_sign",
    "警示牌": "traffic_sign",
    "指示标志": "traffic_sign",
    "道路标志": "traffic_sign",
    
    # 施工标志
    "施工标志": "construction",
    "施工牌": "construction",
    "锥桶": "construction",
    "路锥": "construction",
    "交通锥": "construction",
    "施工围挡": "construction",
    "围挡": "construction",
    "施工警示": "construction",
    "施工区域": "construction",
}


def image_to_base64_url(image_path: str) -> str:
    """将本地图片转换为 base64 data URL"""
    path = Path(image_path)
    ext = path.suffix.lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
    }
    mime_type = mime_types.get(ext, 'image/jpeg')
    
    with open(path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    return f"data:{mime_type};base64,{image_data}"


def get_image_size(image_path: str) -> tuple:
    """获取图片尺寸"""
    with Image.open(image_path) as img:
        return img.width, img.height


def normalize_label(label: str) -> str:
    """将中文标签标准化为英文类别"""
    label = label.strip()
    
    # 直接匹配
    if label in LABEL_MAPPING:
        return LABEL_MAPPING[label]
    
    # 模糊匹配
    for chinese, english in LABEL_MAPPING.items():
        if chinese in label or label in chinese:
            return english
    
    # 默认返回原标签（小写）
    return label.lower().replace(" ", "_")


def detect_objects(client: ZaiClient, image_path: str) -> list:
    """使用 GLM-4.6V 检测图片中的目标物体"""
    base64_url = image_to_base64_url(image_path)
    width, height = get_image_size(image_path)
    
    prompt = """请仔细分析这张图片，检测以下四类物体并返回它们的边界框坐标：

1. 行人（包括骑自行车的人、路人、行人等）
2. 车辆（包括汽车、货车、摩托车、公交车、自行车等）
3. 交通标志（⚠️ 请仔细检测！包括：限速牌、指示牌、红绿灯、路牌、方向指示牌、警告牌、禁止标志、车道指示等）
4. 施工标志（包括锥桶、施工围挡、施工警示牌等）

⚠️ 重要提示：
- 这是第一人称骑行视角的画面
- 请**不要标注**画面底部的第一人称载具（自车/摩托车的车把、仪表盘、骑手的手等）
- 只标注道路上的**其他**车辆、行人和各种标志
- 请**特别注意**检测道路两侧和上方的交通标志牌

请以 JSON 数组格式返回结果，每个检测到的物体包含：
- label: 物体类别名称（中文），交通标志请具体说明类型如"限速牌"、"路牌"、"红绿灯"等
- bbox_2d: 边界框坐标 [xmin, ymin, xmax, ymax]

示例格式：
[
  {"label": "汽车", "bbox_2d": [100, 200, 300, 400]},
  {"label": "限速牌", "bbox_2d": [800, 50, 900, 150]},
  {"label": "红绿灯", "bbox_2d": [600, 100, 650, 200]}
]

如果图片中没有这四类物体（或只有第一人称自车），请返回空数组 []

只返回 JSON 数组，不要其他解释文字。"""

    response = client.chat.completions.create(
        model="glm-4.6v",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": base64_url
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    )
    
    result_text = response.choices[0].message.content
    
    # 解析 JSON
    try:
        # 尝试提取 JSON 部分
        if "```json" in result_text:
            json_str = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            json_str = result_text.split("```")[1].split("```")[0].strip()
        elif "[" in result_text:
            start = result_text.find("[")
            end = result_text.rfind("]") + 1
            json_str = result_text[start:end]
        else:
            json_str = result_text
        
        detections = json.loads(json_str)
        
        # 处理检测结果
        processed = []
        for det in detections:
            if "label" in det and "bbox_2d" in det:
                raw_bbox = det["bbox_2d"]
                
                # GLM-4.6V 返回的是 0-1000 归一化坐标，转换为像素坐标
                bbox = [
                    int(round(raw_bbox[0] / 1000 * width)),
                    int(round(raw_bbox[1] / 1000 * height)),
                    int(round(raw_bbox[2] / 1000 * width)),
                    int(round(raw_bbox[3] / 1000 * height))
                ]
                
                # 确保坐标在图片范围内
                bbox[0] = max(0, min(bbox[0], width))
                bbox[1] = max(0, min(bbox[1], height))
                bbox[2] = max(0, min(bbox[2], width))
                bbox[3] = max(0, min(bbox[3], height))
                
                processed.append({
                    "label": normalize_label(det["label"]),
                    "original_label": det["label"],
                    "bbox": bbox
                })
        
        return processed
        
    except Exception as e:
        print(f"  ⚠️ JSON 解析失败: {e}")
        print(f"  原始响应: {result_text[:500]}")
        return []


def to_xanylabeling_format(detections: list, image_path: str) -> dict:
    """转换为 X-AnyLabeling 格式"""
    width, height = get_image_size(image_path)
    
    shapes = []
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        shapes.append({
            "label": det["label"],
            "text": det.get("original_label", ""),
            "points": [[x1, y1], [x2, y2]],
            "group_id": None,
            "shape_type": "rectangle",
            "flags": {}
        })
    
    return {
        "version": "0.4.1",
        "flags": {},
        "shapes": shapes,
        "imagePath": Path(image_path).name,
        "imageData": None,
        "imageHeight": height,
        "imageWidth": width
    }


def main():
    if not API_KEY:
        print("❌ 请设置 ZAI_API_KEY 环境变量")
        return
    
    # 获取 D1 图片
    images_dir = Path("test_images/extracted_frames")
    images = sorted([f for f in images_dir.glob("D1_*.jpg")])
    
    # 测试前 15 张（包含有交通标志的帧）
    test_images = images[:15]
    
    print("=" * 70)
    print(f"🏷️  GLM-4.6V 数据标注测试 - D1 系列前 {len(test_images)} 张")
    print("=" * 70)
    
    client = ZaiClient(api_key=API_KEY)
    
    # 创建输出目录
    output_dir = Path("output/d1_annotations")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_results = []
    
    for i, img_path in enumerate(test_images, 1):
        print(f"\n📷 [{i}/{len(test_images)}] {img_path.name}")
        print("-" * 50)
        
        try:
            # 检测物体
            detections = detect_objects(client, str(img_path))
            
            print(f"  ✅ 检测到 {len(detections)} 个目标:")
            for det in detections:
                cat = det["label"]
                color = CATEGORIES.get(cat, {}).get("display", cat)
                print(f"     - {det['original_label']} -> {cat} {det['bbox']}")
            
            # 转换为 X-AnyLabeling 格式
            annotation = to_xanylabeling_format(detections, str(img_path))
            
            # 保存 JSON
            json_path = output_dir / f"{img_path.stem}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(annotation, f, ensure_ascii=False, indent=2)
            
            all_results.append({
                "image": img_path.name,
                "detections": len(detections),
                "annotation_file": str(json_path)
            })
            
        except Exception as e:
            print(f"  ❌ 错误: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("✅ 测试完成!")
    print(f"📁 标注文件保存在: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
