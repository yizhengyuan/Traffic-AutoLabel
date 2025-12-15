#!/usr/bin/env python3
"""
Gemini API 修复测试
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

def test_gemini_models():
    """测试不同的Gemini模型"""
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')

    if not api_key:
        print("❌ 未找到API密钥")
        return

    print("🔧 配置Gemini API...")
    genai.configure(api_key=api_key)

    # 尝试列出所有可用模型
    try:
        print("\n📋 尝试列出可用模型...")
        models = genai.list_models()
        print(f"找到 {len(list(models))} 个模型")

        for model in models:
            if 'generateContent' in model.supported_generation_methods:
                print(f"✅ {model.name} - {model.display_name}")

    except Exception as e:
        print(f"❌ 列出模型失败: {e}")

    # 尝试不同的模型名称
    model_names = [
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-pro',
        'gemini-pro-vision',
        'models/gemini-1.5-flash',
        'models/gemini-1.5-pro',
        'models/gemini-pro',
        'models/gemini-pro-vision'
    ]

    print(f"\n🧪 测试 {len(model_names)} 种模型配置...")

    working_models = []
    for model_name in model_names:
        try:
            print(f"   测试: {model_name}")
            model = genai.GenerativeModel(model_name)

            # 尝试简单的文本生成
            response = model.generate_content("Hello")
            print(f"   ✅ {model_name} - 工作正常")
            working_models.append(model_name)
            break  # 找到一个工作的模型就够了

        except Exception as e:
            print(f"   ❌ {model_name} - 错误: {str(e)[:80]}...")

    if working_models:
        print(f"\n🎉 找到可用模型: {working_models[0]}")

        # 测试图像功能
        try:
            from PIL import Image
            img = Image.new('RGB', (100, 100), color='red')

            model = genai.GenerativeModel(working_models[0])
            response = model.generate_content(["这是什么颜色？", img])
            print(f"🎨 图像识别功能正常工作")

            return working_models[0]

        except Exception as e:
            print(f"❌ 图像识别功能测试失败: {e}")
    else:
        print("\n❌ 没有找到可用的模型")

    return None

def update_config_with_working_model(working_model):
    """更新配置文件以使用工作的模型"""
    if not working_model:
        return False

    try:
        # 读取原始文件
        with open('traffic_sign_recognition.py', 'r') as f:
            content = f.read()

        # 替换模型配置部分
        old_section = """        # 尝试不同的可用模型
        possible_models = [
            'gemini-1.5-pro',
            'gemini-1.5-flash',
            'gemini-pro',
            'gemini-pro-vision'
        ]"""

        new_section = f"""        # 使用已知工作的模型
        self.model = genai.GenerativeModel('{working_model}')
        self.text_model = genai.GenerativeModel('{working_model}')
        print(f"✅ 使用模型: {working_model}")"""

        if old_section in content:
            updated_content = content.replace(old_section, new_section)

            # 写入更新后的文件
            with open('traffic_sign_recognition.py', 'w') as f:
                f.write(updated_content)

            print(f"✅ 已更新配置文件使用模型: {working_model}")
            return True
        else:
            print("❌ 无法找到要替换的配置部分")
            return False

    except Exception as e:
        print(f"❌ 更新配置文件失败: {e}")
        return False

def main():
    """主函数"""
    print("🔧 Gemini API 修复工具")
    print("=" * 40)

    working_model = test_gemini_models()

    if working_model:
        print(f"\n🎯 找到可用模型: {working_model}")
        if update_config_with_working_model(working_model):
            print(f"\n✅ 修复完成！现在可以使用Gemini API进行识别了。")
            print(f"📝 尝试运行: python3 -c \"from traffic_sign_recognition import TrafficSignRecognizer; r = TrafficSignRecognizer(); print(r.basic_recognition('test_images/extracted_frames/D6_frame_0005.jpg'))\"")
        else:
            print(f"\n⚠️  找到可用模型但更新配置失败")
    else:
        print(f"\n❌ 无法找到可用的Gemini模型")
        print(f"💡 可能的原因:")
        print(f"   • 网络连接问题")
        print(f"   • API密钥无效")
        print(f"   • 地理位置限制")
        print(f"   • API配额用完")
        print(f"\n🔄 继续使用本地模拟功能进行测试")

if __name__ == "__main__":
    main()