"""
数据模型定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    EXTRACTING = "extracting"  # 正在抽帧
    RUNNING = "running"        # 正在标注
    VISUALIZING = "visualizing"  # 正在生成可视化
    PACKAGING = "packaging"    # 正在打包
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskMode(Enum):
    """任务模式"""
    IMAGES = "images"    # 处理已有图片
    VIDEO = "video"      # 从视频开始完整流水线


class IssueSeverity(Enum):
    """问题严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class IssueType(Enum):
    """问题类型"""
    BBOX_TOO_SMALL = "bbox_too_small"
    BBOX_TOO_LARGE = "bbox_too_large"
    BBOX_OVERLAP = "bbox_overlap"
    UNKNOWN_LABEL = "unknown_label"
    TEMPORAL_DISAPPEAR = "temporal_disappear"
    TEMPORAL_APPEAR = "temporal_appear"
    TEMPORAL_LABEL_CHANGE = "temporal_label_change"
    TEMPORAL_POSITION_JUMP = "temporal_position_jump"
    MISSING_DETECTION = "missing_detection"
    WRONG_LABEL = "wrong_label"


@dataclass
class Issue:
    """标注问题"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    frame_id: str = ""
    issue_type: IssueType = IssueType.UNKNOWN_LABEL
    severity: IssueSeverity = IssueSeverity.WARNING
    description: str = ""
    suggestion: str = ""
    detected_by: str = "rule"  # rule / ai_scan / ai_deep
    bbox: Optional[List[int]] = None
    status: str = "open"  # open / resolved / ignored
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "frame_id": self.frame_id,
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "suggestion": self.suggestion,
            "detected_by": self.detected_by,
            "bbox": self.bbox,
            "status": self.status,
            "created_at": self.created_at,
        }


@dataclass
class FrameResult:
    """单帧处理结果"""
    frame_id: str
    image_path: str
    detections: List[Dict[str, Any]] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)
    elapsed_ms: int = 0
    visualized_path: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "image_path": self.image_path,
            "detections": self.detections,
            "issues": [i.to_dict() for i in self.issues],
            "elapsed_ms": self.elapsed_ms,
            "visualized_path": self.visualized_path,
            "error": self.error,
        }


@dataclass
class TaskStats:
    """任务统计"""
    pedestrian: int = 0
    vehicle: int = 0
    traffic_sign: int = 0
    construction: int = 0
    unknown: int = 0
    
    # 细分标签统计
    labels: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "pedestrian": self.pedestrian,
            "vehicle": self.vehicle,
            "traffic_sign": self.traffic_sign,
            "construction": self.construction,
            "unknown": self.unknown,
            "labels": self.labels,
        }
    
    def increment(self, category: str, label: str = None):
        """增加计数"""
        # 主类别计数
        if hasattr(self, category) and category != "labels":
            setattr(self, category, getattr(self, category) + 1)
        else:
            self.unknown += 1
        
        # 细分标签计数
        if label:
            self.labels[label] = self.labels.get(label, 0) + 1


@dataclass
class Task:
    """标注任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    prefix: str = ""
    status: TaskStatus = TaskStatus.PENDING
    mode: TaskMode = TaskMode.IMAGES
    
    # 视频相关（仅 VIDEO 模式）
    video_name: str = ""
    video_path: str = ""
    fps: int = 3
    
    # 进度
    total_frames: int = 0
    completed_frames: int = 0
    failed_frames: int = 0
    
    # 各阶段进度
    extract_progress: float = 0.0
    label_progress: float = 0.0
    visualize_progress: float = 0.0
    
    # 统计
    stats: TaskStats = field(default_factory=TaskStats)
    
    # 问题列表
    issues: List[Issue] = field(default_factory=list)
    
    # 时间
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # 配置
    use_rag: bool = False
    workers: int = 5
    images_dir: str = ""
    output_dir: str = ""
    frames_dir: str = ""  # 抽帧输出目录
    annotations_dir: str = ""
    visualized_dir: str = ""
    dataset_dir: str = ""
    
    # 帧结果缓存（最近 N 帧）
    recent_frames: List[FrameResult] = field(default_factory=list)
    max_recent_frames: int = 50
    
    @property
    def progress(self) -> float:
        """总进度百分比"""
        if self.mode == TaskMode.IMAGES:
            if self.total_frames == 0:
                return 0
            return (self.completed_frames + self.failed_frames) / self.total_frames
        else:
            # VIDEO 模式：抽帧 20% + 标注 60% + 可视化 15% + 打包 5%
            return (
                self.extract_progress * 0.2 +
                self.label_progress * 0.6 +
                self.visualize_progress * 0.15 +
                (1.0 if self.status == TaskStatus.COMPLETED else 0) * 0.05
            )
    
    @property
    def current_stage(self) -> str:
        """当前阶段"""
        stage_map = {
            TaskStatus.PENDING: "等待开始",
            TaskStatus.EXTRACTING: "抽帧中",
            TaskStatus.RUNNING: "标注中",
            TaskStatus.VISUALIZING: "生成可视化",
            TaskStatus.PACKAGING: "打包数据集",
            TaskStatus.COMPLETED: "已完成",
            TaskStatus.FAILED: "失败",
            TaskStatus.PAUSED: "已暂停",
        }
        return stage_map.get(self.status, "未知")
    
    def add_frame_result(self, result: FrameResult):
        """添加帧结果"""
        self.recent_frames.append(result)
        if len(self.recent_frames) > self.max_recent_frames:
            self.recent_frames.pop(0)
        
        # 更新统计
        for det in result.detections:
            category = det.get("category", "unknown")
            label = det.get("label", "unknown")
            self.stats.increment(category, label)
        
        # 添加问题
        self.issues.extend(result.issues)
        
        # 更新计数
        if result.error:
            self.failed_frames += 1
        else:
            self.completed_frames += 1
        
        # 更新标注进度
        if self.total_frames > 0:
            self.label_progress = (self.completed_frames + self.failed_frames) / self.total_frames
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prefix": self.prefix,
            "status": self.status.value,
            "mode": self.mode.value,
            "video_name": self.video_name,
            "fps": self.fps,
            "total_frames": self.total_frames,
            "completed_frames": self.completed_frames,
            "failed_frames": self.failed_frames,
            "progress": self.progress,
            "current_stage": self.current_stage,
            "extract_progress": self.extract_progress,
            "label_progress": self.label_progress,
            "visualize_progress": self.visualize_progress,
            "stats": self.stats.to_dict(),
            "issues_count": len(self.issues),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "use_rag": self.use_rag,
            "workers": self.workers,
            "dataset_dir": self.dataset_dir,
        }

