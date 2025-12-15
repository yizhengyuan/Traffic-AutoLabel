#!/usr/bin/env python3
"""
交通标志识别测试脚本
"""

import os
import sys
from traffic_sign_recognition import TrafficSignRecognizer

def test_basic_recognition():
    """测试基础识别功能"""
    print("测试1: 基础交通标志识别")
    print("-" * 40)

    try:
        recognizer = TrafficSignRecognizer()

        # 检查测试图片文件夹
        test_folder = "test_images"
        if not os.path.exists(test_folder):
            print(f"请创建 '{test_folder}' 文件夹并放入测试图片")
            return

        # 查找测试图片
        image_files = [f for f in os.listdir(test_folder)
                      if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]

        if not image_files:
            print(f"'{test_folder}' 文件夹中没有找到图片文件")
            return

        print(f"找到 {len(image_files)} 张测试图片\n")

        # 测试每张图片
        for img_file in image_files[:3]:  # 最多测试3张
            img_path = os.path.join(test_folder, img_file)
            print(f"正在识别: {img_file}")

            result = recognizer.basic_recognition(img_path)
            print(f"识别结果:\n{result}\n")
            print("=" * 50 + "\n")

    except Exception as e:
        print(f"测试失败: {e}")

def test_precise_recognition():
    """测试精准识别功能"""
    print("测试2: 基于样例的精准识别")
    print("-" * 40)

    try:
        recognizer = TrafficSignRecognizer()

        # 检查样例文件夹
        examples_folder = "examples"
        if not os.path.exists(examples_folder):
            print(f"请创建 '{examples_folder}' 文件夹并放入样例图片")
            return

        # 查找样例图片
        example_files = [f for f in os.listdir(examples_folder)
                        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]

        if len(example_files) < 2:
            print(f"请在 '{examples_folder}' 文件夹中放入至少2张样例图片")
            return

        print(f"找到 {len(example_files)} 张样例图片")

        # 添加样例（这里假设文件名包含标志名称）
        for img_file in example_files[:5]:  # 最多添加5个样例
            img_path = os.path.join(examples_folder, img_file)
            # 从文件名提取标志名称（去掉扩展名）
            sign_name = os.path.splitext(img_file)[0]
            recognizer.add_example(img_path, sign_name)

        print(f"\n成功添加 {len(recognizer.examples)} 个样例\n")

        # 测试精准识别
        test_folder = "test_images"
        if not os.path.exists(test_folder):
            print(f"请创建 '{test_folder}' 文件夹并放入测试图片")
            return

        image_files = [f for f in os.listdir(test_folder)
                      if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]

        if not image_files:
            print(f"'{test_folder}' 文件夹中没有找到图片文件")
            return

        # 测试第一张图片的精准识别
        test_img = os.path.join(test_folder, image_files[0])
        print(f"精准识别测试: {image_files[0]}")

        result = recognizer.precise_recognition_with_examples(test_img)
        print(f"精准识别结果:\n{result}\n")
        print("=" * 50 + "\n")

    except Exception as e:
        print(f"精准识别测试失败: {e}")

def interactive_test():
    """交互式测试"""
    print("交互式测试模式")
    print("-" * 30)

    try:
        recognizer = TrafficSignRecognizer()

        while True:
            print("\n请选择操作:")
            print("1. 添加样例")
            print("2. 基础识别")
            print("3. 精准识别")
            print("4. 查看样例数量")
            print("5. 退出")

            choice = input("\n请输入选择 (1-5): ").strip()

            if choice == '1':
                img_path = input("请输入图片路径: ").strip()
                sign_name = input("请输入标志名称: ").strip()
                recognizer.add_example(img_path, sign_name)

            elif choice == '2':
                img_path = input("请输入测试图片路径: ").strip()
                result = recognizer.basic_recognition(img_path)
                print(f"\n识别结果:\n{result}")

            elif choice == '3':
                img_path = input("请输入测试图片路径: ").strip()
                result = recognizer.precise_recognition_with_examples(img_path)
                print(f"\n精准识别结果:\n{result}")

            elif choice == '4':
                print(f"当前样例数量: {len(recognizer.examples)}")
                for i, example in enumerate(recognizer.examples, 1):
                    print(f"  {i}. {example['sign_name']} - {example['image_path']}")

            elif choice == '5':
                print("退出测试")
                break

            else:
                print("无效选择，请重新输入")

    except Exception as e:
        print(f"交互式测试失败: {e}")

def main():
    """主测试函数"""
    print("交通标志识别测试程序")
    print("=" * 40)

    # 检查API密钥
    if not os.path.exists('.env'):
        print("警告: 未找到 .env 文件")
        print("请复制 .env.example 为 .env 并设置您的 GEMINI_API_KEY")
        print("或者确保已设置环境变量 GEMINI_API_KEY")
        return

    print("\n请选择测试模式:")
    print("1. 基础识别测试")
    print("2. 精准识别测试")
    print("3. 交互式测试")
    print("4. 全部测试")

    choice = input("\n请输入选择 (1-4): ").strip()

    if choice == '1':
        test_basic_recognition()
    elif choice == '2':
        test_precise_recognition()
    elif choice == '3':
        interactive_test()
    elif choice == '4':
        test_basic_recognition()
        print("\n" + "="*60 + "\n")
        test_precise_recognition()
    else:
        print("无效选择")

if __name__ == "__main__":
    main()