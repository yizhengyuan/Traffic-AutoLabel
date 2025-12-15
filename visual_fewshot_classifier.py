#!/usr/bin/env python3
"""
Visual Few-Shot 交通标志分类器

使用视觉对比方式，把标准图拼成网格让 GLM-4.6V 直接对比识别。
比纯文本 RAG 更准确，能区分"限速50"和"限速60"。

用法:
    python3 visual_fewshot_classifier.py --test test_images/extracted_frames/D1_frame_0006.jpg
"""

import os
import base64
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from zai import ZaiClient


# ============================================================================
# 标准图库配置
# ============================================================================

STANDARDS_DIR = Path("examples/signs/highres/png2560px")

# 按类别组织标志（基于文件名关键词）
SIGN_CATEGORIES = {
    "speed_limit": ["Speed_limit", "Variable_speed"],
    "prohibition": ["No_", "Prohibit", "End_of"],
    "warning": ["ahead", "Cattle", "Children", "Cyclist", "Danger", "Fog", "Horses"],
    "direction": ["Direction", "Turn", "Keep", "Ahead_only", "One_way"],
    "distance": ["Countdown", "Distance", "100m", "200m", "300m"],
    "bus_lane": ["Bus_lane", "bus_lane"],
    "other": []  # 默认
}


def get_sign_category(filename: str) -> str:
    """根据文件名判断标志类别"""
    for cat, keywords in SIGN_CATEGORIES.items():
        for kw in keywords:
            if kw.lower() in filename.lower():
                return cat
    return "other"


def load_standard_signs() -> dict:
    """加载所有标准标志并按类别分组"""
    if not STANDARDS_DIR.exists():
        print(f"⚠️ 找不到标准图库: {STANDARDS_DIR}")
        return {}
    
    signs_by_category = {cat: [] for cat in SIGN_CATEGORIES}
    
    for f in sorted(STANDARDS_DIR.glob("*.png")):
        cat = get_sign_category(f.stem)
        signs_by_category[cat].append({
            "name": f.stem,
            "path": str(f)
        })
    
    return signs_by_category


def create_grid_image(images: list, labels: list, cols: int = 4, cell_size: int = 150) -> Image.Image:
    """
    把多张图片拼成网格图
    
    Args:
        images: PIL Image 列表
        labels: 每张图的标签（A, B, C...）
        cols: 每行多少列
        cell_size: 每个格子的大小
    
    Returns:
        拼接好的网格图
    """
    rows = (len(images) + cols - 1) // cols
    
    # 创建画布
    grid_width = cols * cell_size
    grid_height = rows * cell_size
    grid = Image.new("RGB", (grid_width, grid_height), (255, 255, 255))
    draw = ImageDraw.Draw(grid)
    
    for i, (img, label) in enumerate(zip(images, labels)):
        row = i // cols
        col = i % cols
        
        # 缩放图片
        img_resized = img.copy()
        img_resized.thumbnail((cell_size - 20, cell_size - 30), Image.Resampling.LANCZOS)
        
        # 计算位置（居中）
        x = col * cell_size + (cell_size - img_resized.width) // 2
        y = row * cell_size + 20 + (cell_size - 30 - img_resized.height) // 2
        
        # 粘贴图片
        grid.paste(img_resized, (x, y))
        
        # 画标签
        label_x = col * cell_size + cell_size // 2
        label_y = row * cell_size + 5
        draw.text((label_x, label_y), label, fill=(0, 0, 0), anchor="mt")
    
    return grid


