#!/usr/bin/env python3
"""
两阶段交通标志分类器（简化版 Visual Few-Shot）

阶段1：判断标志类型（限速、禁止、警告、指示）
阶段2：识别具体细节（如限速数字）

用法:
    python3 two_stage_classifier.py --test test_images/extracted_frames/D1_frame_0006.jpg --bbox "733,270,776,300"
"""

import os
import base64
import re
from pathlib import Path
from PIL import Image
from zai import ZaiClient


# ============================================================================
# 标志类型定义（含视觉特征描述）
# ============================================================================

SIGN_TYPES = {
    "1": {
        "name": "speed_limit",
        "description": "限速标志（红圈白底，中间有数字）",
        "requires_detail": True,
        "detail_prompt": """请识别这个限速标志上显示的具体数字。

视觉特征：
- 形状：圆形
- 边框：红色圆圈
- 底色：白色
- 内容：黑色数字（通常是 20、30、40、50、60、70、80、100、110、120）

请仔细观察数字，只返回数字本身，如 20、30、50、70、100。""",
        "label_format": "Speed_limit_{}_km_h"
    },
    "2": {
        "name": "prohibition",
        "description": "禁止标志",
        "requires_detail": True,
        "detail_prompt": """请判断这是哪种禁止标志。

视觉特征参考：
1. no_stopping 禁止停车 - 红圈蓝底，红色交叉❌
2. no_parking 禁止泊车 - 红圈蓝底，红色单斜杠/
3. no_entry 禁止驶入 - 红色圆形，白色横杠-
4. no_overtaking 禁止超车 - 红圈白底，两辆车图案（一红一黑）
5. no_left_turn 禁止左转 - 红圈白底，左转箭头被划掉
6. no_right_turn 禁止右转 - 红圈白底，右转箭头被划掉
7. no_u_turn 禁止掉头 - 红圈白底，U形箭头被划掉
8. other 其他禁止

只返回数字（1-8）。""",
        "label_map": {
            "1": "No_stopping_at_any_time",
            "2": "No_parking",
            "3": "No_entry_for_all_vehicles",
            "4": "No_overtaking",
            "5": "No_left_turn",
            "6": "No_right_turn",
            "7": "No_U_turn",
            "8": "Prohibition_other"
        }
    },
    "3": {
        "name": "warning",
        "description": "警告标志",
        "requires_detail": True,
        "detail_prompt": """请判断这是哪种警告标志。

视觉特征参考：
1. road_works 道路施工 - 红边黄底三角形，有人在施工/铲子图案
2. pedestrian_crossing 人行横道 - 蓝底方形，有行人走斑马线图案
3. children 注意儿童 - 红边黄底三角形，有儿童跑步图案
4. cyclists 注意自行车 - 红边黄底三角形，有自行车图案
5. bend_ahead 前方弯道 - 红边黄底三角形，有弯曲箭头
6. cross_roads 前方路口 - 红边黄底三角形，有十字交叉图案
7. slippery_road 路滑 - 红边黄底三角形，有打滑车辆图案
8. other 其他警告

只返回数字（1-8）。""",
        "label_map": {
            "1": "Road_works_ahead",
            "2": "Pedestrian_crossing",
            "3": "Children_ahead",
            "4": "Cyclists_ahead",
            "5": "Bend_to_left_ahead",
            "6": "Cross_roads_ahead",
            "7": "Slippery_road_surface",
            "8": "Warning_other"
        }
    },
    "4": {
        "name": "direction",
        "description": "指示/方向标志",
        "requires_detail": True,
        "detail_prompt": """请判断这是哪种指示或方向标志。

视觉特征参考：
1. direction_sign 方向指示牌 - 绿底白字，显示地名和箭头
2. expressway_sign 高速公路标志 - 绿底白字，带高速公路编号
3. countdown_marker 倒计时距离牌 - 绿底白条，有 100m/200m/300m 斜条
4. one_way 单行道 - 蓝底白色箭头，只指一个方向
5. ahead_only 直行 - 蓝色圆形，白色向上箭头
6. turn_left 左转 - 蓝色圆形，白色左转箭头
7. turn_right 右转 - 蓝色圆形，白色右转箭头
8. other 其他指示

只返回数字（1-8）。""",
        "label_map": {
            "1": "Direction_sign",
            "2": "Expressway_sign",
            "3": "100m_Countdown_markers_used_to_indicate_the_distance_to_an_exit_on_the_left_side_of_a_road",
            "4": "One_way_traffic",
            "5": "Ahead_only",
            "6": "Turn_left",
            "7": "Turn_right",
            "8": "Direction_other"
        }
    },
    "5": {
        "name": "other",
        "description": "其他标志",
        "requires_detail": False,
        "label": "traffic_sign_other"
    }
}


