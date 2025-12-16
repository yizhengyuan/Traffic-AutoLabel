"""
FastAPI 服务器

提供 REST API 和 WebSocket 实时推送。
"""

import asyncio
import json
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel

from .config import DashboardConfig
from .task_manager import TaskManager, get_task_manager
from .events import event_bus, Event, EventType
from .models import TaskStatus


# ============ Pydantic 模型 ============

class CreateTaskRequest(BaseModel):
    prefix: str
    use_rag: bool = False
    limit: Optional[int] = None
    images_dir: Optional[str] = None
    output_dir: Optional[str] = None


class CreateVideoTaskRequest(BaseModel):
    video_name: str          # 视频名称（如 D3.100f）
    output_name: str         # 输出名称（如 D3.100f3）
    fps: int = 3
    use_rag: bool = False


class TaskResponse(BaseModel):
    id: str
    prefix: str
    status: str
    total_frames: int
    completed_frames: int
    failed_frames: int
    progress: float
    issues_count: int


# ============ 应用工厂 ============

def create_app(config: DashboardConfig = None) -> FastAPI:
    """
    创建 FastAPI 应用
    
    Args:
        config: Dashboard 配置
        
    Returns:
        FastAPI 应用实例
    """
    config = config or DashboardConfig()
    
    app = FastAPI(
        title="GLM Labeling Dashboard",
        description="实时标注监控系统",
        version="0.2.0"
    )
    
    # 初始化任务管理器
    task_manager = get_task_manager(config)
    
    # 保存配置到 app.state
    app.state.config = config
    app.state.task_manager = task_manager
    
    # ============ 静态文件 ============
    
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # ============ 页面路由 ============
    
    @app.get("/", response_class=HTMLResponse)
    async def index():
        """首页"""
        html_path = static_dir / "index.html"
        if html_path.exists():
            return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
        return HTMLResponse(content=get_fallback_html())
    
    # ============ REST API ============
    
    @app.get("/api/status")
    async def get_status():
        """获取服务状态"""
        return {
            "status": "running",
            "config": {
                "workers": config.workers,
                "images_dir": config.images_dir,
                "output_dir": config.output_dir,
                "enable_review": config.enable_review,
                "review_rate": config.review_rate,
            }
        }
    
    @app.get("/api/videos")
    async def list_videos():
        """获取可用的视频列表"""
        videos = task_manager.list_videos()
        return {"videos": videos}
    
    @app.get("/api/tasks")
    async def list_tasks():
        """获取所有任务"""
        tasks = task_manager.get_all_tasks()
        return {
            "tasks": [t.to_dict() for t in tasks]
        }
    
    @app.post("/api/tasks/video")
    async def create_video_task(request: CreateVideoTaskRequest):
        """创建视频处理任务（完整流水线）"""
        try:
            task = task_manager.create_video_task(
                video_name=request.video_name,
                output_name=request.output_name,
                fps=request.fps,
                use_rag=request.use_rag,
            )
            return {"task": task.to_dict()}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/api/tasks")
    async def create_task(request: CreateTaskRequest):
        """创建新任务"""
        try:
            task = task_manager.create_task(
                prefix=request.prefix,
                use_rag=request.use_rag,
                limit=request.limit,
                images_dir=request.images_dir,
                output_dir=request.output_dir,
            )
            return {"task": task.to_dict()}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/tasks/{task_id}")
    async def get_task(task_id: str):
        """获取任务详情"""
        task = task_manager.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return {"task": task.to_dict()}
    
    @app.post("/api/tasks/{task_id}/start")
    async def start_task(task_id: str):
        """启动任务"""
        try:
            task = await task_manager.start_task(task_id)
            return {"task": task.to_dict()}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/api/tasks/{task_id}/stop")
    async def stop_task(task_id: str):
        """停止任务"""
        try:
            task = task_manager.stop_task(task_id)
            return {"task": task.to_dict()}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.delete("/api/tasks/{task_id}")
    async def delete_task(task_id: str):
        """删除任务"""
        if task_manager.delete_task(task_id):
            return {"success": True}
        raise HTTPException(status_code=404, detail="任务不存在")
    
    @app.get("/api/tasks/{task_id}/issues")
    async def get_task_issues(task_id: str):
        """获取任务问题列表"""
        task = task_manager.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return {
            "issues": [i.to_dict() for i in task.issues]
        }
    
    @app.get("/api/tasks/{task_id}/frames")
    async def get_recent_frames(task_id: str):
        """获取最近处理的帧"""
        task = task_manager.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return {
            "frames": [f.to_dict() for f in task.recent_frames[-20:]]
        }
    
    @app.get("/api/tasks/{task_id}/frames/{frame_id}")
    async def get_frame(task_id: str, frame_id: str):
        """获取单帧详情"""
        result = task_manager.get_frame_result(task_id, frame_id)
        if result is None:
            raise HTTPException(status_code=404, detail="帧不存在")
        return {"frame": result}
    
    @app.get("/api/images/{path:path}")
    async def get_image(path: str):
        """获取图片文件"""
        # 支持可视化图片和原始图片
        full_path = Path(path)
        if not full_path.is_absolute():
            # 尝试多个目录
            for base in [config.output_dir, config.images_dir, "."]:
                candidate = Path(base) / path
                if candidate.exists():
                    full_path = candidate
                    break
        
        if full_path.exists() and full_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
            return FileResponse(str(full_path))
        raise HTTPException(status_code=404, detail="图片不存在")
    
    # ============ WebSocket ============
    
    @app.websocket("/ws/live")
    async def websocket_all(websocket: WebSocket):
        """订阅所有任务的实时事件"""
        await websocket.accept()
        queue = event_bus.subscribe(task_id=None)
        
        try:
            while True:
                event = await queue.get()
                await websocket.send_json(event.to_dict())
        except WebSocketDisconnect:
            event_bus.unsubscribe(queue, task_id=None)
    
    @app.websocket("/ws/live/{task_id}")
    async def websocket_task(websocket: WebSocket, task_id: str):
        """订阅特定任务的实时事件"""
        await websocket.accept()
        queue = event_bus.subscribe(task_id=task_id)
        
        try:
            while True:
                event = await queue.get()
                await websocket.send_json(event.to_dict())
        except WebSocketDisconnect:
            event_bus.unsubscribe(queue, task_id=task_id)
    
    return app