def create_comparison_image(target_img: Image.Image, candidates: list, max_candidates: int = 16) -> tuple:
    """
    创建对比图：左边是待识别图，右边是候选库网格
    
    Args:
        target_img: 待识别的图片
        candidates: 候选标志列表 [{"name": ..., "path": ...}, ...]
        max_candidates: 最多显示多少个候选
    
    Returns:
        (合并图, 标签映射字典)
    """
    # 限制候选数量
    candidates = candidates[:max_candidates]
    
    # 生成标签 A, B, C...
    labels = [chr(65 + i) for i in range(len(candidates))]  # A=65
    label_map = {labels[i]: candidates[i]["name"] for i in range(len(candidates))}
    
    # 加载候选图片
    candidate_images = []
    for c in candidates:
        try:
            img = Image.open(c["path"]).convert("RGB")
            candidate_images.append(img)
        except:
            continue
    
    # 创建候选网格
    grid = create_grid_image(candidate_images, labels, cols=4, cell_size=150)
    
    # 调整目标图大小
    target_resized = target_img.copy()
    target_resized.thumbnail((300, 300), Image.Resampling.LANCZOS)
    
    # 创建最终合并图
    margin = 20
    total_width = target_resized.width + margin + grid.width + margin * 2
    total_height = max(target_resized.height, grid.height) + margin * 2
    
    merged = Image.new("RGB", (total_width, total_height), (240, 240, 240))
    
    # 粘贴目标图（左边）
    merged.paste(target_resized, (margin, (total_height - target_resized.height) // 2))
    
    # 粘贴候选网格（右边）
    merged.paste(grid, (margin + target_resized.width + margin, (total_height - grid.height) // 2))
    
    # 添加标题
    draw = ImageDraw.Draw(merged)
    draw.text((margin + target_resized.width // 2, 5), "待识别", fill=(0, 0, 0), anchor="mt")
    draw.text((margin + target_resized.width + margin + grid.width // 2, 5), "候选库", fill=(0, 0, 0), anchor="mt")
    
    return merged, label_map


def classify_with_visual_fewshot(client: ZaiClient, target_img_path: str, bbox: list = None, category_hint: str = None) -> dict:
    """
    使用 Visual Few-Shot 方式分类交通标志
    
    Args:
        client: ZaiClient 实例
        target_img_path: 目标图片路径
        bbox: 标志区域 [x1, y1, x2, y2]，如果提供则裁剪
        category_hint: 类别提示，用于缩小候选范围
    
    Returns:
        分类结果
    """
    # 加载目标图片
    img = Image.open(target_img_path).convert("RGB")
    
    # 如果有 bbox，裁剪
    if bbox:
        padding = 10
        x1 = max(0, bbox[0] - padding)
        y1 = max(0, bbox[1] - padding)
        x2 = min(img.width, bbox[2] + padding)
        y2 = min(img.height, bbox[3] + padding)
        img = img.crop((x1, y1, x2, y2))
    
    # 加载标准图库
    signs_by_cat = load_standard_signs()
    
    # 确定候选范围
    if category_hint and category_hint in signs_by_cat:
        candidates = signs_by_cat[category_hint]
    else:
        # 如果没有提示，先做粗分类
        # 这里简单起见，用限速类 + 禁止类作为默认候选
        candidates = signs_by_cat.get("speed_limit", []) + signs_by_cat.get("prohibition", [])[:10]
    
    if not candidates:
        # 如果没有候选，用所有标志
        for cat in signs_by_cat.values():
            candidates.extend(cat)
        candidates = candidates[:20]
    
    print(f"    📚 候选库: {len(candidates)} 张标准图")
    
    # 创建对比图
    comparison_img, label_map = create_comparison_image(img, candidates)
    
    # 保存对比图（调试用）
    temp_path = "/tmp/visual_comparison.jpg"
    comparison_img.save(temp_path, "JPEG", quality=95)
    
    # 编码
    with open(temp_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()
    
    # 构建 prompt
    label_list = "\n".join([f"  {label}: {name}" for label, name in sorted(label_map.items())])
    
    prompt = f"""这是一张交通标志对比图。

左侧是【待识别图片】（从道路视频中裁剪）。
右侧是【候选库】，每张标准图标有字母编号（A, B, C...）。

候选项：
{label_list}

任务：
1. 仔细观察左侧待识别图的颜色、形状、文字、数字
2. 与右侧候选库逐一对比
3. 选择最匹配的那一张

规则：
- 如果是限速标志，请仔细识别数字（50 和 60 是不同的！）
- 如果都不像，返回 "NONE"

请只返回字母编号（如 A、B、C），不要其他解释。"""

    try:
        response = client.chat.completions.create(
            model="glm-4.6v",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}},
                    {"type": "text", "text": prompt}
                ]
            }],
            temperature=0.1  # 低温度减少幻觉
        )
        
        choice = response.choices[0].message.content.strip().upper()
        
        # 解析结果
        selected_name = None
        if choice in label_map:
            selected_name = label_map[choice]
        else:
            # 尝试提取第一个字母
            for char in choice:
                if char in label_map:
                    selected_name = label_map[char]
                    choice = char
                    break
        
        if selected_name:
            # ============================================================
            # 二阶段：如果是通用限速标志，进一步识别具体数字
            # ============================================================
            if "Speed_limit" in selected_name or "speed" in selected_name.lower():
                print("    🔎 二阶段：识别限速数字...")
                
                # 重新读取裁剪图
                with open(temp_path.replace("visual_comparison", "target_crop"), "rb") as f:
                    crop_data = base64.b64encode(f.read()).decode()
                
                # 直接用裁剪图识别数字
                img_crop = Image.open(target_img_path).convert("RGB")
                if bbox:
                    padding = 10
                    x1 = max(0, bbox[0] - padding)
                    y1 = max(0, bbox[1] - padding)
                    x2 = min(img_crop.width, bbox[2] + padding)
                    y2 = min(img_crop.height, bbox[3] + padding)
                    img_crop = img_crop.crop((x1, y1, x2, y2))
                
                crop_temp = "/tmp/target_crop.jpg"
                img_crop.save(crop_temp, "JPEG")
                
                with open(crop_temp, "rb") as f:
                    crop_data = base64.b64encode(f.read()).decode()
                
                number_response = client.chat.completions.create(
                    model="glm-4.6v",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{crop_data}"}},
                            {"type": "text", "text": "请识别这个限速标志上显示的具体数字。只返回数字，如 20、50、70、100。"}
                        ]
                    }],
                    temperature=0.1
                )
                
                number_text = number_response.choices[0].message.content.strip()
                
                import re
                numbers = re.findall(r'\d+', number_text)
                if numbers:
                    speed_value = numbers[0]
                    refined_label = f"Speed_limit_{speed_value}_km_h"
                    print(f"    → 识别到数字: {speed_value}")
                    return {
                        "success": True,
                        "choice": choice,
                        "label": refined_label,
                        "base_label": selected_name,
                        "speed_value": speed_value,
                        "candidates_count": len(candidates),
                        "comparison_image": temp_path
                    }
            
            return {
                "success": True,
                "choice": choice,
                "label": selected_name,
                "candidates_count": len(candidates),
                "comparison_image": temp_path
            }
        
        elif choice == "NONE":
            return {
                "success": False,
                "choice": "NONE",
                "label": "traffic_sign_unknown",
                "candidates_count": len(candidates)
            }
        else:
            return {
                "success": False,
                "choice": choice,
                "label": "traffic_sign",
                "raw_response": choice
            }
    
    except Exception as e:
        print(f"    ⚠️ Visual Few-Shot 失败: {e}")
        return {
            "success": False,
            "label": "traffic_sign",
            "error": str(e)
        }


def demo_visual_fewshot(image_path: str, bbox: list = None):
    """演示 Visual Few-Shot 分类"""
    print("=" * 60)
    print("🔍 Visual Few-Shot 交通标志分类")
    print("=" * 60)
    
    api_key = os.getenv("ZAI_API_KEY")
    if not api_key:
        print("❌ 请设置 ZAI_API_KEY")
        return
    
    client = ZaiClient(api_key=api_key)
    
    print(f"\n📷 目标图片: {image_path}")
    if bbox:
        print(f"📦 裁剪区域: {bbox}")
    
    print("\n⏳ 创建对比图并调用 GLM-4.6V...")
    
    result = classify_with_visual_fewshot(client, image_path, bbox, category_hint="speed_limit")
    
    print("\n" + "-" * 40)
    print("📊 分类结果:")
    print(f"   选择: {result.get('choice', 'N/A')}")
    print(f"   标签: {result['label']}")
    print(f"   候选数: {result.get('candidates_count', 'N/A')}")
    
    if result.get("comparison_image"):
        print(f"   对比图: {result['comparison_image']}")
    
    print("=" * 60)
    
    return result


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Visual Few-Shot 交通标志分类")
    parser.add_argument("--test", type=str, help="测试图片路径")
    parser.add_argument("--bbox", type=str, help="裁剪区域 x1,y1,x2,y2")
    parser.add_argument("--category", type=str, default="speed_limit", help="类别提示")
    args = parser.parse_args()
    
    if args.test:
        bbox = None
        if args.bbox:
            bbox = [int(x) for x in args.bbox.split(",")]
        
        demo_visual_fewshot(args.test, bbox)
    else:
        # 默认测试
        demo_visual_fewshot(
            "test_images/extracted_frames/D1_frame_0006.jpg",
            bbox=[733, 270, 776, 300]  # 已知的限速标志位置
        )


if __name__ == "__main__":
    main()
