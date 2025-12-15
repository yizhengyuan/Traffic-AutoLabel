#!/usr/bin/env python3
"""
GLM-4.6V 数据标注脚本 V2
- 精细化标签体系
- 四类物体：行人、车辆、交通标志、施工标志
- 交通标志细分为具体类型
- 输出 X-AnyLabeling 兼容的 JSON 格式
"""

import os
import json
import base64
from pathlib import Path
from PIL import Image
from zai import ZaiClient

# ============================================================================
# 配置
# ============================================================================
API_KEY = os.getenv("ZAI_API_KEY", "")

# ============================================================================
# 精细化标签体系
# ============================================================================

# 行人类（粗颗粒度：pedestrian）
PEDESTRIAN_LABELS = [
    "pedestrian",           # 行人
    "cyclist",              # 骑自行车的人
    "child",                # 儿童
]

# 车辆类（粗颗粒度：vehicle）
VEHICLE_LABELS = [
    "car",                  # 轿车
    "truck",                # 货车/卡车
    "bus",                  # 公交车
    "motorcycle",           # 摩托车
    "bicycle",              # 自行车
    "van",                  # 面包车
    "suv",                  # SUV
    "taxi",                 # 出租车
]

# 交通标志类（粗颗粒度：traffic_sign）- 基于 examples/signs 精细分类
TRAFFIC_SIGN_LABELS = {
    # === 限速类 ===
    "speed_limit": "Speed limit sign (限速标志)",
    "speed_limit_20": "Speed limit 20 km/h",
    "speed_limit_30": "Speed limit 30 km/h",
    "speed_limit_40": "Speed limit 40 km/h",
    "speed_limit_50": "Speed limit 50 km/h",
    "speed_limit_60": "Speed limit 60 km/h",
    "speed_limit_70": "Speed limit 70 km/h",
    "speed_limit_80": "Speed limit 80 km/h",
    "speed_limit_100": "Speed limit 100 km/h",
    "speed_limit_120": "Speed limit 120 km/h",
    
    # === 禁止类 ===
    "no_entry": "No entry for vehicles (禁止驶入)",
    "no_parking": "No parking (禁止停车)",
    "no_stopping": "No stopping (禁止停留)",
    "no_overtaking": "No overtaking (禁止超车)",
    "no_left_turn": "No left turn (禁止左转)",
    "no_right_turn": "No right turn (禁止右转)",
    "no_u_turn": "No U-turn (禁止掉头)",
    "no_horn": "No use of horn (禁止鸣笛)",
    "no_pedestrians": "No pedestrians (禁止行人)",
    "no_bicycles": "No bicycles (禁止自行车)",
    "no_motorcycles": "No motorcycles (禁止摩托车)",
    "no_trucks": "No trucks/goods vehicles (禁止货车)",
    "height_limit": "Height limit (限高)",
    "weight_limit": "Weight limit (限重)",
    "width_limit": "Width limit (限宽)",
    
    # === 警告类 ===
    "road_works": "Road works ahead (前方施工)",
    "slippery_road": "Slippery road ahead (路滑)",
    "steep_hill": "Steep hill ahead (陡坡)",
    "bend_ahead": "Bend ahead (弯道)",
    "crossroads": "Cross roads ahead (十字路口)",
    "t_junction": "T-junction ahead (T形路口)",
    "traffic_lights": "Traffic lights ahead (前方红绿灯)",
    "pedestrian_crossing": "Pedestrian crossing ahead (人行横道)",
    "children": "Children ahead (注意儿童)",
    "school": "School ahead (注意学校)",
    "cyclists": "Cyclists ahead (注意自行车)",
    "cattle": "Cattle ahead (注意牲畜)",
    "road_narrows": "Road narrows ahead (道路变窄)",
    "two_way_traffic": "Two-way traffic (双向交通)",
    "falling_rocks": "Risk of falling rocks (注意落石)",
    "uneven_road": "Uneven road surface (路面不平)",
    
    # === 指示类 ===
    "direction_sign": "Direction sign (方向指示牌)",
    "street_sign": "Street direction sign (路名牌)",
    "expressway_sign": "Expressway sign (高速公路标志)",
    "exit_sign": "Exit sign (出口标志)",
    "lane_sign": "Lane sign (车道指示)",
    "one_way": "One way traffic (单行道)",
    "ahead_only": "Ahead only (直行)",
    "turn_left": "Turn left (左转)",
    "turn_right": "Turn right (右转)",
    "keep_left": "Keep left (靠左)",
    "keep_right": "Keep right (靠右)",
    "roundabout": "Roundabout (环岛)",
    "parking": "Parking place (停车场)",
    "bus_lane": "Bus lane (公交车道)",
    "bus_stop": "Bus stop (公交站)",
    
    # === 交通设施 ===
    "traffic_light_red": "Traffic light - Red",
    "traffic_light_yellow": "Traffic light - Yellow", 
    "traffic_light_green": "Traffic light - Green",
    "traffic_light": "Traffic light (交通信号灯)",
    
    # === 其他 ===
    "stop": "Stop sign (停车让行)",
    "give_way": "Give way (减速让行)",
    "countdown_marker": "Countdown marker (倒计时牌)",
    
    # === 粗颗粒度 fallback ===
    "traffic_sign": "Unknown traffic sign (未知交通标志)",
}

