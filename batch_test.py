#!/usr/bin/env python3
"""
批量测试脚本 - 无交互版本
"""

import os
import random
from PIL import Image
import json

def analyze_image_characteristics(image_path):
    """分析图片的基本特征"""
    try:
        img = Image.open(image_path)

        # 获取基本信息
        width, height = img.size
        mode = img.mode

        # 简单的颜色分析
        if mode == 'RGB':
            pixels = list(img.getdata())
            # 采样以提高性能
            sample_size = min(1000, len(pixels))
            sampled_pixels = pixels[::len(pixels)//sample_size]

            avg_r = sum(p[0] for p in sampled_pixels) // len(sampled_pixels)
            avg_g = sum(p[1] for p in sampled_pixels) // len(sampled_pixels)
            avg_b = sum(p[2] for p in sampled_pixels) // len(sampled_pixels)

            # 简单的颜色分类
            if avg_r > 150 and avg_g < 100 and avg_b < 100:
                dominant_color = "红色系"
            elif avg_r > 150 and avg_g > 150 and avg_b < 100:
                dominant_color = "黄色系"
            elif avg_r < 100 and avg_g < 100 and avg_b < 100:
                dominant_color = "深色系"
            elif avg_r > 200 and avg_g > 200 and avg_b > 200:
                dominant_color = "浅色系"
            else:
                dominant_color = "混合色"
        else:
            dominant_color = "无法分析"

        return {
            'width': width,
            'height': height,
            'mode': mode,
            'dominant_color': dominant_color,
            'avg_rgb': (avg_r, avg_g, avg_b) if mode == 'RGB' else None
        }

    except Exception as e:
        return {'error': str(e)}

def mock_traffic_sign_recognition(image_path, image_name):
    """模拟交通标志识别"""
    analysis = analyze_image_characteristics(image_path)

    if 'error' in analysis:
        return {
            'image_name': image_name,
            'status': 'error',
            'error': analysis['error']
        }

    # 扩展的交通标志列表
    signs = [
        {"name": "停车标志", "type": "禁令标志", "color": "红色", "shape": "八角形", "meaning": "要求车辆完全停止"},
        {"name": "让行标志", "type": "禁令标志", "color": "红色", "shape": "倒三角形", "meaning": "要求让行其他车辆"},
        {"name": "限速标志", "type": "禁令标志", "color": "红色", "shape": "圆形", "meaning": "显示最大允许速度"},
        {"name": "禁止通行标志", "type": "禁令标志", "color": "红色", "shape": "圆形", "meaning": "表示禁止通行"},
        {"name": "禁止转弯标志", "type": "禁令标志", "color": "红色", "shape": "圆形", "meaning": "禁止特定转向"},
        {"name": "禁止超车标志", "type": "禁令标志", "color": "红色", "shape": "圆形", "meaning": "禁止超车"},
        {"name": "禁止停车标志", "type": "禁令标志", "color": "红色", "shape": "圆形", "meaning": "禁止停车"},
        {"name": "注意行人标志", "type": "警告标志", "color": "黄色", "shape": "三角形", "meaning": "警示有行人"},
        {"name": "注意儿童标志", "type": "警告标志", "color": "黄色", "shape": "三角形", "meaning": "警示有儿童"},
        {"name": "道路施工标志", "type": "警告标志", "color": "橙色", "shape": "菱形", "meaning": "警示道路施工"},
        {"name": "注意信号灯标志", "type": "警告标志", "color": "黄色", "shape": "三角形", "meaning": "警示前方有信号灯"},
        {"name": "直行标志", "type": "指示标志", "color": "蓝色", "shape": "圆形", "meaning": "指示直行"},
        {"name": "左转标志", "type": "指示标志", "color": "蓝色", "shape": "圆形", "meaning": "指示左转"},
        {"name": "右转标志", "type": "指示标志", "color": "蓝色", "shape": "圆形", "meaning": "指示右转"},
        {"name": "停车场标志", "type": "指示标志", "color": "蓝色", "shape": "方形", "meaning": "指示停车场位置"}
    ]

    # 基于"智能"分析的识别逻辑
    dominant_color = analysis['dominant_color']

    if dominant_color == "红色系":
        likely_signs = [s for s in signs if s["color"] == "红色"]
    elif dominant_color == "黄色系":
        likely_signs = [s for s in signs if s["color"] == "黄色"]
    elif dominant_color == "浅色系":
        likely_signs = [s for s in signs if s["color"] == "蓝色"]
    else:
        likely_signs = signs

    # 智能选择
    recognized = random.choice(likely_signs)

    return {
        'image_name': image_name,
        'status': 'success',
        'image_analysis': {
            'dimensions': f"{analysis['width']} x {analysis['height']} 像素",
            'color_mode': analysis['mode'],
            'dominant_color': dominant_color,
            'avg_rgb': analysis['avg_rgb']
        },
        'recognition_result': {
            'sign_name': recognized['name'],
            'sign_type': recognized['type'],
            'sign_color': recognized['color'],
            'sign_shape': recognized['shape'],
            'sign_meaning': recognized['meaning']
        },
        'confidence': random.randint(75, 98),
        'note': '这是基于图片特征的模拟识别结果'
    }

def main():
    """主测试函数"""
    print("🚦 交通标志识别系统 - 批量模拟测试")
    print("=" * 60)

    # 检查图片文件夹
    img_dir = "test_images/extracted_frames"
    if not os.path.exists(img_dir):
        print(f"❌ 图片文件夹不存在: {img_dir}")
        return

    # 获取图片列表
    image_files = [f for f in os.listdir(img_dir)
                  if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]

    if not image_files:
        print(f"❌ 在 {img_dir} 中没有找到图片文件")
        return

    print(f"📸 找到 {len(image_files)} 张图片")
    print(f"🔄 将测试前 {min(10, len(image_files))} 张图片\n")

    # 测试前10张图片
    results = []
    for i, img_file in enumerate(image_files[:10], 1):
        img_path = os.path.join(img_dir, img_file)
        print(f"📍 测试图片 {i}/10: {img_file}")

        result = mock_traffic_sign_recognition(img_path, img_file)
        results.append(result)

        if result['status'] == 'success':
            recog = result['recognition_result']
            print(f"   ✅ {recog['sign_name']} ({recog['sign_type']})")
            print(f"   📊 信心度: {result['confidence']}%")
            print(f"   🎨 主色调: {result['image_analysis']['dominant_color']}")
        else:
            print(f"   ❌ 错误: {result['error']}")

        print()

    # 保存结果
    output_file = "batch_test_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"📁 结果已保存到: {output_file}")

    # 统计分析
    successful_results = [r for r in results if r['status'] == 'success']
    if successful_results:
        sign_types = {}
        colors = {}
        confidences = []

        for result in successful_results:
            sign_type = result['recognition_result']['sign_type']
            color = result['image_analysis']['dominant_color']
            confidence = result['confidence']

            sign_types[sign_type] = sign_types.get(sign_type, 0) + 1
            colors[color] = colors.get(color, 0) + 1
            confidences.append(confidence)

        print(f"\n📊 统计分析 (基于 {len(successful_results)} 张成功识别的图片):")
        print(f"   🚦 标志类型分布:")
        for sign_type, count in sorted(sign_types.items(), key=lambda x: x[1], reverse=True):
            print(f"      • {sign_type}: {count} 张")

        print(f"   🎨 颜色分布:")
        for color, count in sorted(colors.items(), key=lambda x: x[1], reverse=True):
            print(f"      • {color}: {count} 张")

        print(f"   📈 平均信心度: {sum(confidences)/len(confidences):.1f}%")

    print(f"\n✅ 批量测试完成!")
    print(f"🎯 成功处理 {len(successful_results)}/{len(results)} 张图片")

if __name__ == "__main__":
    main()