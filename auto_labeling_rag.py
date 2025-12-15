#!/usr/bin/env python3
"""
GLM-4.6V + RAG 增强标注脚本

功能：
1. 基础检测：识别行人、车辆、交通标志、施工标志
2. RAG 精排：对交通标志进行细粒度分类（匹配 188 种标准标志）

用法:
    python3 auto_labeling_rag.py --prefix D1 --limit 10
"""

import os
import json
import base64
import argparse
from pathlib import Path
from PIL import Image
from zai import ZaiClient


# ============================================================================
# 标准交通标志候选库
# ============================================================================

# 限速标志
SPEED_LIMIT_CANDIDATES = [
    "speed_limit_20", "speed_limit_30", "speed_limit_40", "speed_limit_50",
    "speed_limit_60", "speed_limit_70", "speed_limit_80", "speed_limit_100", "speed_limit_120"
]

# 禁止标志
PROHIBITION_CANDIDATES = [
    "no_entry", "no_stopping", "no_parking", "no_overtaking",
    "no_left_turn", "no_right_turn", "no_u_turn", "no_horn"
]

# 警告标志
WARNING_CANDIDATES = [
    "road_works", "pedestrian_crossing", "children", "cyclists",
    "bend_ahead", "crossroads", "slippery_road", "falling_rocks"
]

# 指示标志
DIRECTION_CANDIDATES = [
    "direction_sign", "expressway_sign", "street_sign", "exit_sign",
    "one_way", "ahead_only", "turn_left", "turn_right", "keep_left", "keep_right"
]

# 信号灯
TRAFFIC_LIGHT_CANDIDATES = [
    "traffic_light", "traffic_light_red", "traffic_light_yellow", "traffic_light_green"
]

# 其他
OTHER_SIGN_CANDIDATES = [
    "stop", "give_way", "roundabout", "parking", "bus_stop"
]

# 所有候选
ALL_SIGN_CANDIDATES = (
    SPEED_LIMIT_CANDIDATES + PROHIBITION_CANDIDATES + 
    WARNING_CANDIDATES + DIRECTION_CANDIDATES + 
    TRAFFIC_LIGHT_CANDIDATES + OTHER_SIGN_CANDIDATES
)


# ============================================================================
# 辅助函数
# ============================================================================

def get_category(label: str) -> str:
    """根据标签获取粗颗粒度类别"""
    label_lower = label.lower().replace(" ", "_").replace("-", "_")
    
    if any(p in label_lower for p in ["pedestrian", "person", "people", "child", "cyclist", "crowd"]):
        return "pedestrian"
    if any(v in label_lower for v in ["car", "truck", "bus", "motorcycle", "bicycle", "van", "suv", "taxi", "vehicle"]):
        return "vehicle"
    if any(c in label_lower for c in ["cone", "construction", "barrier", "road_work", "detour"]):
        return "construction"
    if any(s in label_lower for s in ["sign", "speed", "limit", "no_", "traffic", "light", "stop", "give_way", "direction", "exit", "lane"]):
        return "traffic_sign"
    return "unknown"


def image_to_base64_url(image_path: str) -> str:
    with open(image_path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    ext = Path(image_path).suffix.lower()
    mime_type = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}.get(ext, 'image/jpeg')
    return f"data:{mime_type};base64,{image_data}"


def get_image_size(image_path: str) -> tuple:
    with Image.open(image_path) as img:
        return img.width, img.height


# ============================================================================
# RAG 细粒度分类
# ============================================================================

