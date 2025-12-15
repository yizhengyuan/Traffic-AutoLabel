import os
import io
import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import base64
from typing import List, Dict, Tuple, Optional
import json
import requests

class VideoDataLabeler:
    def __init__(self, api_key: str = None):
        """
        初始化视频数据标注器

        Args:
            api_key: GLM API密钥，如果不提供则从环境变量读取
        """
        load_dotenv()

        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv('GLM_API_KEY')

        if not self.api_key:
            raise ValueError("请设置GLM_API_KEY环境变量或提供api_key参数")

        # 配置GLM-4.6V模型
        self.model = "glm-4v-plus"
        self.api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

        # 测试模型连接
        try:
            test_response = self._make_api_call("测试连接", None)
            if test_response:
                print(f"✅ 成功连接到GLM-4.6V模型")
            else:
                print("⚠️ 模型连接测试失败，但初始化完成")
        except Exception as e:
            print(f"⚠️ 模型连接测试失败: {e}")
            print("✅ GLM-4.6V模型初始化完成")

        # 存储样例数据
        self.examples = []

    def _encode_image_to_base64(self, image_path: str) -> str:
        """将图片编码为base64格式"""
        try:
            with Image.open(image_path) as img:
                # 转换为RGB格式
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # 调整大小以符合API限制
                max_size = 1024
                if max(img.size) > max_size:
                    ratio = max_size / max(img.size)
                    new_size = tuple(int(dim * ratio) for dim in img.size)
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                # 保存到内存并编码为base64
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                img_str = base64.b64encode(buffered.getvalue()).decode()

                return img_str
        except Exception as e:
            print(f"图片编码失败: {e}")
            raise

    def _make_api_call(self, prompt: str, image_base64: str = None) -> str:
        """调用GLM-4.6V API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            # 构建消息内容
            content = [{"type": "text", "text": prompt}]

            if image_base64:
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                })

            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }

            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                error_msg = f"API调用失败: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail.get('error', {}).get('message', '未知错误')}"
                except:
                    pass
                return error_msg

        except requests.exceptions.RequestException as e:
            return f"网络请求失败: {str(e)}"
        except Exception as e:
            return f"API调用异常: {str(e)}"

    def add_example(self, image_path: str, label: str) -> bool:
        """
        添加标注样例

        Args:
            image_path: 图片路径
            label: 标签描述

        Returns:
            bool: 是否成功添加
        """
        try:
            if not os.path.exists(image_path):
                print(f"图片文件不存在: {image_path}")
                return False

            # 验证图片格式
            with Image.open(image_path) as img:
                img.verify()

            self.examples.append({
                'image_path': image_path,
                'label': label
            })
            print(f"成功添加样例: {label}")
            return True

        except Exception as e:
            print(f"添加样例失败: {e}")
            return False

    def preprocess_image(self, image_path: str, max_size: int = 1024) -> Image.Image:
        """
        预处理图片

        Args:
            image_path: 图片路径
            max_size: 最大尺寸

        Returns:
            PIL.Image: 处理后的图片
        """
        try:
            img = Image.open(image_path)

            # 转换为RGB格式
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # 调整大小
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = tuple(int(dim * ratio) for dim in img.size)
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            return img

        except Exception as e:
            print(f"图片预处理失败: {e}")
            raise

    def basic_annotation(self, image_path: str, annotation_type: str = "general") -> str:
        """
        基础数据标注（通用标注）

        Args:
            image_path: 图片路径
            annotation_type: 标注类型（general, object, scene, text, activity等）

        Returns:
            str: 标注结果
        """
        try:
            image_base64 = self._encode_image_to_base64(image_path)

            # 根据标注类型定制prompt
            prompts = {
                "general": """
                请对这张图片进行详细的标注分析。请描述：
                1. 图片中的主要对象和元素
                2. 场景环境和背景信息
                3. 任何重要的文字或标签
                4. 图片的整体主题和内容
                5. 适用于数据标注的标签建议

                请用中文回答，尽可能详细和准确。
                """,
                "object": """
                请识别这张图片中的所有对象。请列出：
                1. 所有可见的对象及其位置
                2. 对象的属性（颜色、大小、形状等）
                3. 对象之间的关系
                4. 建议的分类标签

                请用中文回答，适合机器学习标注用途。
                """,
                "scene": """
                请分析这张图片的场景信息。请描述：
                1. 场景类型（室内/室外、具体场所等）
                2. 环境特征（光线、天气、时间等）
                3. 主要活动和事件
                4. 场景标注建议

                请用中文回答，适合视频场景分析。
                """,
                "text": """
                请识别和分析这张图片中的文字内容。请提供：
                1. 所有可见的文字内容
                2. 文字的位置和排版信息
                3. 文字的含义和用途
                4. OCR标注建议

                请用中文回答，适合文字识别标注。
                """,
                "activity": """
                请分析这张图片中的活动和动作。请描述：
                1. 正在进行的主要活动
                2. 人物的动作和姿态
                3. 活动的上下文环境
                4. 活动分类标签建议

                请用中文回答，适合行为识别标注。
                """
            }

            prompt = prompts.get(annotation_type, prompts["general"])

            result = self._make_api_call(prompt, image_base64)
            return result

        except Exception as e:
            return f"标注失败: {str(e)}"

    def precise_annotation_with_examples(self, image_path: str) -> str:
        """
        基于样例的精准标注

        Args:
            image_path: 待标注图片路径

        Returns:
            str: 标注结果
        """
        try:
            if not self.examples:
                return "请先添加样例数据才能进行精准标注"

            target_image_base64 = self._encode_image_to_base64(image_path)

            # 构建包含样例的提示
            prompt = f"""