# 施工标志类（粗颗粒度：construction）
CONSTRUCTION_LABELS = {
    "traffic_cone": "Traffic cone (锥桶)",
    "construction_barrier": "Construction barrier (施工围挡)",
    "warning_light": "Warning light (警示灯)",
    "road_works_sign": "Road works sign (施工标志牌)",
    "detour_sign": "Detour sign (绕行标志)",
    "construction": "Construction zone (施工区域)",  # fallback
}

# 类别颜色（用于可视化）
CATEGORY_COLORS = {
    "pedestrian": (255, 0, 0),      # 红色
    "vehicle": (0, 255, 0),         # 绿色
    "traffic_sign": (0, 0, 255),    # 蓝色
    "construction": (255, 165, 0),  # 橙色
}

# ============================================================================
# 工具函数
# ============================================================================

def image_to_base64_url(image_path: str) -> str:
    """将本地图片转换为 base64 data URL"""
    path = Path(image_path)
    ext = path.suffix.lower()
    mime_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}
    mime_type = mime_types.get(ext, 'image/jpeg')
    
    with open(path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    return f"data:{mime_type};base64,{image_data}"


def get_image_size(image_path: str) -> tuple:
    """获取图片尺寸"""
    with Image.open(image_path) as img:
        return img.width, img.height


def get_category(label: str) -> str:
    """根据标签获取粗颗粒度类别"""
    label_lower = label.lower().replace(" ", "_").replace("-", "_")
    
    # 行人类
    if any(p in label_lower for p in ["pedestrian", "person", "people", "child", "cyclist"]):
        return "pedestrian"
    
    # 车辆类
    if any(v in label_lower for v in ["car", "truck", "bus", "motorcycle", "bicycle", "van", "suv", "taxi", "vehicle"]):
        return "vehicle"
    
    # 施工类
    if any(c in label_lower for c in ["cone", "construction", "barrier", "road_work", "detour"]):
        return "construction"
    
    # 交通标志类
    if any(s in label_lower for s in ["sign", "speed", "limit", "no_", "traffic", "light", "stop", "give_way", "direction", "exit", "lane"]):
        return "traffic_sign"
    
    # 默认
    return "unknown"


def normalize_label(label: str) -> str:
    """标准化标签为英文格式"""
    label = label.strip().lower()
    
    # 中英文映射
    mapping = {
        # 行人
        "行人": "pedestrian", "人": "pedestrian", "路人": "pedestrian",
        "骑车人": "cyclist", "骑自行车的人": "cyclist", "骑自行车": "cyclist",
        "儿童": "child", "小孩": "child",
        
        # 车辆
        "车": "car", "汽车": "car", "轿车": "car", "小汽车": "car",
        "货车": "truck", "卡车": "truck",
        "公交车": "bus", "巴士": "bus", "大巴": "bus",
        "摩托车": "motorcycle", "电动车": "motorcycle",
        "自行车": "bicycle", "单车": "bicycle",
        "面包车": "van", "越野车": "suv", "出租车": "taxi",
        "车辆": "car",  # 默认
        
        # 交通标志
        "限速": "speed_limit", "限速牌": "speed_limit",
        "限速70": "speed_limit_70", "限速60": "speed_limit_60",
        "限速80": "speed_limit_80", "限速100": "speed_limit_100",
        "限速50": "speed_limit_50", "限速40": "speed_limit_40",
        "禁止停车": "no_parking", "禁止驶入": "no_entry",
        "禁止超车": "no_overtaking", "禁止掉头": "no_u_turn",
        "禁止左转": "no_left_turn", "禁止右转": "no_right_turn",
        "红绿灯": "traffic_light", "交通灯": "traffic_light", "信号灯": "traffic_light",
        "指示牌": "direction_sign", "路牌": "street_sign", "方向牌": "direction_sign",
        "出口": "exit_sign", "入口": "entrance_sign",
        "停": "stop", "让行": "give_way",
        "交通标志": "traffic_sign", "标志": "traffic_sign",
        
        # 施工
        "锥桶": "traffic_cone", "路锥": "traffic_cone", "交通锥": "traffic_cone",
        "施工": "construction", "围挡": "construction_barrier",
    }
    
    # 直接匹配
    if label in mapping:
        return mapping[label]
    
    # 部分匹配
    for cn, en in mapping.items():
        if cn in label:
            return en
    
    # 保持原样（已经是英文的情况）
    return label.replace(" ", "_").replace("-", "_")


# ============================================================================
# 检测函数
# ============================================================================

def detect_objects(client: ZaiClient, image_path: str) -> list:
    """使用 GLM-4.6V 检测图片中的目标物体（精细化标签）"""
    base64_url = image_to_base64_url(image_path)
    width, height = get_image_size(image_path)
    
    prompt = """You are an expert traffic scene analyst. Please carefully analyze this image and detect all objects in these 4 categories:

## 1. PEDESTRIANS (行人)
- pedestrian, cyclist, child

## 2. VEHICLES (车辆) - Exclude first-person ego vehicle!
- car, truck, bus, motorcycle, bicycle, van, suv, taxi

## 3. TRAFFIC SIGNS (交通标志) - Use specific labels!
Speed limits: speed_limit_20, speed_limit_30, speed_limit_40, speed_limit_50, speed_limit_60, speed_limit_70, speed_limit_80, speed_limit_100, speed_limit_120
Prohibitions: no_entry, no_parking, no_stopping, no_overtaking, no_left_turn, no_right_turn, no_u_turn, no_horn
Warnings: road_works, slippery_road, steep_hill, bend_ahead, crossroads, t_junction, pedestrian_crossing, children, school, cyclists, road_narrows
Directions: direction_sign, street_sign, expressway_sign, exit_sign, lane_sign, one_way, ahead_only, turn_left, turn_right, roundabout
Traffic lights: traffic_light, traffic_light_red, traffic_light_yellow, traffic_light_green
Others: stop, give_way, countdown_marker
If unknown: traffic_sign

## 4. CONSTRUCTION (施工标志)
- traffic_cone, construction_barrier, warning_light, road_works_sign, detour_sign

## IMPORTANT RULES:
- This is first-person riding view - DO NOT label the ego motorcycle/bicycle at bottom
- Use English labels only (as listed above)
- For traffic signs, use the most specific label possible
- If you cannot identify the exact type, use the general category

Return JSON array format:
[{"label": "car", "bbox_2d": [xmin, ymin, xmax, ymax]}, ...]

If no objects found, return []
Only return JSON, no explanation."""

    response = client.chat.completions.create(
        model="glm-4.6v",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": base64_url}},
                    {"type": "text", "text": prompt}
                ]
            }
        ]
    )
    
    result_text = response.choices[0].message.content
    
    # 解析 JSON
    try:
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
            if "label" not in det or "bbox_2d" not in det:
                continue
                
            raw_bbox = det["bbox_2d"]
            
            # 坐标转换（0-1000 归一化 -> 像素）
            bbox = [
                int(round(raw_bbox[0] / 1000 * width)),
                int(round(raw_bbox[1] / 1000 * height)),
                int(round(raw_bbox[2] / 1000 * width)),
                int(round(raw_bbox[3] / 1000 * height))
            ]
            
            # 确保坐标在范围内
            bbox = [
                max(0, min(bbox[0], width)),
                max(0, min(bbox[1], height)),
                max(0, min(bbox[2], width)),
                max(0, min(bbox[3], height))
            ]
            
            # 标准化标签
            label = normalize_label(det["label"])
            category = get_category(label)
            
            processed.append({
                "label": label,
                "category": category,
                "bbox": bbox,
                "original": det["label"]
            })
        
        return processed
        
    except Exception as e:
        print(f"  ⚠️ JSON parse error: {e}")
        print(f"  Raw: {result_text[:300]}")
        return []


