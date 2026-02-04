// TrendRadar Web UI - 主脚本

// Toast 提示
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = 'toast show ' + type;

    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

// 运行爬虫
function runCrawler() {
    const modal = document.getElementById('run-modal');
    const logContainer = document.getElementById('run-log');

    modal.classList.add('show');
    logContainer.innerHTML = '<div class="log-line">正在启动...</div>';

    fetch('/api/run', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // 轮询获取日志
                pollStatus();
            } else {
                logContainer.innerHTML = `<div class="log-line" style="color: #ef4444;">${data.error}</div>`;
            }
        })
        .catch(e => {
            logContainer.innerHTML = `<div class="log-line" style="color: #ef4444;">启动失败: ${e}</div>`;
        });
}

// 轮询状态
let pollInterval = null;

function pollStatus() {
    if (pollInterval) clearInterval(pollInterval);

    pollInterval = setInterval(() => {
        fetch('/api/status')
            .then(r => r.json())
            .then(data => {
                const logContainer = document.getElementById('run-log');

                if (data.log && data.log.length > 0) {
                    logContainer.innerHTML = data.log.map(line =>
                        `<div class="log-line">${escapeHtml(line)}</div>`
                    ).join('');
                    logContainer.scrollTop = logContainer.scrollHeight;
                }

                if (!data.running) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                    logContainer.innerHTML += '<div class="log-line" style="color: #10b981;">✓ 运行完成</div>';
                }
            });
    }, 1000);
}

// HTML 转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Modal 关闭
document.addEventListener('DOMContentLoaded', function() {
    // 关闭按钮
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', function() {
            this.closest('.modal').classList.remove('show');
            if (pollInterval) {
                clearInterval(pollInterval);
                pollInterval = null;
            }
        });
    });

    // 点击背景关闭
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('show');
                if (pollInterval) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                }
            }
        });
    });

    // 运行按钮
    const runBtn = document.getElementById('run-btn');
    if (runBtn) {
        runBtn.addEventListener('click', runCrawler);
    }
});
