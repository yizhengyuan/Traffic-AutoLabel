#!/usr/bin/env python3
"""
GLM-4.6V 视频数据标注系统演示脚本

这个脚本演示了如何使用 GLM-4.6V 视频数据标注系统的各种功能，
包括基础标注、基于样例的精准标注、视频帧提取和批量处理。
"""

import os
import sys
from video_data_labeler import VideoDataLabeler

def demo_without_api_key():
    """演示不使用API密钥的功能"""
    print("GLM-4.6V 视频数据标注系统演示")
    print("=" * 50)
    print("\n注意：此演示不需要API密钥，仅展示系统结构和功能。")
    print("要使用实际的标注功能，请配置GLM API密钥。")
    print()

    # 检查文件结构
    print("1. 检查项目文件结构：")
    files_to_check = [
        'video_data_labeler.py',
        'requirements.txt',
        'demo_glm.py'
    ]

    for file in files_to_check:
        status = "✓" if os.path.exists(file) else "✗"
        print(f"   {status} {file}")

    # 检查文件夹
    print("\n2. 创建必要的文件夹：")
    folders = ['examples', 'test_images', 'video_frames', 'output']

    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"   ✓ 创建文件夹: {folder}")
        else:
            print(f"   ✓ 文件夹已存在: {folder}")

    # 展示代码结构
    print("\n3. 主要功能模块：")
    print("   ✓ VideoDataLabeler 类：核心标注器")
    print("   ✓ 基础标注功能：basic_annotation()")
    print("   ✓ 精准标注功能：precise_annotation_with_examples()")
    print("   ✓ 批量标注功能：batch_annotation()")
    print("   ✓ 视频帧提取功能：extract_frames_from_video()")
    print("   ✓ 多格式输出：JSON, TXT, CSV")

