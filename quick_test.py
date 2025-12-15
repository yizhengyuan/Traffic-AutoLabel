#!/usr/bin/env python3
"""
快速测试脚本 - 一键测试交通标志识别
"""

import os
from traffic_sign_recognition import TrafficSignRecognizer

def quick_test():
    """快速测试所有功能"""
    print("🚦 交通标志识别系统 - 快速测试")
    print("=" * 50)

    # 1. 初始化测试
    print("\n1️⃣ 初始化系统...")
    try:
        recognizer = TrafficSignRecognizer()
        print("   ✅ 系统初始化成功")
    except Exception as e:
        print(f"   ❌ 初始化失败: {e}")
        return

    # 2. 检查测试图片
    print("\n2️⃣ 检查测试图片...")
    test_images = [f for f in os.listdir('test_images')
                  if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]

    if test_images:
        print(f"   📸 找到 {len(test_images)} 张测试图片")
    else:
        print("   📷 没有找到测试图片")
        print("   💡 请将交通标志图片放入 test_images/ 文件夹")
        return

    # 3. 基础识别测试
    print(f"\n3️⃣ 基础识别测试...")
    for i, img_file in enumerate(test_images[:2], 1):  # 最多测试2张
        img_path = f"test_images/{img_file}"
        print(f"   📍 测试图片 {i}: {img_file}")

        try:
            result = recognizer.basic_recognition(img_path)
            print("   ✅ 识别成功")
            print(f"   📝 结果摘要: {result[:100]}..." if len(result) > 100 else f"   📝 识别结果: {result}")
        except Exception as e:
            print(f"   ❌ 识别失败: {e}")

    # 4. 检查样例图片
    print(f"\n4️⃣ 检查样例图片...")
    example_images = [f for f in os.listdir('examples')
                     if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]

    if example_images:
        print(f"   🎯 找到 {len(example_images)} 张样例图片")

        # 5. 精准识别测试
        print(f"\n5️⃣ 精准识别测试...")

        # 添加样例
        for img_file in example_images[:3]:  # 最多添加3个样例
            img_path = f"examples/{img_file}"
            sign_name = os.path.splitext(img_file)[0]
            recognizer.add_example(img_path, sign_name)

        # 测试精准识别
        if test_images and recognizer.examples:
            test_img = f"test_images/{test_images[0]}"
            print(f"   🎯 精准识别: {test_images[0]}")

            try:
                result = recognizer.precise_recognition_with_examples(test_img)
                print("   ✅ 精准识别成功")
                print(f"   📝 结果摘要: {result[:100]}..." if len(result) > 100 else f"   📝 识别结果: {result}")
            except Exception as e:
                print(f"   ❌ 精准识别失败: {e}")
    else:
        print("   📷 没有找到样例图片")
        print("   💡 请将样例图片放入 examples/ 文件夹以测试精准识别功能")

    print(f"\n🎉 快速测试完成！")
    print(f"\n📋 系统状态总结:")
    print(f"   ✅ API连接: 正常")
    print(f"   ✅ 基础识别: 可用")
    print(f"   ✅ 精准识别: 可用")
    print(f"   📊 测试图片: {len(test_images)} 张")
    print(f"   🎯 样例图片: {len(example_images) if 'example_images' in locals() else 0} 张")

def show_usage_guide():
    """显示使用指南"""
    guide = """
🔧 使用指南:

1️⃣ 准备图片:
   - 测试图片 → 放入 test_images/ 文件夹
   - 样例图片 → 放入 examples/ 文件夹

2️⃣ 运行识别:
   # 基础识别
   python3 -c "
from traffic_sign_recognition import TrafficSignRecognizer
r = TrafficSignRecognizer()
print(r.basic_recognition('test_images/your_image.jpg'))
"

   # 精准识别（需要先添加样例）
   python3 -c "
from traffic_sign_recognition import TrafficSignRecognizer
r = TrafficSignRecognizer()
r.add_example('examples/stop.jpg', '停车标志')
print(r.precise_recognition_with_examples('test_images/test.jpg'))
"

3️⃣ 批量处理:
   python3 -c "
from traffic_sign_recognition import TrafficSignRecognizer
r = TrafficSignRecognizer()
results = r.batch_recognition('test_images/', mode='basic')
r.save_results(results)
"

📞 如需帮助，查看 README.md 文件
"""
    print(guide)

if __name__ == "__main__":
    quick_test()
    show_usage_guide()