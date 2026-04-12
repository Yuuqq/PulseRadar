# coding=utf-8
"""HTML 报告脚本常量"""

REPORT_JS = """
            async function saveAsImage() {
                const button = event.target;
                const originalText = button.textContent;
                const isDark = document.body.dataset.theme === 'dark';
                const backgroundColor = isDark ? '#0b1220' : '#ffffff';

                try {
                    button.textContent = '生成中...';
                    button.disabled = true;
                    window.scrollTo(0, 0);

                    // 等待页面稳定
                    await new Promise(resolve => setTimeout(resolve, 200));

                    // 截图前隐藏按钮
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'hidden';

                    // 再次等待确保按钮完全隐藏
                    await new Promise(resolve => setTimeout(resolve, 100));

                    const container = document.querySelector('.container');

                    const canvas = await html2canvas(container, {
                        backgroundColor: backgroundColor,
                        scale: 1.5,
                        useCORS: true,
                        allowTaint: false,
                        imageTimeout: 10000,
                        removeContainer: false,
                        foreignObjectRendering: false,
                        logging: false,
                        width: container.offsetWidth,
                        height: container.offsetHeight,
                        x: 0,
                        y: 0,
                        scrollX: 0,
                        scrollY: 0,
                        windowWidth: window.innerWidth,
                        windowHeight: window.innerHeight
                    });

                    buttons.style.visibility = 'visible';

                    const link = document.createElement('a');
                    const now = new Date();
                    const filename = `TrendRadar_热点新闻分析_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}.png`;

                    link.download = filename;
                    link.href = canvas.toDataURL('image/png', 1.0);

                    // 触发下载
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);

                    button.textContent = '保存成功!';
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);

                } catch (error) {
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'visible';
                    button.textContent = '保存失败';
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);
                }
            }

            async function saveAsMultipleImages() {
                const button = event.target;
                const originalText = button.textContent;
                const container = document.querySelector('.container');
                const scale = 1.5;
                const maxHeight = 5000 / scale;
                const isDark = document.body.dataset.theme === 'dark';
                const backgroundColor = isDark ? '#0b1220' : '#ffffff';

                try {
                    button.textContent = '分析中...';
                    button.disabled = true;

                    // 获取所有可能的分割元素
                    const newsItems = Array.from(container.querySelectorAll('.news-item'));
                    const wordGroups = Array.from(container.querySelectorAll('.word-group'));
                    const newSection = container.querySelector('.new-section');
                    const errorSection = container.querySelector('.error-section');
                    const header = container.querySelector('.header');
                    const footer = container.querySelector('.footer');

                    // 计算元素位置和高度
                    const containerRect = container.getBoundingClientRect();
                    const elements = [];

                    // 添加header作为必须包含的元素
                    elements.push({
                        type: 'header',
                        element: header,
                        top: 0,
                        bottom: header.offsetHeight,
                        height: header.offsetHeight
                    });

                    // 添加错误信息（如果存在）
                    if (errorSection) {
                        const rect = errorSection.getBoundingClientRect();
                        elements.push({
                            type: 'error',
                            element: errorSection,
                            top: rect.top - containerRect.top,
                            bottom: rect.bottom - containerRect.top,
                            height: rect.height
                        });
                    }

                    // 按word-group分组处理news-item
                    wordGroups.forEach(group => {
                        const groupRect = group.getBoundingClientRect();
                        const groupNewsItems = group.querySelectorAll('.news-item');

                        // 添加word-group的header部分
                        const wordHeader = group.querySelector('.word-header');
                        if (wordHeader) {
                            const headerRect = wordHeader.getBoundingClientRect();
                            elements.push({
                                type: 'word-header',
                                element: wordHeader,
                                parent: group,
                                top: groupRect.top - containerRect.top,
                                bottom: headerRect.bottom - containerRect.top,
                                height: headerRect.height
                            });
                        }

                        // 添加每个news-item
                        groupNewsItems.forEach(item => {
                            const rect = item.getBoundingClientRect();
                            elements.push({
                                type: 'news-item',
                                element: item,
                                parent: group,
                                top: rect.top - containerRect.top,
                                bottom: rect.bottom - containerRect.top,
                                height: rect.height
                            });
                        });
                    });

                    // 添加新增新闻部分
                    if (newSection) {
                        const rect = newSection.getBoundingClientRect();
                        elements.push({
                            type: 'new-section',
                            element: newSection,
                            top: rect.top - containerRect.top,
                            bottom: rect.bottom - containerRect.top,
                            height: rect.height
                        });
                    }

                    // 添加footer
                    const footerRect = footer.getBoundingClientRect();
                    elements.push({
                        type: 'footer',
                        element: footer,
                        top: footerRect.top - containerRect.top,
                        bottom: footerRect.bottom - containerRect.top,
                        height: footer.offsetHeight
                    });

                    // 计算分割点
                    const segments = [];
                    let currentSegment = { start: 0, end: 0, height: 0, includeHeader: true };
                    let headerHeight = header.offsetHeight;
                    currentSegment.height = headerHeight;

                    for (let i = 1; i < elements.length; i++) {
                        const element = elements[i];
                        const potentialHeight = element.bottom - currentSegment.start;

                        // 检查是否需要创建新分段
                        if (potentialHeight > maxHeight && currentSegment.height > headerHeight) {
                            // 在前一个元素结束处分割
                            currentSegment.end = elements[i - 1].bottom;
                            segments.push(currentSegment);

                            // 开始新分段
                            currentSegment = {
                                start: currentSegment.end,
                                end: 0,
                                height: element.bottom - currentSegment.end,
                                includeHeader: false
                            };
                        } else {
                            currentSegment.height = potentialHeight;
                            currentSegment.end = element.bottom;
                        }
                    }

                    // 添加最后一个分段
                    if (currentSegment.height > 0) {
                        currentSegment.end = container.offsetHeight;
                        segments.push(currentSegment);
                    }

                    button.textContent = `生成中 (0/${segments.length})...`;

                    // 隐藏保存按钮
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'hidden';

                    // 为每个分段生成图片
                    const images = [];
                    for (let i = 0; i < segments.length; i++) {
                        const segment = segments[i];
                        button.textContent = `生成中 (${i + 1}/${segments.length})...`;

                        // 创建临时容器用于截图
                        const tempContainer = document.createElement('div');
                        tempContainer.style.cssText = `
                            position: absolute;
                            left: -9999px;
                            top: 0;
                            width: ${container.offsetWidth}px;
                            background: ${backgroundColor};
                        `;
                        tempContainer.className = 'container';

                        // 克隆容器内容
                        const clonedContainer = container.cloneNode(true);

                        // 移除克隆内容中的保存按钮
                        const clonedButtons = clonedContainer.querySelector('.save-buttons');
                        if (clonedButtons) {
                            clonedButtons.style.display = 'none';
                        }

                        tempContainer.appendChild(clonedContainer);
                        document.body.appendChild(tempContainer);

                        // 等待DOM更新
                        await new Promise(resolve => setTimeout(resolve, 100));

                        // 使用html2canvas截取特定区域
                        const canvas = await html2canvas(clonedContainer, {
                            backgroundColor: backgroundColor,
                            scale: scale,
                            useCORS: true,
                            allowTaint: false,
                            imageTimeout: 10000,
                            logging: false,
                            width: container.offsetWidth,
                            height: segment.end - segment.start,
                            x: 0,
                            y: segment.start,
                            windowWidth: window.innerWidth,
                            windowHeight: window.innerHeight
                        });

                        images.push(canvas.toDataURL('image/png', 1.0));

                        // 清理临时容器
                        document.body.removeChild(tempContainer);
                    }

                    // 恢复按钮显示
                    buttons.style.visibility = 'visible';

                    // 下载所有图片
                    const now = new Date();
                    const baseFilename = `TrendRadar_热点新闻分析_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;

                    for (let i = 0; i < images.length; i++) {
                        const link = document.createElement('a');
                        link.download = `${baseFilename}_part${i + 1}.png`;
                        link.href = images[i];
                        document.body.appendChild(link);
                        link.click();
                        document.body.removeChild(link);

                        // 延迟一下避免浏览器阻止多个下载
                        await new Promise(resolve => setTimeout(resolve, 100));
                    }

                    button.textContent = `已保存 ${segments.length} 张图片!`;
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);

                } catch (error) {
                    console.error('分段保存失败:', error);
                    const buttons = document.querySelector('.save-buttons');
                    buttons.style.visibility = 'visible';
                    button.textContent = '保存失败';
                    setTimeout(() => {
                        button.textContent = originalText;
                        button.disabled = false;
                    }, 2000);
                }
            }

            const THEME_KEY = 'trendradar_theme';
            const VIEW_KEY = 'trendradar_view';
            const SECTION_KEY = 'trendradar_section';

            function setTheme(theme) {
                document.body.dataset.theme = theme;
                localStorage.setItem(THEME_KEY, theme);
                const btn = document.getElementById('theme-toggle');
                if (btn) {
                    btn.textContent = theme === 'dark' ? '☀️' : '🌙';
                }
            }

            function toggleTheme() {
                const current = document.body.dataset.theme || 'light';
                setTheme(current === 'dark' ? 'light' : 'dark');
            }

            function getActiveView() {
                const views = Array.from(document.querySelectorAll('.hotlist-view'));
                return views.find(view => view.style.display !== 'none') || views[0] || null;
            }

            function setSection(section) {
                const tabs = Array.from(document.querySelectorAll('.section-tab'));
                if (!tabs.length) {
                    return;
                }
                const available = tabs.map(t => t.dataset.section);
                let target = available.includes(section) ? section : 'all';
                if (!available.includes(target)) {
                    target = available[0];
                }

                document.querySelectorAll('.report-section').forEach(sec => {
                    const match = target === 'all' || sec.dataset.section === target;
                    sec.dataset.hidden = match ? "false" : "true";
                });

                tabs.forEach(tab => {
                    tab.classList.toggle('active', tab.dataset.section === target);
                });

                localStorage.setItem(SECTION_KEY, target);

                if (target === 'all' || target === 'hotlist') {
                    applySearchFilter();
                }
            }

            function setView(view) {
                const views = Array.from(document.querySelectorAll('.hotlist-view'));
                if (!views.length) {
                    return;
                }
                const available = views.map(v => v.dataset.view);
                const targetView = available.includes(view) ? view : available[0];
                views.forEach(v => {
                    v.style.display = v.dataset.view === targetView ? '' : 'none';
                });
                document.querySelectorAll('.view-btn').forEach(btn => {
                    btn.classList.toggle('active', btn.dataset.view === targetView);
                });
                localStorage.setItem(VIEW_KEY, targetView);
                applySearchFilter();
            }

            function initSectionTabs() {
                const tabs = document.querySelectorAll('.section-tab');
                if (!tabs.length) {
                    return;
                }
                document.body.dataset.sectionTabs = 'true';
                tabs.forEach(tab => {
                    tab.addEventListener('click', () => setSection(tab.dataset.section));
                });
                const saved = localStorage.getItem(SECTION_KEY) || 'all';
                setSection(saved);
            }

            function initViewToggle() {
                const viewButtons = document.querySelectorAll('.view-btn');
                if (!viewButtons.length) {
                    return;
                }
                viewButtons.forEach(btn => {
                    btn.addEventListener('click', () => setView(btn.dataset.view));
                });
                const defaultView = document.body.dataset.defaultView || 'keyword';
                const savedView = localStorage.getItem(VIEW_KEY);
                setView(savedView || defaultView);
            }

            function initTopicTabs() {
                document.querySelectorAll('.hotlist-view').forEach(view => {
                    const tabs = Array.from(view.querySelectorAll('.topic-tab'));
                    if (!tabs.length) {
                        return;
                    }
                    const groups = Array.from(view.querySelectorAll('.word-group'));
                    const storageKey = `trendradar_topic_${view.dataset.view}`;

                    const setActive = (topic) => {
                        let found = false;
                        tabs.forEach(tab => {
                            if (tab.dataset.topic === topic) {
                                found = true;
                                tab.classList.add('active');
                            } else {
                                tab.classList.remove('active');
                            }
                        });
                        const target = found ? topic : 'all';
                        groups.forEach(group => {
                            const match = target === 'all' || group.dataset.topic === target;
                            group.dataset.hidden = match ? "false" : "true";
                        });
                        localStorage.setItem(storageKey, target);
                        applySearchFilter();
                    };

                    tabs.forEach(tab => {
                        tab.addEventListener('click', () => setActive(tab.dataset.topic));
                    });

                    const saved = localStorage.getItem(storageKey) || 'all';
                    setActive(saved);
                });
            }

            function applySearchFilter() {
                const input = document.getElementById('search-input');
                if (!input) {
                    return;
                }
                const query = input.value.trim().toLowerCase();
                const view = getActiveView();
                if (!view) {
                    return;
                }

                let anyVisible = false;
                const groups = Array.from(view.querySelectorAll('.word-group'));
                groups.forEach(group => {
                    const isHidden = group.dataset.hidden === "true";
                    let visibleCount = 0;
                    group.querySelectorAll('.news-item').forEach(item => {
                        const hay = (item.dataset.search || '').toLowerCase();
                        const match = !query || hay.includes(query);
                        item.style.display = match ? '' : 'none';
                        if (match) {
                            visibleCount += 1;
                        }
                    });
                    if (isHidden) {
                        group.dataset.filtered = "true";
                        return;
                    }
                    group.dataset.filtered = visibleCount === 0 ? "true" : "false";
                    if (visibleCount > 0) {
                        anyVisible = true;
                    }
                });

                const empty = document.getElementById('search-empty');
                if (empty) {
                    empty.style.display = anyVisible ? 'none' : 'block';
                }
            }

            function initSearch() {
                const input = document.getElementById('search-input');
                if (!input) {
                    return;
                }
                input.addEventListener('input', applySearchFilter);
            }

            document.addEventListener('DOMContentLoaded', function() {
                window.scrollTo(0, 0);
                setTheme(localStorage.getItem(THEME_KEY) || 'light');
                initSectionTabs();
                initViewToggle();
                initTopicTabs();
                initSearch();
            });
"""