def demo_with_api_key():
    """演示需要API密钥的功能"""
    print("\n" + "=" * 50)
    print("API 功能演示")
    print("=" * 50)

    try:
        # 初始化标注器
        print("1. 初始化 GLM-4.6V 标注器...")
        labeler = VideoDataLabeler()
        print("   ✓ 初始化成功！")

        # 检查测试图片
        test_images_dir = "test_images"
        if os.path.exists(test_images_dir):
            images = [f for f in os.listdir(test_images_dir)
                     if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'))]

            if images:
                print(f"\n2. 在 {test_images_dir} 中找到 {len(images)} 张测试图片")

                # 演示基础标注
                test_image = os.path.join(test_images_dir, images[0])
                print(f"\n3. 演示基础标注：{images[0]}")
                print("   (通用标注)")
                try:
                    result = labeler.basic_annotation(test_image, "general")
                    print(f"   标注结果: {result[:200]}...")
                except Exception as e:
                    print(f"   标注失败: {e}")

                # 如果有样例，演示精准标注
                examples_dir = "examples"
                if os.path.exists(examples_dir):
                    example_images = [f for f in os.listdir(examples_dir)
                                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'))]

                    if example_images:
                        print(f"\n4. 添加样例进行精准标注...")
                        for i, example_img in enumerate(example_images[:2]):  # 最多添加2个样例
                            example_path = os.path.join(examples_dir, example_img)
                            labeler.add_example(example_path, f"样例标注 {i+1}")

                        print("   ✓ 样例添加完成")
                        try:
                            precise_result = labeler.precise_annotation_with_examples(test_image)
                            print(f"   精准标注结果: {precise_result[:200]}...")
                        except Exception as e:
                            print(f"   精准标注失败: {e}")

                # 演示不同类型的标注
                annotation_types = ["object", "scene", "text", "activity"]
                print(f"\n5. 演示不同类型的标注...")
                for ann_type in annotation_types[:2]:  # 只演示前2种
                    try:
                        type_result = labeler.basic_annotation(test_image, ann_type)
                        print(f"   {ann_type} 标注: {type_result[:100]}...")
                    except Exception as e:
                        print(f"   {ann_type} 标注失败: {e}")

            else:
                print(f"\n2. {test_images_dir} 文件夹中没有找到测试图片")
                print("   请添加一些图片到 test_images 文件夹来测试标注功能")
        else:
            print(f"\n2. {test_images_dir} 文件夹不存在")
            print("   请创建 test_images 文件夹并添加测试图片")

    except Exception as e:
        print(f"   ✗ 初始化失败: {e}")
        print("\n请检查:")
        print("1. 是否设置了 GLM_API_KEY 环境变量")
        print("2. API密钥是否有效")
        print("3. 网络连接是否正常")

def demo_video_features():
    """演示视频相关功能"""
    print("\n" + "=" * 50)
    print("视频功能演示")
    print("=" * 50)

    print("视频帧提取功能:")
    print("   支持的格式: MP4, AVI, MOV, MKV 等")
    print("   功能: 从视频中提取帧进行批量标注")
    print("   使用方法:")
    print("   ```python")
    print("   labeler = VideoDataLabeler()")
    print("   frame_paths = labeler.extract_frames_from_video(")
    print("       'video.mp4', 'output_frames', frame_interval=30)")
    print("   results = labeler.batch_annotation('output_frames')")
    print("   labeler.save_results(results, 'annotation_results.json')")
    print("   ```")

def show_usage_examples():
    """显示使用示例"""
    print("\n" + "=" * 50)
    print("使用示例")
    print("=" * 50)

    examples = {
        "基础标注": """
# 通用标注
labeler = VideoDataLabeler()
result = labeler.basic_annotation('image.jpg', 'general')

# 对象检测标注
result = labeler.basic_annotation('image.jpg', 'object')

# 场景分析标注
result = labeler.basic_annotation('image.jpg', 'scene')
""",

        "精准标注": """
# 添加样例
labeler.add_example('example1.jpg', '标签1')
labeler.add_example('example2.jpg', '标签2')

# 基于样例的精准标注
result = labeler.precise_annotation_with_examples('target.jpg')
""",

        "批量处理": """
# 批量标注文件夹中的所有图片
results = labeler.batch_annotation(
    'images_folder',
    mode='basic',
    annotation_type='general'
)

# 保存结果为不同格式
labeler.save_results(results, 'results.json', 'json')
labeler.save_results(results, 'results.txt', 'txt')
labeler.save_results(results, 'results.csv', 'csv')
""",

        "视频处理": """
# 从视频提取帧
frame_paths = labeler.extract_frames_from_video(
    'video.mp4',
    'frames_folder',
    frame_interval=30,  # 每秒提取1帧（假设30fps）
    max_frames=100      # 最多提取100帧
)

# 批量标注提取的帧
results = labeler.batch_annotation('frames_folder')
labeler.save_results(results, 'video_annotation_results.json')
"""
    }

    for title, code in examples.items():
        print(f"\n{title}:")
        print(code)

def main():
    """主演示函数"""
    print("GLM-4.6V 视频数据标注系统")
    print("基于智谱AI GLM-4.6V 大模型的数据标注工具")
    print("=" * 60)

    # 检查是否设置了API密钥
    api_key_set = bool(os.getenv('GLM_API_KEY'))

    if not api_key_set:
        print("\n⚠️  未检测到 GLM_API_KEY 环境变量")
        print("请设置API密钥来使用完整的标注功能:")
        print("export GLM_API_KEY='your_api_key_here'")
        print("或者在 .env 文件中添加: GLM_API_KEY=your_api_key_here")

    # 运行演示
    demo_without_api_key()

    if api_key_set:
        print("\n✓ 检测到 API 密钥，运行完整功能演示...")
        demo_with_api_key()
    else:
        print("\n运行基础演示（无API功能）...")

    demo_video_features()
    show_usage_examples()

    print("\n" + "=" * 60)
    print("演示完成！")
    print("\n下一步:")
    print("1. 设置 GLM_API_KEY 环境变量")
    print("2. 安装依赖: pip install -r requirements.txt")
    print("3. 准备测试数据到 test_images 和 examples 文件夹")
    print("4. 运行 python demo_glm.py 进行完整测试")

if __name__ == "__main__":
    main()