#!/usr/bin/env python3
"""
简单的功能测试脚本
"""

import os
from traffic_sign_recognition import TrafficSignRecognizer

def test_api_connection():
    """测试API连接"""
    print("1. 测试API连接...")
    try:
        recognizer = TrafficSignRecognizer()
        print("   ✓ API连接成功")
        return True, recognizer
    except Exception as e:
        print(f"   ✗ API连接失败: {e}")
        return False, None

def test_without_images(recognizer):
    """测试没有图片时的错误处理"""
    print("\n2. 测试错误处理...")

    # 测试不存在的文件
    result = recognizer.basic_recognition("nonexistent.jpg")
    if "识别失败" in result:
        print("   ✓ 正确处理不存在的文件")
    else:
        print("   ✗ 错误处理有问题")

    # 测试精准识别（没有样例）
    result = recognizer.precise_recognition_with_examples("test.jpg")
    if "请先添加样例" in result:
        print("   ✓ 正确处理无样例情况")
    else:
        print("   ✗ 无样例处理有问题")

def test_structure():
    """测试项目结构"""
    print("\n3. 测试项目结构...")

    # 检查必要文件
    required_files = [
        'traffic_sign_recognition.py',
        'requirements.txt',
        '.env'
    ]

    for file in required_files:
        if os.path.exists(file):
            print(f"   ✓ {file} 存在")
        else:
            print(f"   ✗ {file} 不存在")

    # 检查文件夹
    folders = ['examples', 'test_images']
    for folder in folders:
        if os.path.exists(folder):
            print(f"   ✓ {folder}/ 文件夹存在")
        else:
            print(f"   ✗ {folder}/ 文件夹不存在")

def main():
    """主测试函数"""
    print("交通标志识别系统 - 简单测试")
    print("=" * 50)

    # 测试API连接
    success, recognizer = test_api_connection()

    if success:
        # 测试错误处理
        test_without_images(recognizer)

        # 测试项目结构
        test_structure()

        print("\n" + "=" * 50)
        print("基础功能测试完成！")
        print("\n下一步：")
        print("1. 准备一些交通标志图片")
        print("2. 将图片放入 test_images/ 文件夹")
        print("3. 运行 python3 traffic_sign_recognition.py 进行实际识别测试")
    else:
        print("\n请检查API密钥配置")

if __name__ == "__main__":
    main()