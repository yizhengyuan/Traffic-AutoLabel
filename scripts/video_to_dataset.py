#!/usr/bin/env python3
"""
🚀 视频到数据集一键流水线

完整流程：
1. 从视频抽帧 (3 FPS)
2. 自动标注 (GLM-4.6V + RAG)
3. 生成可视化图片
4. 打包成 Dataset 文件夹

用法:
    python3 scripts/video_to_dataset.py --video D3
    python3 scripts/video_to_dataset.py --video D4 --workers 20 --rag
"""

import os
import sys
import json
import argparse
import subprocess
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 添加 scripts 目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from auto_labeling_parallel import (
    process_single_image,
    to_xanylabeling_format,
    get_image_size
)


# ============================================================================
# 配置
# ============================================================================

VIDEO_DIR = Path("traffic_sign_data/videos/raw_clips")
TEMP_FRAMES_DIR = Path("temp_frames")
OUTPUT_BASE = Path("output")

COLORS = {
    'pedestrian': (255, 0, 0),
    'vehicle': (0, 255, 0),
    'traffic_sign': (0, 100, 255),
    'construction': (255, 165, 0),
}


# ============================================================================
# Step 1: 抽帧
# ============================================================================

def extract_frames(video_name: str, fps: int = 3) -> tuple:
    """从视频抽帧"""
    video_path = VIDEO_DIR / f"{video_name}.mp4"
    
    if not video_path.exists():
        print(f"❌ 视频不存在: {video_path}")
        return None, 0
    
    # 创建临时帧目录
    frames_dir = TEMP_FRAMES_DIR / video_name
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    # 清空旧帧
    for old_frame in frames_dir.glob("*.jpg"):
        old_frame.unlink()
    
    print(f"\n📹 Step 1: 抽帧 ({fps} FPS)")
    print(f"   视频: {video_path}")
    
    # 使用 ffmpeg 抽帧
    output_pattern = str(frames_dir / f"{video_name}_%06d.jpg")
    cmd = [
        "ffmpeg", "-i", str(video_path),
        "-vf", f"fps={fps}",
        "-q:v", "2",  # 高质量
        output_pattern,
        "-y"  # 覆盖
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True,
            timeout=300  # 5分钟超时
        )
        
        frame_count = len(list(frames_dir.glob("*.jpg")))
        print(f"   ✅ 抽取 {frame_count} 帧")
        
        return frames_dir, frame_count
        
    except subprocess.TimeoutExpired:
        print("   ❌ ffmpeg 超时")
        return None, 0
    except Exception as e:
        print(f"   ❌ ffmpeg 错误: {e}")
        return None, 0


# ============================================================================
# Step 2: 自动标注
# ============================================================================

def run_labeling(frames_dir: Path, video_name: str, workers: int, use_rag: bool) -> Path:
    """运行自动标注"""
    print(f"\n🏷️ Step 2: 自动标注")
    print(f"   Workers: {workers} | RAG: {'✅' if use_rag else '❌'}")
    
    api_key = os.getenv("ZAI_API_KEY")
    if not api_key:
        print("   ❌ 请设置 ZAI_API_KEY")
        return None
    
    # 获取帧列表
    image_files = sorted(frames_dir.glob("*.jpg"))
    if not image_files:
        print("   ❌ 没有找到帧")
        return None
    
    # 创建输出目录
    rag_suffix = "_rag" if use_rag else ""
    output_dir = OUTPUT_BASE / f"{video_name.lower()}_annotations{rag_suffix}"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 准备任务
    task_args = [(str(img), api_key, 3, use_rag) for img in image_files]
    
    start_time = time.time()
    stats = {"pedestrian": 0, "vehicle": 0, "traffic_sign": 0, "construction": 0}
    success = 0
    errors = 0
    
    # 并行处理
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_single_image, arg): arg[0] for arg in task_args}
        
        for i, future in enumerate(as_completed(futures)):
            image_path = futures[future]
            image_name = Path(image_path).name
            
            try:
                _, detections, error = future.result()
                
                if error:
                    print(f"  ⚠️ [{i+1}/{len(image_files)}] {error}")
                    errors += 1
                else:
                    for det in detections:
                        cat = det.get("category", "unknown")
                        stats[cat] = stats.get(cat, 0) + 1
                    
                    # 保存
                    annotation = to_xanylabeling_format(detections, image_path)
                    out_path = output_dir / f"{Path(image_path).stem}.json"
                    with open(out_path, "w", encoding="utf-8") as f:
                        json.dump(annotation, f, ensure_ascii=False, indent=2)
                    
                    emoji = "✅" if detections else "⚪"
                    print(f"  {emoji} [{i+1}/{len(image_files)}] {len(detections)} objects")
                    success += 1
                    
            except Exception as e:
                print(f"  ❌ [{i+1}/{len(image_files)}] {e}")
                errors += 1
    
    elapsed = time.time() - start_time
    print(f"\n   📊 统计: {stats}")
    print(f"   ⏱️ 耗时: {elapsed:.1f}s ({elapsed/len(image_files):.2f}s/帧)")
    print(f"   ✅ 成功: {success} | ❌ 错误: {errors}")
    
    return output_dir


# ============================================================================
# Step 3: 可视化
# ============================================================================