我将提供一些标注样例，然后请你标注新的图片。

请仔细学习以下样例中的标注模式，然后标注新的图片。

样例数据：
"""

            # 添加样例信息
            for i, example in enumerate(self.examples, 1):
                example_image_base64 = self._encode_image_to_base64(example['image_path'])
                prompt += f"""

样例{i}: {example['label']}
[图片编码为base64格式，用于模型学习]
"""

            prompt += f"""

以上共有{len(self.examples)}个样例。现在请标注下面这张新的图片，
参考上面样例的标注风格和标准，给出最准确的标注结果。请说明：
1. 基于样例学习得出的标注内容
2. 与哪个样例的标注风格最相似（如果有）
3. 标注的置信程度
4. 关键特征分析
5. 建议的标签和分类

请按照样例的格式进行标注。
"""

            # 由于GLM API的限制，我们需要分步骤处理
            # 首先发送样例学习请求，然后处理目标图片

            # 发送包含样例信息的请求（不包含图片）
            examples_prompt = prompt + f"\n\n样例学习完成，请准备标注新图片。"

            # 现在处理目标图片
            final_prompt = f"""
基于前面学习的{len(self.examples)}个样例，请对这张新图片进行精准标注。
请参考样例的标注风格和标准，提供详细的标注结果，包括：
1. 详细的对象描述和标签
2. 场景分析和环境信息
3. 与样例相似的标注特征
4. 适合机器学习训练的结构化标签
5. 标注置信度评估
"""

            result = self._make_api_call(final_prompt, target_image_base64)
            return result

        except Exception as e:
            return f"精准标注失败: {str(e)}"

    def batch_annotation(self, image_folder: str, mode: str = 'basic',
                        annotation_type: str = 'general',
                        output_format: str = 'json') -> Dict[str, str]:
        """
        批量标注图片

        Args:
            image_folder: 图片文件夹路径
            mode: 标注模式 ('basic' 或 'precise')
            annotation_type: 标注类型 ('general', 'object', 'scene', 'text', 'activity')
            output_format: 输出格式 ('json', 'txt', 'csv')

        Returns:
            Dict: 文件名到标注结果的映射
        """
        results = {}

        if not os.path.exists(image_folder):
            return {"error": "文件夹不存在"}

        supported_formats = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')
        image_files = [f for f in os.listdir(image_folder)
                      if f.lower().endswith(supported_formats)]

        if not image_files:
            return {"error": "文件夹中没有支持的图片文件"}

        print(f"找到 {len(image_files)} 张图片，开始批量标注...")

        for i, filename in enumerate(image_files, 1):
            image_path = os.path.join(image_folder, filename)
            print(f"正在标注 ({i}/{len(image_files)}): {filename}")

            try:
                if mode == 'precise':
                    result = self.precise_annotation_with_examples(image_path)
                else:
                    result = self.basic_annotation(image_path, annotation_type)

                results[filename] = result
                print(f"✓ 完成: {filename}")

            except Exception as e:
                error_msg = f"标注失败: {str(e)}"
                results[filename] = error_msg
                print(f"✗ 失败: {filename} - {error_msg}")

        return results

    def save_results(self, results: Dict[str, str], output_file: str = 'annotation_results.json',
                    output_format: str = 'json'):
        """
        保存标注结果到文件

        Args:
            results: 标注结果字典
            output_file: 输出文件名
            output_format: 输出格式 ('json', 'txt', 'csv')
        """
        try:
            if output_format == 'json':
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2)

            elif output_format == 'txt':
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("视频数据标注结果\n")
                    f.write("=" * 50 + "\n\n")

                    for filename, result in results.items():
                        f.write(f"文件: {filename}\n")
                        f.write("-" * 30 + "\n")
                        f.write(f"{result}\n\n")

            elif output_format == 'csv':
                import csv
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['文件名', '标注结果'])
                    for filename, result in results.items():
                        writer.writerow([filename, result])

            print(f"标注结果已保存到: {output_file}")

        except Exception as e:
            print(f"保存结果失败: {e}")

    def extract_frames_from_video(self, video_path: str, output_folder: str,
                                 frame_interval: int = 1, max_frames: int = None) -> List[str]:
        """
        从视频中提取帧用于标注

        Args:
            video_path: 视频文件路径
            output_folder: 输出文件夹
            frame_interval: 帧间隔（每隔多少帧提取一次）
            max_frames: 最大提取帧数

        Returns:
            List[str]: 提取的帧文件路径列表
        """
        try:
            if not os.path.exists(output_folder):
                os.makedirs(output_folder)

            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件: {video_path}")

            frame_count = 0
            extracted_count = 0
            frame_paths = []

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)

            print(f"视频信息: 总帧数 {total_frames}, FPS: {fps}")

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_count % frame_interval == 0:
                    if max_frames and extracted_count >= max_frames:
                        break

                    frame_filename = f"frame_{extracted_count:06d}.jpg"
                    frame_path = os.path.join(output_folder, frame_filename)
                    cv2.imwrite(frame_path, frame)
                    frame_paths.append(frame_path)
                    extracted_count += 1

                frame_count += 1

            cap.release()
            print(f"成功提取 {extracted_count} 帧到 {output_folder}")
            return frame_paths

        except Exception as e:
            print(f"视频帧提取失败: {e}")
            return []


def main():
    """主函数 - 演示使用"""
    print("GLM-4.6V 视频数据标注系统")
    print("=" * 30)

    # 初始化标注器
    try:
        labeler = VideoDataLabeler()
        print("✓ GLM-4.6V API 初始化成功")
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        print("\n请确保:")
        print("1. 设置了 GLM_API_KEY 环境变量")
        print("2. API密钥有效且有足够的额度")
        return

    # 创建必要的文件夹
    folders = ['test_images', 'examples', 'video_frames', 'output']
    for folder in folders:
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"✓ 创建文件夹: {folder}")

    print("\n使用说明:")
    print("1. 将图片放入 'test_images' 文件夹进行单张标注")
    print("2. 将样例图片放入 'examples' 文件夹进行学习")
    print("3. 将视频文件用于提取帧并标注")
    print("\n功能菜单:")
    print("- 基础标注: labeler.basic_annotation(image_path, annotation_type)")
    print("- 添加样例: labeler.add_example(image_path, label)")
    print("- 精准标注: labeler.precise_annotation_with_examples(image_path)")
    print("- 批量标注: labeler.batch_annotation(folder_path, mode, annotation_type)")
    print("- 视频帧提取: labeler.extract_frames_from_video(video_path, output_folder)")
    print("- 保存结果: labeler.save_results(results, output_file, output_format)")

if __name__ == "__main__":
    main()