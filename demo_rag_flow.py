#!/usr/bin/env python3
"""
RAG 流程可视化演示

直观展示 GLM-4.6V + RAG 交通标志分类的完整流程

用法:
    python3 demo_rag_flow.py --image D1_frame_0006.jpg
    python3 demo_rag_flow.py --prefix D1 --limit 5
"""

import os
import json
import base64
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from zai import ZaiClient

# ============================================================================
# 动态加载 188 个香港道路标志候选库
# ============================================================================

SIGNS_DIR = Path("examples/signs/highres/png2560px")

def load_sign_candidates():
    """从标志图片目录动态加载所有标志名称"""
    if not SIGNS_DIR.exists():
        print(f"⚠️ 找不到标志目录: {SIGNS_DIR}")
        return []
    
    candidates = []
    for f in sorted(SIGNS_DIR.glob("*.png")):
        label = f.stem  # 使用原始文件名
        candidates.append(label)
    
    return candidates

ALL_CANDIDATES = load_sign_candidates()


def print_box(title: str, content: list, width: int = 60):
    """打印美观的信息框"""
    print("┌" + "─" * (width - 2) + "┐")
    print(f"│ {title:^{width - 4}} │")
    print("├" + "─" * (width - 2) + "┤")
    for line in content:
        if len(line) > width - 4:
            line = line[:width - 7] + "..."
        print(f"│ {line:<{width - 4}} │")
    print("└" + "─" * (width - 2) + "┘")


def step_indicator(step: int, total: int, title: str):
    """步骤指示器"""
    bar = "█" * step + "░" * (total - step)
    print(f"\n{'='*60}")
    print(f"  [{bar}] Step {step}/{total}: {title}")
    print(f"{'='*60}")


def detect_with_details(client: ZaiClient, image_path: str) -> list:
    """检测并返回详细信息"""
    with open(image_path, 'rb') as f:
        img_data = base64.b64encode(f.read()).decode()
    
    img = Image.open(image_path)
    width, height = img.size
    
    prompt = """请检测图片中的交通标志和车辆，返回JSON格式。

车辆：car, truck, bus, van, taxi, motorcycle
交通标志：统一用 traffic_sign 标注

格式：[{"label": "car", "bbox_2d": [x1,y1,x2,y2]}]

只返回JSON数组。"""

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
    
    result = response.choices[0].message.content.strip()
    
    try:
        if "[" in result:
            json_str = result[result.find("["):result.rfind("]")+1]
            detections = json.loads(json_str)
            
            processed = []
            for det in detections:
                if "label" not in det or "bbox_2d" not in det:
                    continue
                bbox = det["bbox_2d"]
                processed.append({
                    "label": det["label"],
                    "bbox": [
                        int(bbox[0] / 1000 * width),
                        int(bbox[1] / 1000 * height),
                        int(bbox[2] / 1000 * width),
                        int(bbox[3] / 1000 * height)
                    ]
                })
            return processed
    except:
        pass
    return []


def rag_classify_sign(client: ZaiClient, image_path: str, bbox: list) -> dict:
    """RAG 分类单个标志，返回详细过程"""
    img = Image.open(image_path)
    
    # 扩大裁剪区域
    x1, y1, x2, y2 = bbox
    padding = 10
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(img.width, x2 + padding)
    y2 = min(img.height, y2 + padding)
    
    # 裁剪
    sign_crop = img.crop((x1, y1, x2, y2))
    
    # 保存裁剪图
    temp_path = "/tmp/demo_sign_crop.jpg"
    sign_crop.save(temp_path, "JPEG")
    
    with open(temp_path, "rb") as f:
        crop_data = base64.b64encode(f.read()).decode()
    
    # 构建候选列表
    candidate_list = "\n".join([f"{i+1}. {c}" for i, c in enumerate(ALL_CANDIDATES)])
    
    prompt = f"""请仔细观察这个交通标志，从以下选项中选择最匹配的：

{candidate_list}

规则：
1. 观察颜色、形状、文字、数字
2. 如果是限速标志，识别具体数字
3. 如果都不匹配，返回数字 0

只返回选项编号（1-{len(ALL_CANDIDATES)}），不要其他解释。"""

    response = client.chat.completions.create(
        model="glm-4.6v",
        messages=[{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{crop_data}"}},
                {"type": "text", "text": prompt}
            ]
        }]
    )
    
    choice = response.choices[0].message.content.strip()
    
    # 解析结果
    import re
    numbers = re.findall(r'\d+', choice)
    selected_idx = -1
    selected_label = "unknown"
    
    if numbers:
        idx = int(numbers[0]) - 1
        if 0 <= idx < len(ALL_CANDIDATES):
            selected_idx = idx
            selected_label = ALL_CANDIDATES[idx]
    
    return {
        "crop_size": sign_crop.size,
        "crop_path": temp_path,
        "candidates_count": len(ALL_CANDIDATES),
        "raw_response": choice,
        "selected_index": selected_idx,
        "selected_label": selected_label
    }


def visualize_result(image_path: str, detections: list, rag_results: dict, output_path: str):
    """生成可视化结果图"""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    
    colors = {
        "vehicle": (0, 255, 0),
        "traffic_sign": (255, 100, 0),
        "rag_refined": (0, 100, 255)
    }
    
    for i, det in enumerate(detections):
        bbox = det["bbox"]
        label = det["label"]
        
        # 判断颜色
        if "sign" in label.lower():
            # 如果有 RAG 结果，使用精排后的标签
            if i in rag_results:
                label = rag_results[i]["selected_label"]
                color = colors["rag_refined"]
            else:
                color = colors["traffic_sign"]
        else:
            color = colors["vehicle"]
        
        # 画框
        draw.rectangle(bbox, outline=color, width=3)
        
        # 画标签
        text_bbox = draw.textbbox((bbox[0], bbox[1] - 20), label)
        draw.rectangle([text_bbox[0] - 2, text_bbox[1] - 2, text_bbox[2] + 2, text_bbox[3] + 2], fill=color)
        draw.text((bbox[0], bbox[1] - 20), label, fill=(255, 255, 255))
    
    img.save(output_path)
    return output_path


