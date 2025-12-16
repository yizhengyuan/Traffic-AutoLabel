// ============ 全局变量 ============
const elements = {
    // 任务列表
    taskList: document.getElementById('task-list'),
    
    // 输入框
    videoName: document.getElementById('video-name'),
    outputName: document.getElementById('output-name'),
    
    // 统计
    totalLabelsCount: document.getElementById('total-labels-count'),
    
    // 进度
    progressFill: document.getElementById('progress-fill'),
    progressText: document.getElementById('progress-text'),
    progressPercent: document.getElementById('progress-percent'),
    
    // 预览
    preview: document.getElementById('preview'),
    frameInfo: document.getElementById('frame-info'),
    
    // 问题
    issuesCount: document.getElementById('issues-count'),
    issuesList: document.getElementById('issues-list'),
    
    // 日志
    logContainer: document.getElementById('log-container')
};

// 默认只支持视频模式
const currentMode = 'video';

// ============ 状态管理 ============
const state = {
    ws: null,
    currentTaskId: null,
    stats: {
        pedestrian: 0,
        vehicle: 0,
        traffic_sign: 0,
        construction: 0,
        labels: {}
    },
    issues: [],
    reconnectAttempts: 0,
    maxReconnectAttempts: 10
};

// ============ 工具函数 ============
function addLog(message, type = 'info') {
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;
    
    const time = new Date().toLocaleTimeString();
    entry.innerHTML = `<span class="log-time">[${time}]</span> ${message}`;
    
    elements.logContainer.appendChild(entry);
    elements.logContainer.scrollTop = elements.logContainer.scrollHeight;
}

function clearLogs() {
    elements.logContainer.innerHTML = '';
}

function getStatusText(status) {
    const map = {
        'pending': '等待中',
        'running': '运行中',
        'completed': '已完成',
        'failed': '失败',
        'extracting': '抽帧中...',
        'visualizing': '可视化...',
        'packaging': '打包中...'
    };
    return map[status] || status;
}

// ============ API 调用 ============
async function apiCall(method, path, body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    const response = await fetch(path, options);
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }
    
    return response.json();
}

async function loadTasks() {
    try {
        const data = await apiCall('GET', '/api/tasks');
        renderTasks(data.tasks);
    } catch (e) {
        console.error('加载任务失败:', e);
        addLog(`❌ 加载任务失败: ${e.message}`, 'error');
    }
}

function renderTasks(tasks) {
    if (tasks.length === 0) {
        elements.taskList.innerHTML = '<div class="empty-state">暂无任务，请创建新任务</div>';
        return;
    }
    
    elements.taskList.innerHTML = tasks.map(task => {
        const isRunning = ['running', 'extracting', 'visualizing', 'packaging'].includes(task.status);
        const modeIcon = task.mode === 'video' ? '🎬' : '🖼️';
        const progressPercent = Math.round(task.progress * 100);
        
        return `
        <div class="task-item">
            <div class="task-info">
                <div class="task-prefix">${modeIcon} ${task.prefix}</div>
                <div class="task-meta">
                    <span class="task-status ${task.status}">${task.current_stage || getStatusText(task.status)}</span>
                    ${task.total_frames > 0 ? `${task.completed_frames}/${task.total_frames} 帧` : ''} 
                    ${progressPercent > 0 ? `| ${progressPercent}%` : ''}
                    ${task.issues_count > 0 ? `| ⚠️ ${task.issues_count}` : ''}
                    ${task.dataset_dir ? `| 📦 已打包` : ''}
                </div>
            </div>
            <div class="task-actions">
                ${task.status === 'pending' ? `<button class="btn btn-primary" onclick="startTask('${task.id}')">开始</button>` : ''}
                ${isRunning ? `<button class="btn btn-danger" onclick="stopTask('${task.id}')">停止</button>` : ''}
                <button class="btn btn-secondary" onclick="deleteTask('${task.id}')">删除</button>
            </div>
        </div>
        `;
    }).join('');
}

// ============ 统一处理开始任务 ============
async function handleStart() {
    await createVideoTask();
}
window.handleStart = handleStart;

