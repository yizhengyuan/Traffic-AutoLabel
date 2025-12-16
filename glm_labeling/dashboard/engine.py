"""
标注引擎模块

封装标注逻辑，支持事件发布。
支持两种模式：
1. IMAGES 模式：处理已有图片
2. VIDEO 模式：完整流水线（视频 → 抽帧 → 标注 → 可视化 → 打包）
"""

import asyncio
import time
import json
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from PIL import Image, ImageDraw

from .events import EventBus, Event, EventType, event_bus
from .models import Task, TaskStatus, TaskMode, FrameResult, Issue
from .config import DashboardConfig
from .video_processor import VideoProcessor


class LabelingEngine:
    """
    标注引擎
    
    管理标注任务的执行，发布实时事件。
    支持两种模式：IMAGES（处理已有图片）和 VIDEO（完整流水线）
    """
    
    def __init__(self, config: DashboardConfig):
        self.config = config
        self._executor: Optional[ThreadPoolExecutor] = None
        self._running_tasks: Dict[str, bool] = {}  # task_id -> is_running
        self._lock = threading.Lock()
        
        # 延迟导入，避免循环依赖
        self._detector = None
        self._reviewer = None
        self._video_processor = None
    
    @property
    def detector(self):
        """延迟加载检测器"""
        if self._detector is None:
            from ..core import ObjectDetector
            self._detector = ObjectDetector(api_key=self.config.api_key)
        return self._detector
    
    @property
    def reviewer(self):
        """延迟加载审查器"""
        if self._reviewer is None:
            from .reviewer import AnnotationReviewer
            self._reviewer = AnnotationReviewer(
                api_key=self.config.api_key,
                sample_rate=self.config.review_rate,
                enable_ai=self.config.enable_review
            )
        return self._reviewer
    
    @property
    def video_processor(self):
        """延迟加载视频处理器"""
        if self._video_processor is None:
            self._video_processor = VideoProcessor()
        return self._video_processor
    
    async def start_task(self, task: Task, image_paths: List[str] = None):
        """
        启动标注任务
        
        Args:
            task: 任务对象
            image_paths: 图片路径列表（仅 IMAGES 模式需要）
        """
        task.started_at = datetime.now().isoformat()
        
        with self._lock:
            self._running_tasks[task.id] = True
        
        # 发布任务开始事件
        await event_bus.publish(Event(
            type=EventType.TASK_STARTED,
            task_id=task.id,
            data={
                "mode": task.mode.value,
                "video_name": task.video_name,
                "total_frames": task.total_frames
            }
        ))
        
        # 根据模式选择处理流程
        if task.mode == TaskMode.VIDEO:
            # 视频模式：完整流水线
            def run_in_thread():
                asyncio.run(self._process_video_pipeline(task))
            
            thread = threading.Thread(target=run_in_thread)
            thread.start()
        else:
            # 图片模式
            task.status = TaskStatus.RUNNING
            task.total_frames = len(image_paths)
            
            output_dir = Path(task.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            vis_dir = output_dir.parent / f"{output_dir.name.replace('_annotations', '')}_visualized"
            vis_dir.mkdir(parents=True, exist_ok=True)
            
            def run_in_thread():
                asyncio.run(self._process_images(task, image_paths, output_dir, vis_dir))
            
            thread = threading.Thread(target=run_in_thread)
            thread.start()
    
    async def _process_video_pipeline(self, task: Task):
        """
        视频模式：完整流水线
        视频 → 抽帧 → 标注 → 可视化 → 打包
        """
        try:
            # ========== 阶段 1: 抽帧 ==========
            task.status = TaskStatus.EXTRACTING
            await event_bus.publish(Event(
                type=EventType.STAGE_CHANGED,
                task_id=task.id,
                data={"stage": "extracting", "message": f"正在从 {task.video_name} 抽帧..."}
            ))
            
            frames_dir = Path(f"temp_frames/{task.prefix}")
            
            def on_extract_progress(progress: float):
                task.extract_progress = progress
                # 同步发布事件（在线程中）
                asyncio.run(event_bus.publish(Event(
                    type=EventType.EXTRACT_PROGRESS,
                    task_id=task.id,
                    data={"progress": progress}
                )))
            
            frames_dir, frame_count = self.video_processor.extract_frames(
                video_name=task.video_name,
                output_dir=frames_dir,
                fps=task.fps,
                output_prefix=task.prefix,
                on_progress=on_extract_progress
            )
            
            if not frames_dir or frame_count == 0:
                raise Exception(f"抽帧失败: {task.video_name}")
            
            task.total_frames = frame_count
            task.frames_dir = str(frames_dir)
            task.extract_progress = 1.0
            
            await event_bus.publish(Event(
                type=EventType.EXTRACT_COMPLETED,
                task_id=task.id,
                data={"frame_count": frame_count, "frames_dir": str(frames_dir)}
            ))
            
            # ========== 阶段 2: 标注 ==========
            task.status = TaskStatus.RUNNING
            await event_bus.publish(Event(
                type=EventType.STAGE_CHANGED,
                task_id=task.id,
                data={"stage": "labeling", "message": f"正在标注 {frame_count} 帧..."}
            ))
            
            annotations_dir = Path(task.annotations_dir)
            annotations_dir.mkdir(parents=True, exist_ok=True)
            vis_dir = Path(task.visualized_dir)
            vis_dir.mkdir(parents=True, exist_ok=True)
            
            image_paths = sorted([str(p) for p in frames_dir.glob("*.jpg")])
            await self._process_images(task, image_paths, annotations_dir, vis_dir)
            
            # ========== 阶段 3: 可视化（已在标注阶段完成） ==========
            task.status = TaskStatus.VISUALIZING
            task.visualize_progress = 1.0
            await event_bus.publish(Event(
                type=EventType.STAGE_CHANGED,
                task_id=task.id,
                data={"stage": "visualizing", "message": "可视化已完成"}
            ))
            
            # ========== 阶段 4: 打包数据集 ==========
            task.status = TaskStatus.PACKAGING
            await event_bus.publish(Event(
                type=EventType.STAGE_CHANGED,
                task_id=task.id,
                data={"stage": "packaging", "message": "正在打包数据集..."}
            ))
            
            dataset_dir = self.video_processor.create_dataset(
                video_name=task.video_name,
                output_name=task.prefix,
                frames_dir=frames_dir,
                annotations_dir=annotations_dir,
                visualized_dir=vis_dir,
                fps=task.fps,
                use_rag=task.use_rag
            )
            
            task.dataset_dir = str(dataset_dir)
            
            await event_bus.publish(Event(
                type=EventType.PACKAGE_COMPLETED,
                task_id=task.id,
                data={"dataset_dir": str(dataset_dir)}
            ))
            
            # ========== 完成 ==========
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            
            with self._lock:
                self._running_tasks.pop(task.id, None)
            
            await event_bus.publish(Event(
                type=EventType.TASK_COMPLETED,
                task_id=task.id,
                data={
                    "stats": task.stats.to_dict(),
                    "issues_count": len(task.issues),
                    "dataset_dir": str(dataset_dir),
                    "elapsed_seconds": self._calculate_elapsed(task),
                }
            ))
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            await event_bus.publish(Event(
                type=EventType.TASK_ERROR,
                task_id=task.id,
                data={"error": str(e)}
            ))
    
    async def _process_images(
        self, 
        task: Task, 
        image_paths: List[str],
        output_dir: Path,
        vis_dir: Path
    ):
        """处理图片列表"""
        with ThreadPoolExecutor(max_workers=self.config.workers) as executor:
            futures = {}
            
            for path in image_paths:
                # 检查是否应该停止
                with self._lock:
                    if not self._running_tasks.get(task.id, False):
                        break
                
                future = executor.submit(
                    self._process_single_sync,
                    task,
                    path,
                    output_dir,
                    vis_dir
                )
                futures[future] = path
            
            for future in as_completed(futures):
                image_path = futures[future]
                try:
                    result = future.result()
                    task.add_frame_result(result)
                    
                    # 发布帧完成事件
                    await event_bus.publish(Event(
                        type=EventType.FRAME_COMPLETED,
                        task_id=task.id,
                        data={
                            "frame": result.to_dict(),
                            "progress": task.progress,
                            "completed": task.completed_frames,
                            "total": task.total_frames,
                        }
                    ))
                    
                    # 发布统计更新
                    await event_bus.publish(Event(
                        type=EventType.STATS_UPDATE,
                        task_id=task.id,
                        data={"stats": task.stats.to_dict()}
                    ))
                    
                    # 发布问题事件
                    for issue in result.issues:
                        await event_bus.publish(Event(
                            type=EventType.ISSUE_DETECTED,
                            task_id=task.id,
                            data={"issue": issue.to_dict()}
                        ))
                        
                except Exception as e:
                    # 发布错误事件
                    await event_bus.publish(Event(
                        type=EventType.FRAME_ERROR,
                        task_id=task.id,
                        data={
                            "frame_id": Path(image_path).stem,
                            "error": str(e)
                        }
                    ))
        
        # 任务完成
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now().isoformat()
        
        with self._lock:
            self._running_tasks.pop(task.id, None)
        
        await event_bus.publish(Event(
            type=EventType.TASK_COMPLETED,
            task_id=task.id,
            data={
                "stats": task.stats.to_dict(),
                "issues_count": len(task.issues),
                "elapsed_seconds": self._calculate_elapsed(task),
            }
        ))
    
    def _process_single_sync(
        self,
        task: Task,
        image_path: str,
        output_dir: Path,
        vis_dir: Path
    ) -> FrameResult:
        """
        同步处理单张图片
        """
        frame_id = Path(image_path).stem
        start_time = time.time()
        
        try:
            # 检测
            detections = self.detector.detect(image_path)
            
            # 审查
            issues = []
            if self.config.enable_review:
                issues = self.reviewer.review(frame_id, image_path, detections)
            
            # 保存标注
            annotation = self._to_annotation_format(detections, image_path)
            json_path = output_dir / f"{frame_id}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(annotation, f, ensure_ascii=False, indent=2)
            
            # 生成可视化
            vis_path = vis_dir / f"{frame_id}_vis.jpg"
            self._visualize(image_path, detections, str(vis_path))
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            return FrameResult(
                frame_id=frame_id,
                image_path=image_path,
                detections=detections,
                issues=issues,
                elapsed_ms=elapsed_ms,
                visualized_path=str(vis_path),
            )
            
        except Exception as e:
            return FrameResult(
                frame_id=frame_id,
                image_path=image_path,
                error=str(e),
                elapsed_ms=int((time.time() - start_time) * 1000),
            )
    
    def _to_annotation_format(self, detections: List[dict], image_path: str) -> dict:
        """转换为 X-AnyLabeling 格式"""
        from ..utils import get_image_size
        
        width, height = get_image_size(image_path)
        
        shapes = []
        for det in detections:
            shapes.append({
                "label": det["label"],
                "text": det.get("label", ""),
                "points": [
                    [det["bbox"][0], det["bbox"][1]],
                    [det["bbox"][2], det["bbox"][3]]
                ],
                "group_id": None,
                "shape_type": "rectangle",
                "flags": {"category": det.get("category", "unknown")}
            })
        
        return {
            "version": "0.4.1",
            "flags": {},
            "shapes": shapes,
            "imagePath": Path(image_path).name,
            "imageData": None,
            "imageHeight": height,
            "imageWidth": width
        }
    
    def _visualize(self, image_path: str, detections: List[dict], output_path: str):
        """生成可视化图片"""
        CATEGORY_COLORS = {
            "pedestrian": (255, 0, 0),
            "vehicle": (0, 255, 0),
            "traffic_sign": (0, 100, 255),
            "construction": (255, 165, 0),
            "unknown": (128, 128, 128),
        }
        
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)
        
        for det in detections:
            bbox = det["bbox"]
            label = det["label"]
            category = det.get("category", "unknown")
            color = CATEGORY_COLORS.get(category, (128, 128, 128))
            
            # 绘制矩形框
            draw.rectangle(bbox, outline=color, width=3)
            
            # 绘制标签
            text_bbox = draw.textbbox((bbox[0], bbox[1] - 18), label)
            draw.rectangle(
                [text_bbox[0] - 2, text_bbox[1] - 2, text_bbox[2] + 2, text_bbox[3] + 2],
                fill=color
            )
            draw.text((bbox[0], bbox[1] - 18), label, fill=(255, 255, 255))
        
        img.save(output_path, "JPEG", quality=90)
    
    def _calculate_elapsed(self, task: Task) -> float:
        """计算任务耗时"""
        if task.started_at and task.completed_at:
            start = datetime.fromisoformat(task.started_at)
            end = datetime.fromisoformat(task.completed_at)
            return (end - start).total_seconds()
        return 0
    
    def stop_task(self, task_id: str):
        """停止任务"""
        with self._lock:
            self._running_tasks[task_id] = False

