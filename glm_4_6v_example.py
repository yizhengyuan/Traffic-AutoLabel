#!/usr/bin/env python3
"""
GLM-4.6V API 调用示例
基于 Z.AI SDK (zai-sdk)

使用方法:
1. 安装 SDK: pip install zai-sdk
2. 设置 API Key: export ZAI_API_KEY="your_api_key"
3. 运行: python glm_4_6v_example.py
"""

import os
import base64
from pathlib import Path

# ============================================================================
# 安装提示
# ============================================================================
try:
    from zai import ZaiClient
except ImportError:
    print("❌ 请先安装 zai-sdk:")
    print("   pip install zai-sdk")
    exit(1)


# ============================================================================
# 配置
# ============================================================================
API_KEY = os.getenv("ZAI_API_KEY", "")  # 从环境变量获取，或在这里直接填入

if not API_KEY:
    print("❌ 请设置 ZAI_API_KEY 环境变量，或在代码中直接填入 API_KEY")
    print("   export ZAI_API_KEY='your_api_key_here'")
    exit(1)


# ============================================================================
# 工具函数
# ============================================================================
def image_to_base64_url(image_path: str) -> str:
    """将本地图片转换为 base64 data URL"""
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"图片不存在: {image_path}")
    
    # 根据扩展名确定 MIME 类型
    ext = path.suffix.lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp',
    }
    mime_type = mime_types.get(ext, 'image/jpeg')
    
    with open(path, 'rb') as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    return f"data:{mime_type};base64,{image_data}"


# ============================================================================
# 示例 1: 基础图片描述（非流式）
# ============================================================================
def example_basic_description(image_url: str):
    """
    基础用法：描述一张图片
    """
    print("\n" + "=" * 60)
    print("📌 示例 1: 基础图片描述（非流式）")
    print("=" * 60)
    
    client = ZaiClient(api_key=API_KEY)
    
    response = client.chat.completions.create(
        model="glm-4.6v",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    },
                    {
                        "type": "text",
                        "text": "请详细描述这张图片的内容。"
                    }
                ]
            }
        ]
    )
    
    print("\n📝 模型回复:")
    print(response.choices[0].message.content)
    return response


# ============================================================================
# 示例 2: 流式输出
# ============================================================================
def example_streaming(image_url: str):
    """
    流式用法：实时获取响应（类似打字机效果）
    """
    print("\n" + "=" * 60)
    print("📌 示例 2: 流式输出")
    print("=" * 60)
    
    client = ZaiClient(api_key=API_KEY)
    
    response = client.chat.completions.create(
        model="glm-4.6v",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    },
                    {
                        "type": "text",
                        "text": "请分析这张图片中的主要元素和构图。"
                    }
                ]
            }
        ],
        stream=True
    )
    
    print("\n📝 流式回复:")
    for chunk in response:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end='', flush=True)
    print()  # 换行


# ============================================================================
# 示例 3: 启用推理模式（Thinking）
# ============================================================================
def example_with_thinking(image_url: str):
    """
    带推理模式：模型会先进行思考，然后给出答案
    """
    print("\n" + "=" * 60)
    print("📌 示例 3: 启用推理模式 (Thinking)")
    print("=" * 60)
    
    client = ZaiClient(api_key=API_KEY)
    
    response = client.chat.completions.create(
        model="glm-4.6v",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    },
                    {
                        "type": "text",
                        "text": "这张图片是在什么季节拍摄的？请分析理由。"
                    }
                ]
            }
        ],
        thinking={
            "type": "enabled"
        },
        stream=True
    )
    
    print("\n🧠 推理过程 & 📝 回复:")
    for chunk in response:
        # 输出推理过程
        if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
            print(f"[思考] {chunk.choices[0].delta.reasoning_content}", end='', flush=True)
        # 输出正式内容
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end='', flush=True)
    print()


