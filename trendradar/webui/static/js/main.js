// TrendRadar Web UI - 主脚本

let pollInterval = null;
let currentJobId = null;
let globalConfirmResolver = null;

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = message;
    toast.className = 'toast show ' + type;
    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

function buildRunLogUrl(jobId = null) {
    const prefix = jobId ? `job_id=${encodeURIComponent(jobId)}&` : '';
    return `/api/run-log?${prefix}ts=${Date.now()}`;
}

function runCrawler() {
    const modal = document.getElementById('run-modal');
    const logContainer = document.getElementById('run-log');
    const downloadBtn = document.getElementById('download-log-btn');

    if (!modal || !logContainer) return;

    modal.classList.add('show');
    logContainer.innerHTML = '<div class="log-line log-info">正在启动...</div>';
    currentJobId = null;

    if (downloadBtn) {
        downloadBtn.href = buildRunLogUrl();
    }

    fetch('/api/run', { method: 'POST' })
        .then((response) => response.json())
        .then((data) => {
            if (!data.success) {
                const error = data.error || '启动失败';
                logContainer.innerHTML = `<div class="log-line log-error">${escapeHtml(error)}</div>`;
                return;
            }

            currentJobId = data.job_id || null;
            if (downloadBtn) {
                downloadBtn.href = buildRunLogUrl(currentJobId);
            }
            pollStatus(currentJobId);
        })
        .catch((error) => {
            logContainer.innerHTML = `<div class="log-line log-error">启动失败: ${escapeHtml(String(error))}</div>`;
        });
}

function pollStatus(jobId = null) {
    if (pollInterval) {
        clearInterval(pollInterval);
    }

    pollInterval = setInterval(() => {
        const query = jobId ? `?job_id=${encodeURIComponent(jobId)}` : '';
        fetch(`/api/status${query}`)
            .then((response) => response.json())
            .then((data) => {
                const logContainer = document.getElementById('run-log');
                const downloadBtn = document.getElementById('download-log-btn');
                if (!logContainer) return;

                const activeJobId = jobId || data.job_id || currentJobId;
                if (!currentJobId && data.job_id) {
                    currentJobId = data.job_id;
                }

                if (downloadBtn) {
                    downloadBtn.href = buildRunLogUrl(activeJobId || null);
                }

                if (data.log && data.log.length > 0) {
                    logContainer.innerHTML = data.log
                        .map((line) => {
                            const logClass = getLogClass(line);
                            return `<div class="log-line ${logClass}">${escapeHtml(line)}</div>`;
                        })
                        .join('');
                    logContainer.scrollTop = logContainer.scrollHeight;
                }

                if (!data.running) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                    logContainer.innerHTML += '<div class="log-line log-success">✓ 运行完成</div>';
                }
            })
            .catch(() => {
                clearInterval(pollInterval);
                pollInterval = null;
            });
    }, 1000);
}

function getLogClass(line) {
    const text = String(line || '');
    const lower = text.toLowerCase();

    if (
        text.includes('错误') ||
        text.includes('失败') ||
        lower.includes('error') ||
        lower.includes('exception') ||
        lower.includes('traceback')
    ) {
        return 'log-error';
    }

    if (text.includes('警告') || lower.includes('warn')) {
        return 'log-warn';
    }

    if (text.includes('成功') || text.includes('完成') || text.includes('已更新')) {
        return 'log-success';
    }

    return '';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function closeGlobalConfirmDialog(result) {
    const modal = document.getElementById('global-confirm-modal');
    if (modal) {
        modal.classList.remove('show');
    }

    if (typeof globalConfirmResolver === 'function') {
        const resolve = globalConfirmResolver;
        globalConfirmResolver = null;
        resolve(result === true);
    }
}

function shouldIgnoreGlobalConfirmEnter() {
    const active = document.activeElement;
    if (!active) {
        return false;
    }

    const tagName = String(active.tagName || '').toUpperCase();
    if (tagName === 'TEXTAREA') {
        return true;
    }

    return !!active.isContentEditable;
}

function showConfirmDialog(options = {}) {
    const modal = document.getElementById('global-confirm-modal');
    const titleNode = document.getElementById('global-confirm-title');
    const messageNode = document.getElementById('global-confirm-message');
    const cancelBtn = document.getElementById('global-confirm-cancel');
    const okBtn = document.getElementById('global-confirm-ok');

    if (!modal || !titleNode || !messageNode || !cancelBtn || !okBtn) {
        return Promise.resolve(false);
    }

    if (typeof globalConfirmResolver === 'function') {
        globalConfirmResolver(false);
        globalConfirmResolver = null;
    }

    const title = String(options.title || 'Confirm Action');
    const message = String(options.message || 'Are you sure?');
    const confirmText = String(options.confirmText || 'Confirm');
    const confirmType = String(options.confirmType || 'primary').toLowerCase();
    const buttonClass = confirmType === 'danger' ? 'btn btn-sm btn-danger' : 'btn btn-sm btn-primary';

    titleNode.textContent = title;
    messageNode.textContent = message;
    okBtn.textContent = confirmText;
    okBtn.className = buttonClass;

    modal.classList.add('show');
    requestAnimationFrame(() => {
        cancelBtn.focus();
    });

    return new Promise((resolve) => {
        globalConfirmResolver = resolve;
    });
}

window.showConfirmDialog = showConfirmDialog;

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.modal-close').forEach((button) => {
        button.addEventListener('click', function () {
            this.closest('.modal').classList.remove('show');
            if (pollInterval) {
                clearInterval(pollInterval);
                pollInterval = null;
            }
        });
    });

    document.querySelectorAll('.modal').forEach((modal) => {
        modal.addEventListener('click', function (event) {
            if (event.target === this) {
                this.classList.remove('show');
                if (pollInterval) {
                    clearInterval(pollInterval);
                    pollInterval = null;
                }
            }
        });
    });

    const runBtn = document.getElementById('run-btn');
    const globalConfirmModal = document.getElementById('global-confirm-modal');
    const globalConfirmClose = document.getElementById('global-confirm-close');
    const globalConfirmCancel = document.getElementById('global-confirm-cancel');
    const globalConfirmOk = document.getElementById('global-confirm-ok');
    if (runBtn) {
        runBtn.addEventListener('click', runCrawler);
    }

    if (globalConfirmClose) {
        globalConfirmClose.addEventListener('click', () => {
            closeGlobalConfirmDialog(false);
        });
    }
    if (globalConfirmCancel) {
        globalConfirmCancel.addEventListener('click', () => {
            closeGlobalConfirmDialog(false);
        });
    }
    if (globalConfirmOk) {
        globalConfirmOk.addEventListener('click', () => {
            closeGlobalConfirmDialog(true);
        });
    }
    if (globalConfirmModal) {
        globalConfirmModal.addEventListener('click', (event) => {
            if (event.target === globalConfirmModal) {
                closeGlobalConfirmDialog(false);
            }
        });
    }

    document.addEventListener('keydown', (event) => {
        if (!globalConfirmModal || !globalConfirmModal.classList.contains('show')) {
            return;
        }

        if (event.key === 'Escape') {
            closeGlobalConfirmDialog(false);
            return;
        }

        if (event.key === 'Enter') {
            if (shouldIgnoreGlobalConfirmEnter()) {
                return;
            }
            event.preventDefault();
            closeGlobalConfirmDialog(true);
        }
    });
});