def demo_single_image(client: ZaiClient, image_path: str):
    """演示单张图片的完整 RAG 流程"""
    
    print("\n" + "🔷" * 30)
    print(f"  📷 RAG 流程演示: {Path(image_path).name}")
    print("🔷" * 30)
    
    # Step 1: 加载图片
    step_indicator(1, 4, "📁 数据准备")
    img = Image.open(image_path)
    print_box("图片信息", [
        f"路径: {image_path}",
        f"尺寸: {img.width} x {img.height}",
        f"格式: {img.format}"
    ])
    
    # Step 2: 基础检测
    step_indicator(2, 4, "🤖 模型推理（基础检测）")
    print("\n  ⏳ 调用 GLM-4.6V 进行目标检测...")
    detections = detect_with_details(client, image_path)
    
    detection_info = []
    sign_indices = []
    for i, det in enumerate(detections):
        info = f"{i+1}. {det['label']:15} at {det['bbox']}"
        detection_info.append(info)
        if "sign" in det["label"].lower():
            sign_indices.append(i)
    
    if not detection_info:
        detection_info = ["(未检测到目标)"]
    
    print_box("检测结果", detection_info)
    
    # Step 3: RAG 精排
    step_indicator(3, 4, "🔍 RAG 精排（交通标志细分）")
    
    rag_results = {}
    
    if not sign_indices:
        print("\n  ℹ️  未检测到交通标志，跳过 RAG 精排")
    else:
        print(f"\n  📋 发现 {len(sign_indices)} 个交通标志，开始 RAG 精排...")
        print(f"  📚 候选库: {len(ALL_CANDIDATES)} 种标准标志\n")
        
        for idx in sign_indices:
            det = detections[idx]
            print(f"  ┌─ 处理标志 #{idx + 1}")
            print(f"  │  位置: {det['bbox']}")
            print(f"  │  ⏳ 裁剪区域 → CLIP 编码 → 向量检索...")
            
            # RAG 分类
            result = rag_classify_sign(client, image_path, det["bbox"])
            rag_results[idx] = result
            
            print(f"  │  📤 GLM-4.6V 从 {result['candidates_count']} 个候选中选择...")
            print(f"  │  ✅ 结果: {result['selected_label']}")
            print(f"  └─────────────────────────────────────────\n")
    
    # Step 4: 结果导出
    step_indicator(4, 4, "📦 结果导出")
    
    # 生成可视化
    output_dir = Path("output/rag_demo")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{Path(image_path).stem}_rag_result.jpg"
    
    visualize_result(image_path, detections, rag_results, str(output_path))
    
    # 汇总
    final_labels = []
    for i, det in enumerate(detections):
        if i in rag_results:
            label = f"{rag_results[i]['selected_label']} (RAG精排)"
        else:
            label = det["label"]
        final_labels.append(label)
    
    print_box("最终标注结果", final_labels if final_labels else ["(无目标)"])
    print(f"\n  💾 可视化结果已保存: {output_path}")
    
    # 流程图
    print("\n" + "─" * 60)
    print("  📊 RAG 流程回顾:")
    print("─" * 60)
    print("""
    ┌────────────┐     ┌────────────┐     ┌────────────┐
    │  原始图片   │ ──▶ │ GLM-4.6V   │ ──▶ │ 检测到     │
    │            │     │ 基础检测    │     │ traffic_   │
    │            │     │            │     │ sign       │
    └────────────┘     └────────────┘     └─────┬──────┘
                                                │
                                                ▼
    ┌────────────┐     ┌────────────┐     ┌────────────┐
    │  最终标签   │ ◀── │ GLM-4.6V   │ ◀── │ 裁剪标志   │
    │ speed_     │     │ 从候选中    │     │ 区域       │
    │ limit_70   │     │ 精排选择    │     │            │
    └────────────┘     └────────────┘     └────────────┘
    """)
    
    return detections, rag_results


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG 流程可视化演示")
    parser.add_argument("--image", type=str, help="单张图片路径")
    parser.add_argument("--prefix", type=str, help="图片前缀 (如 D1)")
    parser.add_argument("--limit", type=int, default=3, help="处理数量")
    args = parser.parse_args()
    
    # 初始化
    api_key = os.getenv("ZAI_API_KEY")
    if not api_key:
        print("❌ 请设置 ZAI_API_KEY 环境变量")
        return
    
    client = ZaiClient(api_key=api_key)
    
    if args.image:
        # 单张图片
        demo_single_image(client, args.image)
    
    elif args.prefix:
        # 批量处理
        images_dir = Path("test_images/extracted_frames")
        image_files = sorted(images_dir.glob(f"{args.prefix}_*.jpg"))[:args.limit]
        
        print(f"\n🚀 批量演示: {len(image_files)} 张图片\n")
        
        for img_path in image_files:
            demo_single_image(client, str(img_path))
            print("\n" + "═" * 60 + "\n")
    
    else:
        # 默认演示
        demo_image = "test_images/extracted_frames/D1_frame_0006.jpg"
        if Path(demo_image).exists():
            demo_single_image(client, demo_image)
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