def generate_visualizations(frames_dir: Path, annotations_dir: Path, video_name: str) -> Path:
    """生成可视化图片"""
    from PIL import Image, ImageDraw
    
    print(f"\n🎨 Step 3: 生成可视化")
    
    vis_dir = OUTPUT_BASE / f"{video_name.lower()}_visualized"
    vis_dir.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for json_path in sorted(annotations_dir.glob("*.json")):
        frame_name = json_path.stem + ".jpg"
        frame_path = frames_dir / frame_name
        
        if not frame_path.exists():
            continue
        
        img = Image.open(frame_path)
        draw = ImageDraw.Draw(img)
        
        with open(json_path) as f:
            data = json.load(f)
        
        for shape in data.get("shapes", []):
            pts = shape["points"]
            cat = shape.get("flags", {}).get("category", "unknown")
            label = shape["label"]
            
            color = COLORS.get(cat, (128, 128, 128))
            draw.rectangle([pts[0][0], pts[0][1], pts[1][0], pts[1][1]], 
                          outline=color, width=3)
            
            # 标签
            short_label = label[:20] + "..." if len(label) > 20 else label
            draw.text((pts[0][0], pts[0][1] - 15), short_label, fill=color)
        
        out_path = vis_dir / f"{json_path.stem}_vis.jpg"
        img.save(out_path)
        count += 1
        
        if count % 50 == 0:
            print(f"   已处理 {count} 张...")
    
    print(f"   ✅ 生成 {count} 张可视化图片")
    return vis_dir


# ============================================================================
# Step 4: 打包 Dataset
# ============================================================================

def create_dataset(video_name: str, frames_dir: Path, annotations_dir: Path, vis_dir: Path) -> Path:
    """创建 Dataset 文件夹"""
    import shutil
    
    print(f"\n📦 Step 4: 创建 Dataset")
    
    dataset_dir = Path(f"{video_name}_dataset")
    
    # 创建目录结构
    (dataset_dir / "video").mkdir(parents=True, exist_ok=True)
    (dataset_dir / "frames").mkdir(parents=True, exist_ok=True)
    (dataset_dir / "annotations").mkdir(parents=True, exist_ok=True)
    (dataset_dir / "visualized").mkdir(parents=True, exist_ok=True)
    
    # 复制视频
    video_src = VIDEO_DIR / f"{video_name}.mp4"
    if video_src.exists():
        shutil.copy(video_src, dataset_dir / "video" / f"{video_name}.mp4")
        print(f"   ✅ 复制视频")
    
    # 复制帧
    for frame in frames_dir.glob("*.jpg"):
        shutil.copy(frame, dataset_dir / "frames" / frame.name)
    print(f"   ✅ 复制 {len(list(frames_dir.glob('*.jpg')))} 帧")
    
    # 复制标注
    for ann in annotations_dir.glob("*.json"):
        shutil.copy(ann, dataset_dir / "annotations" / ann.name)
    print(f"   ✅ 复制 {len(list(annotations_dir.glob('*.json')))} 标注")
    
    # 复制可视化
    if vis_dir and vis_dir.exists():
        for vis in vis_dir.glob("*.jpg"):
            shutil.copy(vis, dataset_dir / "visualized" / vis.name)
        print(f"   ✅ 复制 {len(list(vis_dir.glob('*.jpg')))} 可视化")
    
    # 生成压缩包
    print(f"   📦 创建压缩包...")
    shutil.make_archive(str(dataset_dir), 'zip', '.', str(dataset_dir))
    zip_size = Path(f"{dataset_dir}.zip").stat().st_size / (1024 * 1024)
    print(f"   ✅ {dataset_dir}.zip ({zip_size:.1f} MB)")
    
    return dataset_dir


# ============================================================================
# 主函数
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="视频到数据集一键流水线")
    parser.add_argument("--video", type=str, required=True, help="视频名称 (如 D3, D4)")
    parser.add_argument("--fps", type=int, default=3, help="抽帧率 (默认 3)")
    parser.add_argument("--workers", type=int, default=20, help="并行线程数 (默认 20)")
    parser.add_argument("--rag", action="store_true", help="启用 RAG 细粒度分类")
    parser.add_argument("--skip-extract", action="store_true", help="跳过抽帧步骤")
    parser.add_argument("--skip-visualize", action="store_true", help="跳过可视化步骤")
    args = parser.parse_args()
    
    video_name = args.video
    
    print("=" * 70)
    print(f"🚀 视频到数据集流水线 - {video_name}")
    print(f"   FPS: {args.fps} | Workers: {args.workers} | RAG: {args.rag}")
    print("=" * 70)
    
    start_time = time.time()
    
    # Step 1: 抽帧
    if args.skip_extract:
        frames_dir = TEMP_FRAMES_DIR / video_name
        print(f"\n⏭️ 跳过抽帧，使用: {frames_dir}")
    else:
        frames_dir, frame_count = extract_frames(video_name, args.fps)
        if not frames_dir:
            return
    
    # Step 2: 标注
    annotations_dir = run_labeling(frames_dir, video_name, args.workers, args.rag)
    if not annotations_dir:
        return
    
    # Step 3: 可视化
    if args.skip_visualize:
        vis_dir = None
        print(f"\n⏭️ 跳过可视化")
    else:
        vis_dir = generate_visualizations(frames_dir, annotations_dir, video_name)
    
    # Step 4: 打包
    dataset_dir = create_dataset(video_name, frames_dir, annotations_dir, vis_dir)
    
    # 完成
    total_time = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"🎉 完成！总耗时: {total_time/60:.1f} 分钟")
    print(f"📁 Dataset: {dataset_dir}/")
    print(f"📦 压缩包: {dataset_dir}.zip")
    print("=" * 70)


if __name__ == "__main__":
    main()
