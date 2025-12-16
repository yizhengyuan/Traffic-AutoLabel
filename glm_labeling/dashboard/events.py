"""
事件总线模块

用于发布和订阅标注事件，支持 WebSocket 实时推送。
"""

import asyncio
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import threading


class EventType(Enum):
    """事件类型"""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_ERROR = "task_error"
    
    # 视频处理阶段
    STAGE_CHANGED = "stage_changed"
    EXTRACT_PROGRESS = "extract_progress"
    EXTRACT_COMPLETED = "extract_completed"
    VISUALIZE_PROGRESS = "visualize_progress"
    VISUALIZE_COMPLETED = "visualize_completed"
    PACKAGE_COMPLETED = "package_completed"
    
    FRAME_STARTED = "frame_started"
    FRAME_COMPLETED = "frame_completed"
    FRAME_ERROR = "frame_error"
    
    ISSUE_DETECTED = "issue_detected"
    STATS_UPDATE = "stats_update"


@dataclass
class Event:
    """基础事件"""
    type: EventType
    task_id: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "data": self.data
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class EventBus:
    """
    事件总线
    
    支持多任务、多订阅者的事件发布订阅机制。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # task_id -> set of asyncio.Queue
        self._subscribers: Dict[str, Set[asyncio.Queue]] = {}
        # 全局订阅者（订阅所有任务）
        self._global_subscribers: Set[asyncio.Queue] = set()
        self._lock = threading.Lock()
        self._initialized = True
    
    def subscribe(self, task_id: Optional[str] = None) -> asyncio.Queue:
        """
        订阅事件
        
        Args:
            task_id: 任务ID，None 表示订阅所有任务
            
        Returns:
            事件队列
        """
        queue = asyncio.Queue()
        
        with self._lock:
            if task_id is None:
                self._global_subscribers.add(queue)
            else:
                if task_id not in self._subscribers:
                    self._subscribers[task_id] = set()
                self._subscribers[task_id].add(queue)
        
        return queue
    
    def unsubscribe(self, queue: asyncio.Queue, task_id: Optional[str] = None):
        """取消订阅"""
        with self._lock:
            if task_id is None:
                self._global_subscribers.discard(queue)
            elif task_id in self._subscribers:
                self._subscribers[task_id].discard(queue)
    
    async def publish(self, event: Event):
        """
        发布事件
        
        Args:
            event: 事件对象
        """
        # 发送给任务订阅者
        with self._lock:
            task_subscribers = self._subscribers.get(event.task_id, set()).copy()
            global_subscribers = self._global_subscribers.copy()
        
        all_subscribers = task_subscribers | global_subscribers
        
        for queue in all_subscribers:
            try:
                await queue.put(event)
            except Exception:
                pass  # 忽略发送失败
    
    def publish_sync(self, event: Event):
        """
        同步发布事件（用于非异步上下文）
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.publish(event))
            else:
                loop.run_until_complete(self.publish(event))
        except RuntimeError:
            # 没有事件循环，创建新的
            asyncio.run(self.publish(event))
    
    def clear_task(self, task_id: str):
        """清理任务的所有订阅者"""
        with self._lock:
            if task_id in self._subscribers:
                del self._subscribers[task_id]


# 全局事件总线实例
event_bus = EventBus()