def classify_sign_with_rag(client: ZaiClient, image_path: str, bbox: list) -> str:
    """
    对检测到的交通标志区域进行 RAG 细粒度分类
    
    Args:
        client: ZaiClient 实例
        image_path: 原始图片路径
        bbox: 标志区域 [x1, y1, x2, y2]
        
    Returns:
        细粒度标签
    """
    # 扩大裁剪区域（避免边界太紧）
    x1, y1, x2, y2 = bbox
    padding = 5
    
    img = Image.open(image_path)
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(img.width, x2 + padding)
    y2 = min(img.height, y2 + padding)
    
    # 裁剪标志区域
    sign_crop = img.crop((x1, y1, x2, y2))
    
    # 保存临时文件
    temp_path = "/tmp/sign_crop.jpg"
    sign_crop.save(temp_path, "JPEG")
    
    # 读取并编码
    with open(temp_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()
    
    # 构建候选列表
    candidate_list = "\n".join([f"{i+1}. {c}" for i, c in enumerate(ALL_SIGN_CANDIDATES)])
    
    prompt = f"""请仔细观察这个交通标志，从以下选项中选择最匹配的：

{candidate_list}

规则：
1. 观察标志的颜色、形状、文字、数字
2. 如果是限速标志，请识别具体数字
3. 如果都不匹配，返回 "traffic_sign"

请只返回选项编号（如 1、2、3），不要其他解释。"""

    try:
        response = client.chat.completions.create(
            model="glm-4.6v",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}},
                    {"type": "text", "text": prompt}
                ]
            }]
        )
        
        choice = response.choices[0].message.content.strip()
        
        # 解析选择
        try:
            # 提取数字
            import re
            numbers = re.findall(r'\d+', choice)
            if numbers:
                idx = int(numbers[0]) - 1
                if 0 <= idx < len(ALL_SIGN_CANDIDATES):
                    return ALL_SIGN_CANDIDATES[idx]
        except:
            pass
        
        return "traffic_sign"
        
    except Exception as e:
        print(f"    ⚠️ RAG 分类失败: {e}")
        return "traffic_sign"


# ============================================================================
# 主检测函数
# ============================================================================

def detect_objects(client: ZaiClient, image_path: str, use_rag: bool = False, max_retries: int = 3) -> list:
    """检测图片中的目标"""
    base64_url = image_to_base64_url(image_path)
    width, height = get_image_size(image_path)
    
    prompt = """请检测图片中的以下4类物体，返回JSON格式。

## 检测类别（使用英文标签）：
1. 行人：pedestrian, cyclist, child
   - 如果行人很多（超过5人），可以用 crowd 标签框住整个人群区域
2. 车辆：car, truck, bus, motorcycle, bicycle, van, taxi（不要标注第一人称摩托车/自行车）
3. 交通标志：traffic_sign（后续会用 RAG 细分）
4. 施工标志：traffic_cone, construction_barrier

## 返回格式：
[{"label": "car", "bbox_2d": [xmin, ymin, xmax, ymax]}, {"label": "traffic_sign", "bbox_2d": [x1, y1, x2, y2]}]

如果没有目标，返回 []

重要：只返回JSON数组，不要其他文字！"""

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="glm-4.6v",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": base64_url}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if not result_text or result_text.strip() == "":
                if attempt < max_retries - 1:
                    print(f"  ⚠️ Empty response, retrying ({attempt + 2}/{max_retries})...")
                    continue
                return []
            
            # 解析 JSON
            if "```json" in result_text:
                json_str = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                json_str = result_text.split("```")[1].split("```")[0].strip()
            elif "[" in result_text:
                json_str = result_text[result_text.find("["):result_text.rfind("]")+1]
            else:
                json_str = result_text.strip()
            
            if json_str == "[]" or json_str == "":
                return []
            
            # 修复被截断的 JSON
            if json_str and not json_str.endswith("]"):
                last_complete = json_str.rfind("},")
                if last_complete > 0:
                    json_str = json_str[:last_complete+1] + "]"
                    print(f"  ⚠️ JSON truncated, recovered {json_str.count('label')} objects")
            
            detections = json.loads(json_str)
            processed = []
            
            for det in detections:
                if "label" not in det or "bbox_2d" not in det:
                    continue
                    
                raw_bbox = det["bbox_2d"]
                bbox = [
                    int(round(raw_bbox[0] / 1000 * width)),
                    int(round(raw_bbox[1] / 1000 * height)),
                    int(round(raw_bbox[2] / 1000 * width)),
                    int(round(raw_bbox[3] / 1000 * height))
                ]
                
                label = det["label"].lower().replace(" ", "_").replace("-", "_")
                category = get_category(label)
                
                # RAG 细粒度分类（仅对交通标志）
                if use_rag and category == "traffic_sign" and label in ["traffic_sign", "sign"]:
                    print(f"    🔍 RAG 精排交通标志...")
                    label = classify_sign_with_rag(client, image_path, bbox)
                    print(f"    → {label}")
                
                processed.append({
                    "label": label,
                    "category": category,
                    "bbox": bbox
                })
            
            return processed
            
        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                print(f"  ⚠️ JSON parse error, retrying ({attempt + 2}/{max_retries})...")
                continue
            print(f"  ⚠️ JSON parse error after {max_retries} attempts: {e}")
            return []
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"  ⚠️ Error: {e}, retrying ({attempt + 2}/{max_retries})...")
                continue
            return []
    
    return []