# ============================================================================
# 示例 4: 视觉定位（Grounding）- 返回目标坐标
# ============================================================================
def example_visual_grounding(image_url: str):
    """
    视觉定位：让模型返回目标物体的边界框坐标
    """
    print("\n" + "=" * 60)
    print("📌 示例 4: 视觉定位 (Grounding)")
    print("=" * 60)
    
    client = ZaiClient(api_key=API_KEY)
    
    response = client.chat.completions.create(
        model="glm-4.6v",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    },
                    {
                        "type": "text",
                        "text": "请找出图片中的所有物体，并用 JSON 格式返回每个物体的标签和边界框坐标。格式: [{\"label\": \"物体名\", \"bbox_2d\": [xmin, ymin, xmax, ymax]}]"
                    }
                ]
            }
        ],
        thinking={
            "type": "enabled"
        }
    )
    
    print("\n📍 检测结果:")
    print(response.choices[0].message.content)
    return response


# ============================================================================
# 示例 5: 使用本地图片
# ============================================================================
def example_local_image(local_image_path: str):
    """
    使用本地图片进行分析
    """
    print("\n" + "=" * 60)
    print("📌 示例 5: 使用本地图片")
    print("=" * 60)
    
    # 将本地图片转换为 base64 URL
    base64_url = image_to_base64_url(local_image_path)
    print(f"ℹ️  已将本地图片转换为 base64: {local_image_path}")
    
    client = ZaiClient(api_key=API_KEY)
    
    response = client.chat.completions.create(
        model="glm-4.6v",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": base64_url
                        }
                    },
                    {
                        "type": "text",
                        "text": "请描述这张图片的内容。"
                    }
                ]
            }
        ]
    )
    
    print("\n📝 模型回复:")
    print(response.choices[0].message.content)
    return response


# ============================================================================
# 示例 6: 多轮对话
# ============================================================================
def example_multi_turn_conversation(image_url: str):
    """
    多轮对话：基于同一张图片进行连续问答
    """
    print("\n" + "=" * 60)
    print("📌 示例 6: 多轮对话")
    print("=" * 60)
    
    client = ZaiClient(api_key=API_KEY)
    
    # 第一轮：描述图片
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                },
                {
                    "type": "text",
                    "text": "这张图片里有什么？"
                }
            ]
        }
    ]
    
    print("\n🗣️ 用户: 这张图片里有什么？")
    response1 = client.chat.completions.create(
        model="glm-4.6v",
        messages=messages
    )
    assistant_reply1 = response1.choices[0].message.content
    print(f"🤖 助手: {assistant_reply1}")
    
    # 添加助手回复到对话历史
    messages.append({
        "role": "assistant",
        "content": assistant_reply1
    })
    
    # 第二轮：追问
    messages.append({
        "role": "user",
        "content": "你能告诉我更多关于图片中颜色的信息吗？"
    })
    
    print("\n🗣️ 用户: 你能告诉我更多关于图片中颜色的信息吗？")
    response2 = client.chat.completions.create(
        model="glm-4.6v",
        messages=messages
    )
    assistant_reply2 = response2.choices[0].message.content
    print(f"🤖 助手: {assistant_reply2}")
    
    return response2


# ============================================================================
# 主程序
# ============================================================================
def main():
    print("=" * 60)
    print("🚀 GLM-4.6V API 调用示例")
    print("=" * 60)
    
    # 使用一张在线测试图片
    test_image_url = "https://aigc-files.bigmodel.cn/api/cogview/20250723213827da171a419b9b4906_0.png"
    
    print(f"\n📷 测试图片 URL: {test_image_url}")
    
    # 运行各个示例
    try:
        # 示例 1: 基础描述
        example_basic_description(test_image_url)
        
        # 示例 2: 流式输出
        example_streaming(test_image_url)
        
        # 示例 3: 推理模式
        example_with_thinking(test_image_url)
        
        # 示例 4: 视觉定位
        example_visual_grounding(test_image_url)
        
        # 示例 6: 多轮对话
        example_multi_turn_conversation(test_image_url)
        
        # 示例 5: 本地图片（如果有的话）
        local_test_dir = Path("test_images")
        if local_test_dir.exists():
            local_images = list(local_test_dir.glob("*.jpg")) + \
                          list(local_test_dir.glob("*.png")) + \
                          list(local_test_dir.glob("*.jpeg"))
            if local_images:
                example_local_image(str(local_images[0]))
            else:
                print("\n⚠️  跳过本地图片示例：test_images 文件夹中没有图片")
        else:
            print("\n⚠️  跳过本地图片示例：test_images 文件夹不存在")
        
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ 示例运行完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