def get_fallback_html() -> str:
    """获取备用 HTML（当静态文件不存在时）"""
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GLM Labeling Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            min-height: 100vh;
            color: #e4e4e4;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 30px;
        }
        h1 { font-size: 1.8rem; font-weight: 600; }
        h1 span { color: #00d9ff; }
        .status-badge {
            background: #00d9ff;
            color: #1a1a2e;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 24px;
            border: 1px solid rgba(255,255,255,0.08);
        }
        .card-title {
            font-size: 1rem;
            color: #888;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .task-form { display: flex; gap: 12px; flex-wrap: wrap; }
        .task-form input, .task-form select {
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.1);
            padding: 12px 16px;
            border-radius: 8px;
            color: #fff;
            font-size: 0.95rem;
        }
        .task-form input:focus { outline: none; border-color: #00d9ff; }
        .btn {
            background: linear-gradient(135deg, #00d9ff, #0099cc);
            color: #fff;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,217,255,0.3); }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
        .btn-danger { background: linear-gradient(135deg, #ff4757, #cc0000); }
        .stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
        .stat-item {
            background: rgba(0,0,0,0.2);
            padding: 16px;
            border-radius: 12px;
            text-align: center;
        }
        .stat-value { font-size: 2rem; font-weight: 700; }
        .stat-label { color: #888; font-size: 0.85rem; margin-top: 4px; }
        .stat-pedestrian .stat-value { color: #ff6b6b; }
        .stat-vehicle .stat-value { color: #51cf66; }
        .stat-traffic_sign .stat-value { color: #339af0; }
        .stat-construction .stat-value { color: #ffa94d; }
        .progress-bar {
            height: 8px;
            background: rgba(0,0,0,0.3);
            border-radius: 4px;
            overflow: hidden;
            margin: 16px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00d9ff, #51cf66);
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        .progress-text { display: flex; justify-content: space-between; font-size: 0.9rem; color: #888; }
        .preview-container {
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            overflow: hidden;
            aspect-ratio: 16/9;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .preview-container img { max-width: 100%; max-height: 100%; object-fit: contain; }
        .preview-placeholder { color: #666; font-size: 1.2rem; }
        .issues-list { max-height: 300px; overflow-y: auto; }
        .issue-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            margin-bottom: 8px;
        }
        .issue-severity {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }
        .issue-severity.warning { background: #ffa94d; }
        .issue-severity.error { background: #ff6b6b; }
        .issue-severity.info { background: #339af0; }
        .issue-frame { color: #00d9ff; font-weight: 500; }
        .issue-desc { flex: 1; color: #ccc; font-size: 0.9rem; }
        .log-container {
            background: rgba(0,0,0,0.4);
            border-radius: 8px;
            padding: 16px;
            max-height: 200px;
            overflow-y: auto;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.85rem;
        }
        .log-entry { margin-bottom: 4px; }
        .log-time { color: #666; }
        .log-success { color: #51cf66; }
        .log-error { color: #ff6b6b; }
        .task-list { margin-top: 16px; }
        .task-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            margin-bottom: 8px;
        }
        .task-info { flex: 1; }
        .task-prefix { font-weight: 600; font-size: 1.1rem; }
        .task-meta { color: #888; font-size: 0.85rem; margin-top: 4px; }
        .task-actions { display: flex; gap: 8px; }
        .task-actions .btn { padding: 8px 16px; font-size: 0.85rem; }
        @media (max-width: 1024px) {
            .grid { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏷️ <span>GLM</span> Labeling Dashboard</h1>
            <span class="status-badge" id="connection-status">连接中...</span>
        </header>

        <div class="grid">
            <div class="card">
                <div class="card-title">📋 创建任务</div>
                <form class="task-form" id="create-form">
                    <input type="text" id="prefix" placeholder="图片前缀 (如 D1, D2)" required style="flex:1;">
                    <input type="number" id="limit" placeholder="数量限制 (可选)" min="1">
                    <label style="display:flex;align-items:center;gap:6px;">
                        <input type="checkbox" id="use-rag"> RAG
                    </label>
                    <button type="submit" class="btn">创建任务</button>
                </form>
                <div class="task-list" id="task-list"></div>
            </div>

            <div class="card">
                <div class="card-title">📊 实时统计</div>
                <div class="stats-grid">
                    <div class="stat-item stat-pedestrian">
                        <div class="stat-value" id="stat-pedestrian">0</div>
                        <div class="stat-label">🔴 行人</div>
                    </div>
                    <div class="stat-item stat-vehicle">
                        <div class="stat-value" id="stat-vehicle">0</div>
                        <div class="stat-label">🟢 车辆</div>
                    </div>
                    <div class="stat-item stat-traffic_sign">
                        <div class="stat-value" id="stat-traffic_sign">0</div>
                        <div class="stat-label">🔵 交通标志</div>
                    </div>
                    <div class="stat-item stat-construction">
                        <div class="stat-value" id="stat-construction">0</div>
                        <div class="stat-label">🟠 施工标志</div>
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
                </div>
                <div class="progress-text">
                    <span id="progress-text">等待任务...</span>
                    <span id="progress-percent">0%</span>
                </div>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <div class="card-title">📸 当前帧预览</div>
                <div class="preview-container" id="preview">
                    <span class="preview-placeholder">等待处理...</span>
                </div>
                <div style="margin-top:12px;color:#888;font-size:0.9rem;" id="frame-info"></div>
            </div>

            <div class="card">
                <div class="card-title">⚠️ 问题列表 (<span id="issues-count">0</span>)</div>
                <div class="issues-list" id="issues-list">
                    <div style="color:#666;text-align:center;padding:40px;">暂无问题</div>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-title">📜 处理日志</div>
            <div class="log-container" id="log-container"></div>
        </div>
    </div>

    <script>
        const API_BASE = '';
        let ws = null;
        let currentTaskId = null;
        let stats = { pedestrian: 0, vehicle: 0, traffic_sign: 0, construction: 0 };
        let issues = [];

        // WebSocket 连接
        function connectWebSocket() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws/live`);
            
            ws.onopen = () => {
                document.getElementById('connection-status').textContent = '已连接';
                document.getElementById('connection-status').style.background = '#51cf66';
            };
            
            ws.onclose = () => {
                document.getElementById('connection-status').textContent = '已断开';
                document.getElementById('connection-status').style.background = '#ff6b6b';
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onmessage = (e) => {
                const event = JSON.parse(e.data);
                handleEvent(event);
            };
        }

        function handleEvent(event) {
            const time = new Date().toLocaleTimeString();
            
            switch(event.type) {
                case 'frame_completed':
                    const frame = event.data.frame;
                    addLog(`✅ ${frame.frame_id} - ${frame.detections.length} objects (${frame.elapsed_ms}ms)`, 'success');
                    updateProgress(event.data.progress, event.data.completed, event.data.total);
                    if (frame.visualized_path) {
                        updatePreview(frame.visualized_path, frame.frame_id, frame.detections.length, frame.elapsed_ms);
                    }
                    break;
                    
                case 'frame_error':
                    addLog(`❌ ${event.data.frame_id} - ${event.data.error}`, 'error');
                    break;
                    
                case 'stats_update':
                    updateStats(event.data.stats);
                    break;
                    
                case 'issue_detected':
                    addIssue(event.data.issue);
                    break;
                    
                case 'task_completed':
                    addLog(`🎉 任务完成！共检测 ${Object.values(event.data.stats).reduce((a,b)=>a+b,0)} 个物体`, 'success');
                    loadTasks();
                    break;
                    
                case 'task_started':
                    addLog(`🚀 任务开始，共 ${event.data.total_frames} 张图片`, 'success');
                    break;
            }
        }

        function updateStats(newStats) {
            stats = {...stats, ...newStats};
            for (const [key, value] of Object.entries(stats)) {
                const el = document.getElementById(`stat-${key}`);
                if (el) el.textContent = value;
            }
        }

        function updateProgress(progress, completed, total) {
            const percent = Math.round(progress * 100);
            document.getElementById('progress-fill').style.width = `${percent}%`;
            document.getElementById('progress-percent').textContent = `${percent}%`;
            document.getElementById('progress-text').textContent = `已处理: ${completed}/${total}`;
        }

        function updatePreview(path, frameId, objCount, elapsed) {
            const preview = document.getElementById('preview');
            // 转换路径为 API URL
            const imgUrl = `/api/images/${path}`;
            preview.innerHTML = `<img src="${imgUrl}" alt="${frameId}" onerror="this.parentElement.innerHTML='<span class=preview-placeholder>加载失败</span>'">`;
            document.getElementById('frame-info').textContent = `${frameId} | ${objCount} 个物体 | ${elapsed}ms`;
        }

        function addLog(message, type = '') {
            const container = document.getElementById('log-container');
            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = `log-entry ${type ? 'log-' + type : ''}`;
            entry.innerHTML = `<span class="log-time">[${time}]</span> ${message}`;
            container.appendChild(entry);
            container.scrollTop = container.scrollHeight;
            
            // 限制日志数量
            while (container.children.length > 100) {
                container.removeChild(container.firstChild);
            }
        }

        function addIssue(issue) {
            issues.unshift(issue);
            document.getElementById('issues-count').textContent = issues.length;
            
            const list = document.getElementById('issues-list');
            if (issues.length === 1) {
                list.innerHTML = '';
            }
            
            const item = document.createElement('div');
            item.className = 'issue-item';
            item.innerHTML = `
                <span class="issue-severity ${issue.severity}"></span>
                <span class="issue-frame">${issue.frame_id}</span>
                <span class="issue-desc">${issue.description}</span>
            `;
            list.insertBefore(item, list.firstChild);
            
            // 限制显示数量
            while (list.children.length > 50) {
                list.removeChild(list.lastChild);
            }
        }

        // API 调用
        async function loadTasks() {
            try {
                const res = await fetch('/api/tasks');
                const data = await res.json();
                renderTasks(data.tasks);
            } catch (e) {
                console.error('加载任务失败:', e);
            }
        }

        function renderTasks(tasks) {
            const list = document.getElementById('task-list');
            if (tasks.length === 0) {
                list.innerHTML = '<div style="color:#666;text-align:center;padding:20px;">暂无任务</div>';
                return;
            }
            
            list.innerHTML = tasks.map(task => `
                <div class="task-item">
                    <div class="task-info">
                        <div class="task-prefix">${task.prefix}</div>
                        <div class="task-meta">${task.status} | ${task.completed_frames}/${task.total_frames} | 问题: ${task.issues_count}</div>
                    </div>
                    <div class="task-actions">
                        ${task.status === 'pending' ? `<button class="btn" onclick="startTask('${task.id}')">开始</button>` : ''}
                        ${task.status === 'running' ? `<button class="btn btn-danger" onclick="stopTask('${task.id}')">停止</button>` : ''}
                        <button class="btn btn-danger" onclick="deleteTask('${task.id}')" style="background:#666;">删除</button>
                    </div>
                </div>
            `).join('');
        }

        async function createTask(e) {
            e.preventDefault();
            const prefix = document.getElementById('prefix').value;
            const limit = document.getElementById('limit').value;
            const useRag = document.getElementById('use-rag').checked;
            
            try {
                const res = await fetch('/api/tasks', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ prefix, limit: limit ? parseInt(limit) : null, use_rag: useRag })
                });
                
                if (!res.ok) {
                    const err = await res.json();
                    alert(err.detail || '创建失败');
                    return;
                }
                
                const data = await res.json();
                currentTaskId = data.task.id;
                addLog(`📋 创建任务: ${prefix} (${data.task.total_frames} 张图片)`, 'success');
                loadTasks();
                document.getElementById('prefix').value = '';
                document.getElementById('limit').value = '';
            } catch (e) {
                alert('创建任务失败: ' + e.message);
            }
        }

        async function startTask(taskId) {
            try {
                const res = await fetch(`/api/tasks/${taskId}/start`, { method: 'POST' });
                if (!res.ok) {
                    const err = await res.json();
                    alert(err.detail || '启动失败');
                    return;
                }
                currentTaskId = taskId;
                loadTasks();
            } catch (e) {
                alert('启动任务失败: ' + e.message);
            }
        }

        async function stopTask(taskId) {
            try {
                await fetch(`/api/tasks/${taskId}/stop`, { method: 'POST' });
                loadTasks();
            } catch (e) {
                alert('停止任务失败: ' + e.message);
            }
        }

        async function deleteTask(taskId) {
            if (!confirm('确定删除此任务？')) return;
            try {
                await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
                loadTasks();
            } catch (e) {
                alert('删除任务失败: ' + e.message);
            }
        }

        // 初始化
        document.getElementById('create-form').addEventListener('submit', createTask);
        connectWebSocket();
        loadTasks();
    </script>
</body>
</html>"""

