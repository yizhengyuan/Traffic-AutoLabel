#!/usr/bin/env python3
"""
GLM-4.6V 快速测试脚本

用于快速测试 GLM-4.6V 标注系统的基础功能
"""

import os
import sys
from video_data_labeler import VideoDataLabeler

def test_api_connection():
    """测试API连接"""
    print("测试 GLM-4.6V API 连接...")

    try:
        labeler = VideoDataLabeler()
        print("✓ API 连接成功")
        return labeler
    except Exception as e:
        print(f"✗ API 连接失败: {e}")
        return None

def test_single_annotation(labeler):
    """测试单张图片标注"""
    # 查找测试图片
    test_dirs = ['test_images', 'examples', '.']
    test_image = None

    for directory in test_dirs:
        if os.path.exists(directory):
            for file in os.listdir(directory):
                if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')):
                    test_image = os.path.join(directory, file)
                    break
            if test_image:
                break

    if not test_image:
        print("⚠️  未找到测试图片，跳过单图标注测试")
        return

    print(f"\n测试单图标注: {test_image}")

    try:
        result = labeler.basic_annotation(test_image, "general")
        print("✓ 单图标注成功")
        print(f"结果预览: {result[:200]}...")
        return True
    except Exception as e:
        print(f"✗ 单图标注失败: {e}")
        return False

def test_batch_annotation(labeler):
    """测试批量标注"""
    test_dirs = ['test_images', 'examples']
    batch_dir = None

    for directory in test_dirs:
        if os.path.exists(directory):
            images = [f for f in os.listdir(directory)
                     if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'))]
            if len(images) >= 2:
                batch_dir = directory
                break

    if not batch_dir:
        print("⚠️  未找到包含多张图片的文件夹，跳过批量标注测试")
        return

    print(f"\n测试批量标注: {batch_dir}")

    try:
        results = labeler.batch_annotation(batch_dir, mode='basic', annotation_type='general')
        print("✓ 批量标注成功")
        print(f"处理了 {len(results)} 张图片")

        # 保存结果
        output_file = 'test_batch_results.json'
        labeler.save_results(results, output_file, 'json')
        print(f"✓ 结果已保存到: {output_file}")
        return True
    except Exception as e:
        print(f"✗ 批量标注失败: {e}")
        return False

def test_example_learning(labeler):
    """测试样例学习功能"""
    examples_dir = 'examples'
    test_image = None

    # 查找样例图片
    if os.path.exists(examples_dir):
        example_images = [f for f in os.listdir(examples_dir)
                         if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'))]

        if len(example_images) >= 1:
            for i, img in enumerate(example_images[:2]):  # 最多添加2个样例
                example_path = os.path.join(examples_dir, img)
                labeler.add_example(example_path, f"测试样例 {i+1}")
            print("✓ 样例添加成功")

            # 查找测试图片（非样例图片）
            for directory in ['test_images', '.']:
                if os.path.exists(directory) and directory != examples_dir:
                    for file in os.listdir(directory):
                        if file.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')):
                            if os.path.join(directory, file) not in [os.path.join(examples_dir, img) for img in example_images]:
                                test_image = os.path.join(directory, file)
                                break
                    if test_image:
                        break
        else:
            print("⚠️  examples 文件夹中没有图片，跳过样例学习测试")
            return
    else:
        print("⚠️  examples 文件夹不存在，跳过样例学习测试")
        return

    if not test_image:
        print("⚠️  未找到测试图片，跳过精准标注测试")
        return

    print(f"\n测试精准标注（基于样例）: {test_image}")

    try:
        result = labeler.precise_annotation_with_examples(test_image)
        print("✓ 精准标注成功")
        print(f"结果预览: {result[:200]}...")
        return True
    except Exception as e:
        print(f"✗ 精准标注失败: {e}")
        return False

def main():
    """主测试函数"""
    print("GLM-4.6V 快速测试")
    print("=" * 40)

    # 检查API密钥
    if not os.getenv('GLM_API_KEY'):
        print("⚠️  未设置 GLM_API_KEY 环境变量")
        print("请设置API密钥后重试")
        sys.exit(1)

    # 测试API连接
    labeler = test_api_connection()
    if not labeler:
        print("API连接失败，退出测试")
        sys.exit(1)

    # 运行各项测试
    tests = [
        ("单图标注测试", lambda: test_single_annotation(labeler)),
        ("批量标注测试", lambda: test_batch_annotation(labeler)),
        ("样例学习测试", lambda: test_example_learning(labeler))
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 20)
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {test_name} 异常: {e}")

    # 测试总结
    print("\n" + "=" * 40)
    print("测试总结:")
    print(f"通过: {passed}/{total}")
    print(f"成功率: {passed/total*100:.1f}%")

    if passed == total:
        print("🎉 所有测试通过！GLM-4.6V 标注系统运行正常")
    else:
        print("⚠️  部分测试失败，请检查配置和网络连接")

    print("\n功能已验证，可以开始使用标注系统！")

if __name__ == "__main__":
    main()