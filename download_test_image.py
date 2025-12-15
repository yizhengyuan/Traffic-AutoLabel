#!/usr/bin/env python3
"""
下载测试图片脚本
"""

import urllib.request
import os
from traffic_sign_recognition import TrafficSignRecognizer

def download_test_images():
    """下载一些测试用的交通标志图片"""
    print("正在下载测试图片...")

    # 一些常见的交通标志图片URL（这些是示例URL，可能需要替换）
    test_urls = [
        ("https://upload.wikimedia.org/wikipedia/commons/thumb/e/e2/Stop_sign.JPG/240px-Stop_sign.JPG", "test_stop_sign.jpg"),
        # 可以添加更多测试图片URL
    ]

    downloaded_files = []

    for url, filename in test_urls:
        try:
            print(f"下载 {filename}...")
            urllib.request.urlretrieve(url, f"test_images/{filename}")
            downloaded_files.append(filename)
            print(f"   ✓ {filename} 下载成功")
        except Exception as e:
            print(f"   ✗ {filename} 下载失败: {e}")

    return downloaded_files

def create_sample_images():
    """创建一些简单的示例图片提示"""
    sample_info = """
    示例图片建议：

    1. 停车标志 (Stop Sign)
       - 红色八角形，白色背景，红色"STOP"文字

    2. 让行标志 (Yield Sign)
       - 红色倒三角形，白色背景

    3. 限速标志
       - 红色圆形，白色背景，黑色数字

    4. 禁止通行标志
       - 红色圆形，白色背景，黑色横条

    请将这些图片保存到：
    - test_images/ 文件夹：用于测试识别
    - examples/ 文件夹：作为精准识别的样例
    """

    print(sample_info)
    return sample_info

def test_with_local_image():
    """如果存在本地图片，进行测试"""
    print("\n检查是否有现有的测试图片...")

    test_images = [f for f in os.listdir('test_images')
                  if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp'))]

    if test_images:
        print(f"找到 {len(test_images)} 张测试图片: {test_images}")

        try:
            recognizer = TrafficSignRecognizer()

            # 测试第一张图片
            test_img = os.path.join('test_images', test_images[0])
            print(f"\n正在测试识别: {test_images[0]}")

            result = recognizer.basic_recognition(test_img)
            print(f"识别结果:")
            print("-" * 40)
            print(result)
            print("-" * 40)

            return True

        except Exception as e:
            print(f"识别测试失败: {e}")
            return False
    else:
        print("test_images/ 文件夹中没有找到图片")
        return False

def main():
    """主函数"""
    print("交通标志识别系统 - 图片下载和测试")
    print("=" * 50)

    # 检查文件夹
    if not os.path.exists('test_images'):
        os.makedirs('test_images')
        print("创建 test_images/ 文件夹")

    # 尝试下载测试图片
    downloaded = download_test_images()

    # 显示图片建议
    create_sample_images()

    # 如果有图片，进行测试
    if downloaded or test_with_local_image():
        print("\n测试完成！系统已准备就绪。")
    else:
        print("\n请手动添加交通标志图片到 test_images/ 文件夹中进行测试。")

    print("\n使用方法:")
    print("1. 添加图片到 test_images/ 文件夹")
    print("2. 运行: python3 -c \"from traffic_sign_recognition import TrafficSignRecognizer; r = TrafficSignRecognizer(); print(r.basic_recognition('test_images/your_image.jpg'))\"")

if __name__ == "__main__":
    main()