// ============ 视频任务 ============
async function loadVideos() {
    try {
        const data = await apiCall('GET', '/api/videos');
        const select = elements.videoName;
        
        if (select) {
            select.innerHTML = '<option value="">选择视频...</option>' + 
                data.videos.map(v => {
                    const name = typeof v === 'object' ? v.name : v;
                    const label = typeof v === 'object' ? `${v.name} (${v.size_str})` : v;
                    return `<option value="${name}">${label}</option>`;
                }).join('');
        }
            
    } catch (e) {
        addLog(`❌ 加载视频列表失败: ${e.message}`, 'error');
    }
}

async function createVideoTask() {
    const videoName = elements.videoName.value;
    const outputName = elements.outputName.value.trim();
    
    // 固定默认值
    const fps = 3;
    const useRag = false;
    
    if (!videoName) {
        alert('请选择视频');
        return;
    }
    if (!outputName) {
        alert('请输入输出名称');
        return;
    }
    
    try {
        const data = await apiCall('POST', '/api/tasks/video', {
            video_name: videoName,
            output_name: outputName,
            fps: fps,
            use_rag: useRag
        });
        
        state.currentTaskId = data.task.id;
        addLog(`🎬 创建视频任务: ${videoName} → ${outputName}`, 'success');
        
        // 清空表单
        elements.videoName.value = '';
        elements.outputName.value = '';
        
        loadTasks();
    } catch (e) {
        alert('创建任务失败: ' + e.message);
        addLog(`❌ 创建任务失败: ${e.message}`, 'error');
    }
}

async function startTask(taskId) {
    try {
        await apiCall('POST', `/api/tasks/${taskId}/start`);
        state.currentTaskId = taskId;
        
        // 重置统计
        state.stats = { pedestrian: 0, vehicle: 0, traffic_sign: 0, construction: 0, labels: {} };
        updateStats(state.stats);
        
        // 重置问题
        state.issues = [];
        elements.issuesCount.textContent = '0';
        elements.issuesList.innerHTML = '<div class="empty-state">暂无问题</div>';
        
        loadTasks();
    } catch (e) {
        alert('启动任务失败: ' + e.message);
    }
}

async function stopTask(taskId) {
    try {
        await apiCall('POST', `/api/tasks/${taskId}/stop`);
        addLog(`🛑 任务已停止: ${taskId}`, 'info');
        loadTasks();
    } catch (e) {
        alert('停止任务失败: ' + e.message);
    }
}

async function deleteTask(taskId) {
    if (!confirm('确定要删除这个任务吗？相关文件将被清理。')) return;
    
    try {
        await apiCall('DELETE', `/api/tasks/${taskId}`);
        addLog(`🗑️ 任务已删除: ${taskId}`, 'info');
        loadTasks();
    } catch (e) {
        alert('删除任务失败: ' + e.message);
    }
}

// ============ UI 更新 ============
function updateStats(newStats) {
    state.stats = { ...state.stats, ...newStats };
    
    // 计算总标签数
    let total = 0;
    if (state.stats.labels) {
        total = Object.values(state.stats.labels).reduce((a, b) => a + b, 0);
    }
    
    if (elements.totalLabelsCount) {
        elements.totalLabelsCount.textContent = `总计: ${total}`;
    }
    
    // 更新细分标签列表
    updateLabels(state.stats.labels || {});
}

function updateLabels(labels) {
    const container = document.getElementById('labels-list');
    
    if (!labels || Object.keys(labels).length === 0) {
        container.innerHTML = '<div class="empty-state-small">暂无数据</div>';
        return;
    }
    
    // 按数量降序排列
    const sorted = Object.entries(labels).sort((a, b) => b[1] - a[1]);
    
    container.innerHTML = sorted.map(([label, count]) => `
        <div class="label-tag">
            <span class="label-name" title="${label}">${label}</span>
            <span class="label-count">${count}</span>
        </div>
    `).join('');
}

function updateProgress(progress, completed, total, stage = null) {
    const percent = Math.round(progress * 100);
    elements.progressFill.style.width = `${percent}%`;
    elements.progressPercent.textContent = `${percent}%`;
    
    if (stage) {
        elements.progressText.textContent = stage;
    } else if (total > 0) {
        elements.progressText.textContent = `已处理: ${completed}/${total}`;
    }
}

