#!/usr/bin/env python3
"""
本地测试脚本 - 模拟识别功能
"""

import os
import random
from PIL import Image
import matplotlib.pyplot as plt

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
            avg_r = sum(p[0] for p in pixels) // len(pixels)
            avg_g = sum(p[1] for p in pixels) // len(pixels)
            avg_b = sum(p[2] for p in pixels) // len(pixels)

            # 简单的颜色分类
            if avg_r > 150 and avg_g < 100 and avg_b < 100:
                dominant_color = "红色系"
            elif avg_r > 150 and avg_g > 150 and avg_b < 100:
                dominant_color = "黄色系"
            elif avg_r < 100 and avg_g < 100 and avg_b < 100:
                dominant_color = "深色系"
            else:
                dominant_color = "其他颜色"
        else:
            dominant_color = "无法分析"

        return {
            'width': width,
            'height': height,
            'mode': mode,
            'dominant_color': dominant_color
        }

    except Exception as e:
        return {'error': str(e)}

def mock_traffic_sign_recognition(image_path):
    """模拟交通标志识别"""
    analysis = analyze_image_characteristics(image_path)

    if 'error' in analysis:
        return f"图片分析失败: {analysis['error']}"

    # 基于简单特征的模拟识别
    signs = [
        "停车标志 - 红色八角形，要求车辆完全停止",
        "让行标志 - 红色倒三角形，要求让行其他车辆",
        "限速标志 - 圆形，显示最大允许速度",
        "禁止通行标志 - 红色圆形加横条，表示禁止",
        "注意行人标志 - 黄色三角形，警示行人",
        "禁止转弯标志 - 红色圆形，禁止特定转向",
        "停车让行标志 - 红色八角形或方形",
        "道路施工标志 - 橙色菱形，警示施工"
    ]

    # 简单的"智能"识别逻辑
    if analysis['dominant_color'] == "红色系":
        likely_signs = [s for s in signs if "红色" in s or "禁止" in s or "停车" in s]
    elif analysis['dominant_color'] == "黄色系":
        likely_signs = [s for s in signs if "黄色" in s or "注意" in s or "警示" in s]
    else:
        likely_signs = signs

    # 随机选择一个"识别"结果
    recognized = random.choice(likely_signs)

    return f"""
🚦 模拟交通标志识别结果

📷 图片信息:
   • 尺寸: {analysis['width']} x {analysis['height']} 像素
   • 颜色模式: {analysis['mode']}
   • 主色调: {analysis['dominant_color']}

🎯 识别结果:
   {recognized}

📝 分析说明:
   这是一个基于图片特征的模拟识别。
   实际使用时会调用Gemini API进行更精准的识别。

⚙️  信心度: {random.randint(70, 95)}%
"""

def main():
    """主测试函数"""
    print("🚦 交通标志识别系统 - 本地模拟测试")
    print("=" * 50)
    print("注意：这是模拟测试，用于展示系统功能")
    print("实际识别需要有效的Gemini API连接\n")

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
    print(f"🔄 将测试前 {min(5, len(image_files))} 张图片\n")

    # 测试前几张图片
    for i, img_file in enumerate(image_files[:5], 1):
        img_path = os.path.join(img_dir, img_file)
        print(f"📍 测试图片 {i}: {img_file}")
        print("-" * 40)

        result = mock_traffic_sign_recognition(img_path)
        print(result)
        print("=" * 50)

        # 每张图片后暂停
        input("按回车键继续下一张图片...")

    print(f"\n✅ 模拟测试完成!")
    print(f"📊 总共测试了 {min(5, len(image_files))} 张图片")
    print(f"\n💡 要使用真实的Gemini API识别，请:")
    print(f"   1. 确保网络连接正常")
    print(f"   2. 检查API密钥是否有效")
    print(f"   3. 确认所在地区支持Gemini API")

if __name__ == "__main__":
    main()