def to_xanylabeling_format(detections: list, image_path: str) -> dict:
    """转换为 X-AnyLabeling 格式"""
    width, height = get_image_size(image_path)
    
    shapes = []
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        shapes.append({
            "label": det["label"],
            "text": det.get("original", ""),
            "points": [[x1, y1], [x2, y2]],
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
    if not API_KEY:
        print("❌ Please set ZAI_API_KEY environment variable")
        return
    
    # 获取 D1 图片
    images_dir = Path("test_images/extracted_frames")
    images = sorted([f for f in images_dir.glob("D1_*.jpg")])
    
    # 处理全部 D1 图片
    test_images = images  # 全部 169 张
    
    print("=" * 70)
    print(f"🏷️  GLM-4.6V Auto Labeling V2 - D1 series ({len(test_images)} images)")
    print("=" * 70)
    
    client = ZaiClient(api_key=API_KEY)
    
    # 创建输出目录
    output_dir = Path("output/d1_annotations_v2")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    stats = {"pedestrian": 0, "vehicle": 0, "traffic_sign": 0, "construction": 0}
    
    for i, img_path in enumerate(test_images, 1):
        print(f"\n📷 [{i}/{len(test_images)}] {img_path.name}")
        print("-" * 50)
        
        try:
            detections = detect_objects(client, str(img_path))
            
            print(f"  ✅ Detected {len(detections)} objects:")
            for det in detections:
                cat = det["category"]
                stats[cat] = stats.get(cat, 0) + 1
                color_emoji = {"pedestrian": "🔴", "vehicle": "🟢", "traffic_sign": "🔵", "construction": "🟠"}.get(cat, "⚪")
                print(f"     {color_emoji} {det['label']} [{cat}] {det['bbox']}")
            
            # 保存 JSON
            annotation = to_xanylabeling_format(detections, str(img_path))
            json_path = output_dir / f"{img_path.stem}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(annotation, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("📊 Statistics:")
    for cat, count in stats.items():
        print(f"   {cat}: {count}")
    print(f"📁 Annotations saved to: {output_dir}")
    print("=" * 70)


if __name__ == "__main__":
    main()
