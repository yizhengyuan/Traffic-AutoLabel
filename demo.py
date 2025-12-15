#!/usr/bin/env python3
"""
交通标志识别系统演示脚本

这个脚本演示了如何使用交通标志识别系统的各种功能，
包括基础识别和基于样例的精准识别。
"""

import os
import sys
from traffic_sign_recognition import TrafficSignRecognizer

def demo_without_api_key():
    """演示不使用API密钥的功能"""
    print("交通标志识别系统演示")
    print("=" * 50)
    print("\n注意：此演示不需要API密钥，仅展示系统结构和功能。")
    print("要使用实际的识别功能，请配置Gemini API密钥。")
    print()

    # 检查文件结构
    print("1. 检查项目文件结构：")
    files_to_check = [
        'traffic_sign_recognition.py',
        'test_recognition.py',
        'requirements.txt',
        '.env.example'
    ]

    for file in files_to_check:
        status = "✓" if os.path.exists(file) else "✗"
        print(f"   {status} {file}")

    # 检查文件夹
    print("\n2. 创建必要的文件夹：")
    folders = ['examples', 'test_images']

    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"   ✓ 创建文件夹: {folder}")
        else:
            print(f"   ✓ 文件夹已存在: {folder}")

    # 展示代码结构
    print("\n3. 主要功能模块：")
    print("   ✓ TrafficSignRecognizer 类：核心识别器")
    print("   ✓ 基础识别功能：basic_recognition()")
    print("   ✓ 精准识别功能：precise_recognition_with_examples()")
    print("   ✓ 批量处理功能：batch_recognition()")
    print("   ✓ 样例管理功能：add_example()")

    # 展示使用示例
    print("\n4. 使用示例代码：")
    print("""
# 基础使用
from traffic_sign_recognition import TrafficSignRecognizer

recognizer = TrafficSignRecognizer()  # 需要配置API密钥

# 基础识别
result = recognizer.basic_recognition("traffic_sign.jpg")
print(result)

# 添加样例
recognizer.add_example("stop_sign.jpg", "停车标志")
recognizer.add_example("yield_sign.jpg", "让行标志")

# 精准识别
precise_result = recognizer.precise_recognition_with_examples("test_image.jpg")
print(precise_result)
""")

def demo_with_mock_api_key():
    """使用模拟API密钥演示"""
    print("\n" + "="*50)
    print("模拟API密钥演示（仅展示代码逻辑，不实际调用API）")
    print("="*50)

    # 这里我们不实际创建识别器，只展示流程
    print("\n模拟流程：")
    print("1. 初始化识别器")
    print("   recognizer = TrafficSignRecognizer(api_key='demo_key')")
    print()
    print("2. 添加样例数据")
    print("   recognizer.add_example('examples/stop.jpg', '停车标志')")
    print("   recognizer.add_example('examples/yield.jpg', '让行标志')")
    print()
    print("3. 执行识别")
    print("   result = recognizer.basic_recognition('test/image.jpg')")
    print("   # 返回详细的识别结果")
    print()
    print("4. 精准识别")
    print("   precise_result = recognizer.precise_recognition_with_examples('test/image.jpg')")
    print("   # 基于样例进行更精准的识别")

def show_api_key_setup():
    """展示API密钥设置方法"""
    print("\n" + "="*50)
    print("API密钥设置指南")
    print("="*50)

    print("\n方法1: 使用环境变量文件")
    print("1. 复制模板文件:")
    print("   cp .env.example .env")
    print("\n2. 编辑 .env 文件:")
    print("   GEMINI_API_KEY=your_actual_api_key_here")
    print("\n3. 保存文件后即可使用")

    print("\n方法2: 直接设置环境变量")
    print("export GEMINI_API_KEY=your_actual_api_key_here")

    print("\n方法3: 在代码中直接传入")
    print("recognizer = TrafficSignRecognizer(api_key='your_key_here')")

    print("\n获取API密钥:")
    print("1. 访问 https://aistudio.google.com/app/apikey")
    print("2. 登录您的Google账户")
    print("3. 创建新的API密钥")
    print("4. 复制密钥并按照上述方法设置")

def main():
    """主演示函数"""
    print("欢迎使用交通标志识别系统！")
    print("这个系统基于Google Gemini API，支持交通标志的智能识别。")

    # 演示基础功能
    demo_without_api_key()

    # 展示API密钥设置
    show_api_key_setup()

    # 模拟使用流程
    demo_with_mock_api_key()

    print("\n" + "="*50)
    print("演示完成！")
    print("下一步：")
    print("1. 获取Gemini API密钥")
    print("2. 配置环境变量")
    print("3. 准备交通标志图片")
    print("4. 运行 python3 test_recognition.py 开始测试")
    print("="*50)

if __name__ == "__main__":
    main()