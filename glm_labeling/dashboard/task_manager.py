"""
任务管理器

管理多个标注任务的生命周期。
支持两种模式：IMAGES（处理已有图片）和 VIDEO（完整流水线）
"""

import threading
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .models import Task, TaskStatus, TaskMode, Issue
from .config import DashboardConfig
from .engine import LabelingEngine
from .video_processor import VideoProcessor


class TaskManager:
    """
    任务管理器
    
    单例模式，管理所有标注任务。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config: DashboardConfig = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: DashboardConfig = None):
        if self._initialized:
            return
        
        self.config = config or DashboardConfig()
        self.engine = LabelingEngine(self.config)
        self.video_processor = VideoProcessor()
        self._tasks: Dict[str, Task] = {}
        self._lock = threading.Lock()
        self._initialized = True
    
    def list_videos(self) -> List[str]:
        """列出可用的视频文件"""
        return self.video_processor.list_videos()
    
    def create_task(
        self,
        prefix: str,
        use_rag: bool = False,
        limit: Optional[int] = None,
        images_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
    ) -> Task:
        """
        创建新任务
        
        Args:
            prefix: 图片前缀
            use_rag: 是否使用 RAG
            limit: 限制数量
            images_dir: 图片目录
            output_dir: 输出目录
            
        Returns:
            创建的任务对象
        """
        images_dir = images_dir or self.config.images_dir
        
        # 查找图片
        images_path = Path(images_dir)
        patterns = [f"{prefix}_*.jpg", f"{prefix}_*.png", f"{prefix}*.jpg"]
        image_files = []
        for pattern in patterns:
            image_files.extend(images_path.glob(pattern))
        image_files = sorted(set(image_files))
        
        if limit:
            image_files = image_files[:limit]
        
        if not image_files:
            raise ValueError(f"没有找到 {prefix} 开头的图片在 {images_dir}")
        
        # 创建任务
        rag_suffix = "_rag" if use_rag else ""
        task_output_dir = output_dir or f"{self.config.output_dir}/{prefix.lower()}_annotations{rag_suffix}"
        
        task = Task(
            prefix=prefix,
            use_rag=use_rag,
            workers=self.config.workers,
            images_dir=images_dir,
            output_dir=task_output_dir,
            total_frames=len(image_files),
        )
        
        # 保存图片路径到任务（用于后续启动）
        task._image_paths = [str(p) for p in image_files]
        
        with self._lock:
            self._tasks[task.id] = task
        
        return task
    
    def create_video_task(
        self,
        video_name: str,
        output_name: str,
        fps: int = 3,
        use_rag: bool = False,
    ) -> Task:
        """
        创建视频处理任务（完整流水线）
        
        Args:
            video_name: 视频名称（如 D3.100f）
            output_name: 输出数据集名称（如 D3.100f3）
            fps: 抽帧率
            use_rag: 是否使用 RAG
            
        Returns:
            创建的任务对象
        """
        # 检查视频是否存在
        video_path = self.video_processor.get_video_path(video_name)
        if not video_path:
            raise ValueError(f"视频不存在: {video_name}")
        
        # 创建任务
        task = Task(
            prefix=output_name,
            mode=TaskMode.VIDEO,
            video_name=video_name,
            video_path=str(video_path),
            fps=fps,
            use_rag=use_rag,
            workers=self.config.workers,
            images_dir="",  # 视频模式不需要
            output_dir=f"{self.config.output_dir}/{output_name.lower()}_annotations",
            frames_dir=f"temp_frames/{output_name}",
            annotations_dir=f"{self.config.output_dir}/{output_name.lower()}_annotations",
            visualized_dir=f"{self.config.output_dir}/{output_name.lower()}_visualized",
        )
        
        with self._lock:
            self._tasks[task.id] = task
        
        return task
    
    async def start_task(self, task_id: str) -> Task:
        """启动任务"""
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"任务不存在: {task_id}")
        
        if task.status in [TaskStatus.RUNNING, TaskStatus.EXTRACTING, TaskStatus.VISUALIZING, TaskStatus.PACKAGING]:
            raise ValueError(f"任务已在运行: {task_id}")
        
        if task.mode == TaskMode.VIDEO:
            # 视频模式：不需要预先的图片路径
            await self.engine.start_task(task)
        else:
            # 图片模式
            image_paths = getattr(task, '_image_paths', [])
            if not image_paths:
                raise ValueError(f"任务没有图片: {task_id}")
            await self.engine.start_task(task, image_paths)
        
        return task
    
    def stop_task(self, task_id: str) -> Task:
        """停止任务"""
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"任务不存在: {task_id}")
        
        self.engine.stop_task(task_id)
        task.status = TaskStatus.PAUSED
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        with self._lock:
            return self._tasks.get(task_id)
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        with self._lock:
            return list(self._tasks.values())
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        with self._lock:
            if task_id in self._tasks:
                task = self._tasks[task_id]
                if task.status == TaskStatus.RUNNING:
                    self.engine.stop_task(task_id)
                del self._tasks[task_id]
                return True
        return False
    
    def get_task_issues(self, task_id: str) -> List[Issue]:
        """获取任务的所有问题"""
        task = self.get_task(task_id)
        if task:
            return task.issues
        return []
    
    def get_frame_result(self, task_id: str, frame_id: str) -> Optional[dict]:
        """获取单帧结果"""
        task = self.get_task(task_id)
        if task:
            for frame in task.recent_frames:
                if frame.frame_id == frame_id:
                    return frame.to_dict()
        return None


# 全局任务管理器实例（延迟初始化）
_task_manager: Optional[TaskManager] = None


def get_task_manager(config: DashboardConfig = None) -> TaskManager:
    """获取任务管理器实例"""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager(config)
    return _task_manager