function updatePreview(path, frameId, objCount, elapsed) {
    const imgUrl = `/api/images/${encodeURIComponent(path)}`;
    elements.preview.innerHTML = `<img src="${imgUrl}" alt="${frameId}" onerror="this.parentElement.innerHTML='<span class=\\'preview-placeholder\\'>加载失败</span>'">`;
    
    elements.frameInfo.innerHTML = `
        <div>帧ID: ${frameId}</div>
        <div>检测目标: ${objCount}</div>
        <div>耗时: ${elapsed.toFixed(2)}s</div>
    `;
}

function renderIssues(newIssues) {
    if (newIssues && newIssues.length > 0) {
        state.issues.push(...newIssues);
        // 只保留最近 100 条
        if (state.issues.length > 100) {
            state.issues = state.issues.slice(-100);
        }
    }
    
    elements.issuesCount.textContent = state.issues.length;
    
    if (state.issues.length === 0) {
        elements.issuesList.innerHTML = '<div class="empty-state">暂无问题</div>';
        return;
    }
    
    // 倒序显示，最新的在上面
    const listHtml = [...state.issues].reverse().map(issue => `
        <div class="issue-item">
            <div class="issue-severity ${issue.severity}"></div>
            <div class="issue-content">
                <div class="issue-frame">Frame ${issue.frame_id}</div>
                <div class="issue-desc">${issue.description}</div>
            </div>
        </div>
    `).join('');
    
    elements.issuesList.innerHTML = listHtml;
}

// ============ WebSocket ============
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/live`;
    
    console.log(`Connecting to WebSocket: ${wsUrl}`);
    state.ws = new WebSocket(wsUrl);
    
    state.ws.onopen = () => {
        console.log('WebSocket connected');
        document.getElementById('connection-status').textContent = '已连接';
        document.getElementById('connection-status').className = 'status-badge connected';
        state.reconnectAttempts = 0;
        addLog('⚡ WebSocket 已连接', 'success');
    };
    
    state.ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
        }
    };
    
    state.ws.onclose = () => {
        console.log('WebSocket disconnected');
        document.getElementById('connection-status').textContent = '已断开';
        document.getElementById('connection-status').className = 'status-badge disconnected';
        
        // 尝试重连
        if (state.reconnectAttempts < state.maxReconnectAttempts) {
            state.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(1.5, state.reconnectAttempts), 10000);
            addLog(`⚠️ 连接断开，${delay/1000}秒后尝试重连...`, 'warning');
            setTimeout(connectWebSocket, delay);
        } else {
            addLog('❌ 连接失败，请刷新页面重试', 'error');
        }
    };
    
    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

function handleWebSocketMessage(data) {
    // 处理不同类型的事件
    switch (data.type) {
        case 'frame_processed':
            updateStats(data.data.stats);
            updateProgress(data.data.progress, data.data.completed, data.data.total);
            updatePreview(data.data.image_path, data.data.frame_id, data.data.detections_count, data.data.processing_time);
            if (data.data.issues && data.data.issues.length > 0) {
                renderIssues(data.data.issues);
            }
            break;
            
        case 'task_complete':
            addLog(`✅ 任务完成！总耗时: ${data.data.total_time.toFixed(1)}s`, 'success');
            loadTasks(); // 刷新任务状态
            break;
            
        case 'task_failed':
            addLog(`❌ 任务失败: ${data.data.error}`, 'error');
            loadTasks();
            break;
            
        case 'stage_update':
            // 视频流水线阶段更新
            const stageName = data.data.stage_name; // e.g., "extracting", "labeling"
            const stageProgress = data.data.progress;
            updateProgress(stageProgress, 0, 0, getStatusText(stageName));
            if (stageProgress >= 1.0) {
                 addLog(`✅ 阶段完成: ${getStatusText(stageName)}`, 'success');
            }
            break;
            
        case 'log':
            addLog(data.data.message, data.data.level);
            break;
            
        default:
            console.log('Unknown event type:', data.type);
    }
}

// ============ 初始化 ============
function init() {
    // 连接 WebSocket
    connectWebSocket();
    
    // 加载视频列表
    loadVideos();
    
    // 加载任务列表
    loadTasks();
    
    // 定期刷新任务列表
    setInterval(loadTasks, 10000);
    
    addLog('🎯 Dashboard 已就绪（专注视频模式）', 'info');
}

// 启动应用
document.addEventListener('DOMContentLoaded', init);

// 暴露全局函数供 HTML 调用
window.startTask = startTask;
window.stopTask = stopTask;
window.deleteTask = deleteTask;