def classify_sign_two_stage(client: ZaiClient, image_path: str, bbox: list = None) -> dict:
    """
    两阶段交通标志分类
    
    Args:
        client: ZaiClient 实例
        image_path: 图片路径
        bbox: 标志区域 [x1, y1, x2, y2]
    
    Returns:
        分类结果字典
    """
    # 加载并裁剪图片
    img = Image.open(image_path).convert("RGB")
    
    if bbox:
        padding = 10
        x1 = max(0, bbox[0] - padding)
        y1 = max(0, bbox[1] - padding)
        x2 = min(img.width, bbox[2] + padding)
        y2 = min(img.height, bbox[3] + padding)
        img = img.crop((x1, y1, x2, y2))
    
    # 保存裁剪图
    temp_path = "/tmp/sign_crop_2stage.jpg"
    img.save(temp_path, "JPEG")
    
    with open(temp_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()
    
    # ========================================
    # 阶段1：判断标志类型
    # ========================================
    type_prompt = """请判断这是什么类型的交通标志：
1. 限速标志（红圈白底，中间有数字）
2. 禁止标志（红圈，禁止某种行为）
3. 警告标志（三角形或其他形状，提示危险）
4. 指示/方向标志（蓝色或绿色，指示方向或信息）
5. 其他/无法确定

只返回数字（1-5）。"""
    
    try:
        response1 = client.chat.completions.create(
            model="glm-4.6v",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}},
                    {"type": "text", "text": type_prompt}
                ]
            }],
            temperature=0.1
        )
        
        type_response = response1.choices[0].message.content.strip()
        
        # 提取类型数字
        type_match = re.search(r'[1-5]', type_response)
        if not type_match:
            return {
                "success": False,
                "label": "traffic_sign",
                "stage1_response": type_response,
                "error": "无法解析标志类型"
            }
        
        sign_type = type_match.group()
        sign_info = SIGN_TYPES.get(sign_type, SIGN_TYPES["5"])
        
        print(f"    阶段1 - 类型: {sign_info['name']} ({sign_info['description']})")
        
        # ========================================
        # 阶段2：识别具体细节
        # ========================================
        if sign_info.get("requires_detail", False):
            detail_prompt = sign_info["detail_prompt"]
            
            response2 = client.chat.completions.create(
                model="glm-4.6v",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}},
                        {"type": "text", "text": detail_prompt}
                    ]
                }],
                temperature=0.1
            )
            
            detail_response = response2.choices[0].message.content.strip()
            
            # 根据标志类型处理细节
            if sign_type == "1":  # 限速
                numbers = re.findall(r'\d+', detail_response)
                if numbers:
                    speed_value = numbers[0]
                    label = sign_info["label_format"].format(speed_value)
                    print(f"    阶段2 - 限速数字: {speed_value}")
                    return {
                        "success": True,
                        "label": label,
                        "type": sign_info["name"],
                        "detail": speed_value
                    }
            else:
                # 使用 label_map
                label_map = sign_info.get("label_map", {})
                detail_match = re.search(r'[1-8]', detail_response)
                if detail_match and detail_match.group() in label_map:
                    label = label_map[detail_match.group()]
                    print(f"    阶段2 - 具体类型: {label}")
                    return {
                        "success": True,
                        "label": label,
                        "type": sign_info["name"],
                        "detail": detail_response
                    }
        
        # 无需详细分类或分类失败
        label = sign_info.get("label", f"traffic_sign_{sign_info['name']}")
        return {
            "success": True,
            "label": label,
            "type": sign_info["name"]
        }
    
    except Exception as e:
        print(f"    ⚠️ 分类失败: {e}")
        return {
            "success": False,
            "label": "traffic_sign",
            "error": str(e)
        }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="两阶段交通标志分类器")
    parser.add_argument("--test", type=str, required=True, help="测试图片路径")
    parser.add_argument("--bbox", type=str, help="裁剪区域 x1,y1,x2,y2")
    args = parser.parse_args()
    
    api_key = os.getenv("ZAI_API_KEY")
    if not api_key:
        print("❌ 请设置 ZAI_API_KEY")
        return
    
    client = ZaiClient(api_key=api_key)
    
    print("=" * 60)
    print("🔍 两阶段交通标志分类")
    print("=" * 60)
    
    print(f"\n📷 图片: {args.test}")
    
    bbox = None
    if args.bbox:
        bbox = [int(x) for x in args.bbox.split(",")]
        print(f"📦 区域: {bbox}")
    
    print("\n⏳ 分类中...")
    
    result = classify_sign_two_stage(client, args.test, bbox)
    
    print("\n" + "-" * 40)
    print("📊 分类结果:")
    print(f"   标签: {result['label']}")
    if result.get("type"):
        print(f"   类型: {result['type']}")
    if result.get("detail"):
        print(f"   细节: {result['detail']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