# ============================================================================
# 输出函数
# ============================================================================

def to_xanylabeling_format(detections: list, image_path: str) -> dict:
    """转换为 X-AnyLabeling 格式"""
    width, height = get_image_size(image_path)
    
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
            "flags": {"category": det["category"]}
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


# ============================================================================
# 主函数
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="GLM-4.6V + RAG 增强标注")
    parser.add_argument("--prefix", type=str, required=True, help="图片前缀 (如 D1, D2)")
    parser.add_argument("--limit", type=int, default=None, help="限制处理数量")
    parser.add_argument("--rag", action="store_true", help="启用 RAG 细粒度分类")
    parser.add_argument("--images-dir", type=str, default="test_images/extracted_frames")
    args = parser.parse_args()
    
    # 初始化
    api_key = os.getenv("ZAI_API_KEY")
    if not api_key:
        print("❌ 请设置 ZAI_API_KEY 环境变量")
        return
    
    client = ZaiClient(api_key=api_key)
    
    # 获取图片列表
    images_dir = Path(args.images_dir)
    image_files = sorted(images_dir.glob(f"{args.prefix}_*.jpg"))
    
    if args.limit:
        image_files = image_files[:args.limit]
    
    if not image_files:
        print(f"❌ 没有找到 {args.prefix} 开头的图片")
        return
    
    # 创建输出目录
    output_dir = Path(f"output/{args.prefix.lower()}_annotations_rag")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 统计
    width, height = get_image_size(str(image_files[0]))
    stats = {"pedestrian": 0, "vehicle": 0, "traffic_sign": 0, "construction": 0}
    
    print("=" * 70)
    print(f"🏷️  GLM-4.6V {'+ RAG ' if args.rag else ''}Auto Labeling - {args.prefix} series")
    print(f"   Images: {len(image_files)} | Resolution: {width}x{height}")
    print(f"   RAG Mode: {'✅ Enabled' if args.rag else '❌ Disabled'}")
    print("=" * 70)
    
    for i, img_path in enumerate(image_files):
        print(f"\n📷 [{i+1}/{len(image_files)}] {img_path.name}")
        print("-" * 50)
        
        # 检测
        detections = detect_objects(client, str(img_path), use_rag=args.rag)
        
        # 输出
        labels = [d["label"] for d in detections]
        categories = [d["category"] for d in detections]
        
        print(f"  ✅ Detected {len(detections)} objects:")
        for det in detections:
            emoji = {"pedestrian": "🔴", "vehicle": "🟢", "traffic_sign": "🔵", "construction": "🟠"}.get(det["category"], "⚪")
            print(f"     {emoji} {det['label']} [{det['category']}] {det['bbox']}")
            stats[det["category"]] = stats.get(det["category"], 0) + 1
        
        # 保存
        annotation = to_xanylabeling_format(detections, str(img_path))
        output_path = output_dir / f"{img_path.stem}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(annotation, f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 70)
    print("📊 Statistics:")
    for cat, count in stats.items():
        print(f"   {cat}: {count}")
    print(f"📁 Annotations saved to: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
