"""HTML 报告样式常量"""

REPORT_CSS = """
            * { box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
                margin: 0;
                padding: 16px;
                background: #f4f6fb;
                color: #111827;
                line-height: 1.65;
                font-size: 15px;
            }

            .container {
                max-width: 1060px;
                width: 96%;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                overflow: hidden;
                border: 1px solid #e5e7eb;
                box-shadow: 0 4px 6px rgba(15, 23, 42, 0.04), 0 16px 40px rgba(15, 23, 42, 0.08);
            }

            .header {
                background: linear-gradient(135deg, #1d4ed8 0%, #0f766e 100%);
                color: white;
                padding: 36px 28px;
                text-align: center;
                position: relative;
            }

            .save-buttons {
                position: absolute;
                top: 16px;
                right: 16px;
                display: flex;
                gap: 8px;
            }

            .save-btn {
                background: rgba(255, 255, 255, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.3);
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 13px;
                font-weight: 500;
                transition: all 0.2s ease;
                backdrop-filter: blur(10px);
                white-space: nowrap;
            }

            .save-btn:hover {
                background: rgba(255, 255, 255, 0.3);
                border-color: rgba(255, 255, 255, 0.5);
                transform: translateY(-1px);
            }

            .save-btn:active {
                transform: translateY(0);
            }

            .save-btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }

            .save-btn.theme-toggle {
                padding: 8px 10px;
                min-width: 36px;
            }

            .header-title {
                font-size: 26px;
                font-weight: 700;
                margin: 0 0 24px 0;
                letter-spacing: -0.3px;
            }

            .header-info {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 16px;
                font-size: 13px;
                opacity: 0.95;
            }

            .info-item {
                text-align: center;
            }

            .info-label {
                display: block;
                font-size: 12px;
                opacity: 0.8;
                margin-bottom: 4px;
            }

            .info-value {
                font-weight: 700;
                font-size: 18px;
            }

            .content {
                padding: 32px 36px;
            }

            .controls {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                align-items: center;
                justify-content: space-between;
                margin: 4px 0 16px;
            }

            .controls-left,
            .controls-right {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                align-items: center;
            }

            .view-toggle {
                display: flex;
                gap: 6px;
                background: #e2e8f0;
                padding: 4px;
                border-radius: 999px;
            }

            .view-btn {
                border: none;
                background: transparent;
                color: #1f2937;
                font-size: 12px;
                font-weight: 600;
                padding: 6px 12px;
                border-radius: 999px;
                cursor: pointer;
                transition: all 0.15s ease;
            }

            .view-btn.active {
                background: #111827;
                color: #ffffff;
            }

            .search-input {
                border: 1px solid #e2e8f0;
                border-radius: 999px;
                padding: 8px 14px;
                font-size: 13px;
                width: 240px;
                outline: none;
                background: #ffffff;
                color: #0f172a;
            }

            .search-input::placeholder {
                color: #94a3b8;
            }

            .section-tabs {
                position: sticky;
                top: 0;
                z-index: 6;
                background: linear-gradient(to bottom, #ffffff 85%, rgba(255, 255, 255, 0));
                margin: -8px -4px 24px;
                padding: 14px 4px 12px;
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                border-bottom: 2px solid #e2e8f0;
            }

            .section-tab {
                border: 1px solid #e2e8f0;
                background: #ffffff;
                color: #0f172a;
                border-radius: 999px;
                padding: 9px 18px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.15s ease;
                white-space: nowrap;
            }

            .section-tab:hover {
                transform: translateY(-1px);
                box-shadow: 0 6px 16px rgba(15, 23, 42, 0.12);
            }

            .section-tab.active {
                background: #111827;
                color: #ffffff;
                border-color: #111827;
            }

            .topic-tabs {
                position: sticky;
                top: 52px;
                z-index: 5;
                background: linear-gradient(to bottom, #ffffff 85%, rgba(255, 255, 255, 0));
                margin: -4px 0 24px;
                padding: 14px 0 12px;
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
                border-bottom: 1px solid #e2e8f0;
            }

            .topic-tabs::after {
                content: "";
                flex: 0 0 8px;
            }

            .topic-tab {
                border: none;
                background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
                color: #4b5563;
                border-radius: 12px;
                padding: 10px 18px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                white-space: nowrap;
                transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
                display: inline-flex;
                align-items: center;
                gap: 8px;
            }

            .topic-tab:hover {
                background: linear-gradient(135deg, #e5e7eb 0%, #d1d5db 100%);
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }

            .topic-tab .topic-count {
                background: rgba(0, 0, 0, 0.08);
                padding: 2px 8px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: 700;
                color: #6b7280;
            }

            .topic-tab.active {
                background: linear-gradient(135deg, #2563eb 0%, #0f766e 100%);
                color: #ffffff;
                box-shadow: 0 4px 14px rgba(37, 99, 235, 0.35);
            }

            .topic-tab.active:hover {
                background: linear-gradient(135deg, #1d4ed8 0%, #0d9488 100%);
                box-shadow: 0 6px 20px rgba(15, 118, 110, 0.4);
            }

            .topic-tab.active .topic-count {
                background: rgba(255, 255, 255, 0.25);
                color: #ffffff;
            }

            .report-section[data-hidden="true"] {
                display: none;
            }

            .word-group[data-hidden="true"],
            .word-group[data-filtered="true"] {
                display: none;
            }

            .word-group {
                margin-bottom: 28px;
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                padding: 20px 22px 12px;
                box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.03);
                transition: box-shadow 0.2s ease;
            }

            .word-group:hover {
                box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.06);
            }

            .word-group:first-child {
                margin-top: 0;
            }

            .word-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 16px;
                padding-bottom: 12px;
                border-bottom: 2px solid #f1f5f9;
            }

            .word-info {
                display: flex;
                align-items: center;
                gap: 12px;
            }

            .word-name {
                font-size: 18px;
                font-weight: 600;
                color: #0f172a;
            }

            .word-count {
                color: #1d4ed8;
                font-size: 12px;
                font-weight: 600;
                background: #dbeafe;
                padding: 2px 8px;
                border-radius: 999px;
            }

            .word-count.hot { color: #b91c1c; background: #fee2e2; }
            .word-count.warm { color: #c2410c; background: #ffedd5; }

            .word-index {
                color: #94a3b8;
                font-size: 12px;
            }

            .news-item {
                margin-bottom: 4px;
                padding: 14px 8px;
                border-bottom: 1px solid #f1f5f9;
                position: relative;
                display: flex;
                gap: 12px;
                align-items: center;
                border-radius: 8px;
                transition: background 0.15s ease;
            }

            .news-item:hover {
                background: #f8fafc;
            }

            .news-item:last-child {
                border-bottom: none;
                margin-bottom: 0;
            }

            .news-item.new::after {
                content: "NEW";
                position: absolute;
                top: 12px;
                right: 0;
                background: #fde047;
                color: #92400e;
                font-size: 9px;
                font-weight: 700;
                padding: 3px 6px;
                border-radius: 4px;
                letter-spacing: 0.5px;
            }

            .news-number {
                color: #475569;
                font-size: 12px;
                font-weight: 600;
                min-width: 20px;
                text-align: center;
                flex-shrink: 0;
                background: #e2e8f0;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                align-self: flex-start;
                margin-top: 8px;
            }

            .news-content {
                flex: 1;
                min-width: 0;
                padding-right: 40px;
            }

            .news-item.new .news-content {
                padding-right: 50px;
            }

            .news-header {
                display: flex;
                align-items: center;
                gap: 6px;
                margin-bottom: 6px;
                flex-wrap: wrap;
            }

            .source-name {
                color: #64748b;
                font-size: 12px;
                font-weight: 500;
            }

            .keyword-tag {
                color: #0369a1;
                font-size: 12px;
                font-weight: 500;
                background: #e0f2fe;
                padding: 2px 6px;
                border-radius: 4px;
            }

            .rank-num {
                color: #fff;
                background: #94a3b8;
                font-size: 10px;
                font-weight: 700;
                padding: 2px 6px;
                border-radius: 10px;
                min-width: 18px;
                text-align: center;
            }

            .rank-num.top { background: #ef4444; }
            .rank-num.high { background: #f97316; }

            .time-info {
                color: #94a3b8;
                font-size: 11px;
            }

            .count-info {
                color: #059669;
                font-size: 11px;
                font-weight: 500;
            }

            .news-title {
                font-size: 16px;
                line-height: 1.55;
                color: #0f172a;
                margin: 0;
            }

            .news-link {
                color: #1d4ed8;
                text-decoration: none;
            }

            .news-link:hover {
                text-decoration: underline;
            }

            .news-link:visited {
                color: #0f766e;
            }

            /* 通用区域分割线样式 */
            .section-divider {
                margin-top: 36px;
                padding-top: 28px;
                border-top: 3px solid #e2e8f0;
            }

            /* 热榜统计区样式 */
            .hotlist-section {
                /* 默认无边框，由 section-divider 动态添加 */
            }

            .new-section {
                margin-top: 36px;
                padding-top: 28px;
            }

            .new-section-title {
                color: #0f172a;
                font-size: 18px;
                font-weight: 700;
                margin: 0 0 24px 0;
            }

            .new-source-group {
                margin-bottom: 28px;
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                padding: 20px 22px;
                box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.03);
            }

            .new-source-title {
                color: #475569;
                font-size: 14px;
                font-weight: 600;
                margin: 0 0 14px 0;
                padding-bottom: 10px;
                border-bottom: 2px solid #f1f5f9;
            }

            .new-item {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 12px 8px;
                border-bottom: 1px solid #f1f5f9;
                border-radius: 8px;
                transition: background 0.15s ease;
            }

            .new-item:hover {
                background: #f8fafc;
            }

            .new-item:last-child {
                border-bottom: none;
            }

            .new-item-number {
                color: #475569;
                font-size: 12px;
                font-weight: 600;
                min-width: 18px;
                text-align: center;
                flex-shrink: 0;
                background: #e2e8f0;
                border-radius: 50%;
                width: 20px;
                height: 20px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .new-item-rank {
                color: #fff;
                background: #94a3b8;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 6px;
                border-radius: 8px;
                min-width: 20px;
                text-align: center;
                flex-shrink: 0;
            }

            .new-item-rank.top { background: #ef4444; }
            .new-item-rank.high { background: #f97316; }

            .new-item-content {
                flex: 1;
                min-width: 0;
            }

            .new-item-title {
                font-size: 15px;
                line-height: 1.5;
                color: #0f172a;
                margin: 0;
            }

            .error-section {
                background: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 24px;
            }

            .error-title {
                color: #dc2626;
                font-size: 14px;
                font-weight: 600;
                margin: 0 0 12px 0;
            }

            .error-list {
                list-style: none;
                padding: 0;
                margin: 0;
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }

            .error-item {
                color: #991b1b;
                font-size: 13px;
                padding: 4px 12px;
                background: rgba(220, 38, 38, 0.1);
                border-radius: 4px;
                font-family: 'SF Mono', Consolas, monospace;
                display: inline-block;
            }

            .footer {
                margin-top: 40px;
                padding: 24px 32px;
                background: #f8fafc;
                border-top: 2px solid #e2e8f0;
                text-align: center;
            }

            .footer-content {
                font-size: 13px;
                color: #64748b;
                line-height: 1.6;
            }

            .footer-link {
                color: #2563eb;
                text-decoration: none;
                font-weight: 500;
                transition: color 0.2s ease;
            }

            .footer-link:hover {
                color: #0f766e;
                text-decoration: underline;
            }

            .project-name {
                font-weight: 600;
                color: #374151;
            }

            @media (max-width: 480px) {
                body { padding: 8px; }
                .header { padding: 28px 20px; }
                .content { padding: 20px 16px; }
                .footer { padding: 20px; }
                .header-info { grid-template-columns: 1fr; gap: 12px; }
                .controls { gap: 10px; }
                .controls-left, .controls-right { width: 100%; }
                .view-toggle { width: 100%; justify-content: center; }
                .search-input { width: 100%; }
                .topic-tab { font-size: 11px; padding: 6px 10px; }
                .news-header { gap: 6px; }
                .news-content { padding-right: 45px; }
                .news-item { gap: 8px; padding: 12px 4px; }
                .new-item { gap: 8px; padding: 10px 4px; }
                .news-number { width: 20px; height: 20px; font-size: 12px; }
                .word-group { padding: 16px 14px 8px; border-radius: 10px; }
                .feed-group { padding: 16px 14px; border-radius: 10px; }
                .new-source-group { padding: 16px 14px; border-radius: 10px; }
                .ai-section { padding: 20px 16px; }
                .ai-block { padding: 16px; }
                .save-buttons {
                    position: static;
                    margin-bottom: 16px;
                    display: flex;
                    gap: 8px;
                    justify-content: center;
                    flex-direction: column;
                    width: 100%;
                }
                .save-btn {
                    width: 100%;
                }
            }

            /* RSS 订阅内容样式 */
            .rss-section {
                margin-top: 36px;
                padding-top: 28px;
            }

            .rss-section-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 24px;
            }

            .rss-section-title {
                font-size: 20px;
                font-weight: 700;
                color: #0f766e;
            }

            .rss-section-count {
                color: #64748b;
                font-size: 14px;
                font-weight: 500;
            }

            .feed-group {
                margin-bottom: 28px;
                background: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                padding: 20px 22px;
                box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.03);
            }

            .feed-group:last-child {
                margin-bottom: 0;
            }

            .feed-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 16px;
                padding-bottom: 12px;
                border-bottom: 2px solid #0d9488;
            }

            .feed-name {
                font-size: 16px;
                font-weight: 700;
                color: #0f766e;
            }

            .feed-count {
                color: #64748b;
                font-size: 13px;
                font-weight: 500;
            }

            .rss-item {
                margin-bottom: 12px;
                padding: 16px;
                background: #f0fdfa;
                border-radius: 10px;
                border: 1px solid #ccfbf1;
                border-left: 4px solid #0d9488;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }

            .rss-item:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
            }

            .rss-item:last-child {
                margin-bottom: 0;
            }

            .rss-meta {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 6px;
                flex-wrap: wrap;
            }

            .rss-time {
                color: #64748b;
                font-size: 12px;
            }

            .rss-author {
                color: #0f766e;
                font-size: 12px;
                font-weight: 500;
            }

            .rss-title {
                font-size: 15px;
                line-height: 1.5;
                margin-bottom: 6px;
            }

            .rss-link {
                color: #0f172a;
                text-decoration: none;
                font-weight: 500;
            }

            .rss-link:hover {
                color: #0f766e;
                text-decoration: underline;
            }

            .rss-summary {
                font-size: 13px;
                color: #64748b;
                line-height: 1.5;
                margin: 0;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }

            /* 独立展示区样式 - 复用热点词汇统计区样式 */
            .standalone-section {
                margin-top: 32px;
                padding-top: 24px;
            }

            .standalone-section-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 20px;
            }

            .standalone-section-title {
                font-size: 18px;
                font-weight: 600;
                color: #1d4ed8;
            }

            .standalone-section-count {
                color: #64748b;
                font-size: 14px;
            }

            .standalone-group {
                margin-bottom: 40px;
            }

            .standalone-group:last-child {
                margin-bottom: 0;
            }

            .standalone-header {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 20px;
                padding-bottom: 8px;
                border-bottom: 1px solid #f0f0f0;
            }

            .standalone-name {
                font-size: 17px;
                font-weight: 600;
                color: #1a1a1a;
            }

            .standalone-count {
                color: #666;
                font-size: 13px;
                font-weight: 500;
            }

            /* AI 分析区块样式 */
            .ai-section {
                margin-top: 36px;
                padding: 28px;
                background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f0f9ff 100%);
                border-radius: 16px;
                border: 1px solid #bae6fd;
            }

            .ai-section-header {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 24px;
            }

            .ai-section-title {
                font-size: 20px;
                font-weight: 700;
                color: #0369a1;
            }

            .ai-section-badge {
                background: linear-gradient(135deg, #0ea5e9, #0369a1);
                color: white;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 10px;
                border-radius: 6px;
                letter-spacing: 0.5px;
            }

            .ai-block {
                margin-bottom: 16px;
                padding: 20px;
                background: white;
                border-radius: 12px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 4px 12px rgba(3, 105, 161, 0.04);
            }

            .ai-block:last-child {
                margin-bottom: 0;
            }

            .ai-block-title {
                font-size: 14px;
                font-weight: 600;
                color: #0369a1;
                margin-bottom: 8px;
            }

            .ai-block-content {
                font-size: 14px;
                line-height: 1.6;
                color: #334155;
                white-space: pre-wrap;
            }

            .ai-error {
                padding: 16px;
                background: #fef2f2;
                border: 1px solid #fecaca;
                border-radius: 8px;
                color: #991b1b;
                font-size: 14px;
            }

            /* Dark mode */
            body[data-theme="dark"] {
                background: #0f172a;
                color: #e2e8f0;
            }

            body[data-theme="dark"] .container {
                background: #0b1220;
                border-color: #1f2937;
                box-shadow: 0 12px 30px rgba(0, 0, 0, 0.35);
            }

            body[data-theme="dark"] .header {
                background: linear-gradient(135deg, #1e293b 0%, #0f766e 100%);
            }

            body[data-theme="dark"] .save-btn {
                background: rgba(255, 255, 255, 0.12);
                border-color: rgba(255, 255, 255, 0.2);
            }

            body[data-theme="dark"] .save-btn:hover {
                background: rgba(255, 255, 255, 0.18);
            }

            body[data-theme="dark"] .controls {
                color: #e2e8f0;
            }

            body[data-theme="dark"] .view-toggle {
                background: #1f2937;
            }

            body[data-theme="dark"] .view-btn {
                color: #e2e8f0;
            }

            body[data-theme="dark"] .view-btn.active {
                background: #2563eb;
            }

            body[data-theme="dark"] .search-input {
                background: #0f172a;
                border-color: #334155;
                color: #e2e8f0;
            }

            body[data-theme="dark"] .section-tabs {
                background: linear-gradient(to bottom, #0b1220 85%, rgba(11, 18, 32, 0));
                border-bottom: 1px solid #1f2937;
            }

            body[data-theme="dark"] .section-tab {
                background: #0f172a;
                color: #e2e8f0;
                border-color: #1f2937;
                box-shadow: none;
            }

            body[data-theme="dark"] .section-tab:hover {
                box-shadow: none;
                background: #111827;
            }

            body[data-theme="dark"] .section-tab.active {
                background: #2563eb;
                border-color: #2563eb;
                color: #ffffff;
            }

            body[data-theme="dark"] .topic-tabs {
                background: linear-gradient(to bottom, #0b1220 85%, rgba(11, 18, 32, 0));
                border-bottom: 1px solid #1f2937;
            }

            body[data-section-tabs="true"] .topic-tabs {
                top: 52px;
            }

            body[data-theme="dark"] .topic-tab {
                background: #1f2937;
                color: #e2e8f0;
                box-shadow: none;
            }

            body[data-theme="dark"] .topic-tab:hover {
                background: #334155;
                box-shadow: none;
            }

            body[data-theme="dark"] .topic-tab.active {
                background: #2563eb;
                color: #ffffff;
                box-shadow: none;
            }

            body[data-theme="dark"] .topic-tab.active:hover {
                background: #1d4ed8;
            }

            body[data-theme="dark"] .topic-tab .topic-count {
                background: rgba(255, 255, 255, 0.12);
                color: #cbd5f5;
            }

            body[data-theme="dark"] .word-group {
                background: #0f172a;
                border-color: #1f2937;
            }

            body[data-theme="dark"] .word-header {
                border-bottom-color: #1f2937;
            }

            body[data-theme="dark"] .word-name {
                color: #e2e8f0;
            }

            body[data-theme="dark"] .word-count {
                background: #1e293b;
                color: #93c5fd;
            }

            body[data-theme="dark"] .word-count.hot {
                background: #3f1d1d;
                color: #fca5a5;
            }

            body[data-theme="dark"] .word-count.warm {
                background: #3b2616;
                color: #fdba74;
            }

            body[data-theme="dark"] .news-item {
                border-bottom-color: #1f2937;
            }

            body[data-theme="dark"] .news-number {
                background: #1f2937;
                color: #94a3b8;
            }

            body[data-theme="dark"] .source-name,
            body[data-theme="dark"] .time-info {
                color: #94a3b8;
            }

            body[data-theme="dark"] .keyword-tag {
                background: #1e3a8a;
                color: #bfdbfe;
            }

            body[data-theme="dark"] .news-title,
            body[data-theme="dark"] .new-item-title,
            body[data-theme="dark"] .rss-link {
                color: #e2e8f0;
            }

            body[data-theme="dark"] .news-link {
                color: #60a5fa;
            }

            body[data-theme="dark"] .news-link:visited {
                color: #a78bfa;
            }

            body[data-theme="dark"] .new-source-title,
            body[data-theme="dark"] .new-section-title {
                color: #e2e8f0;
            }

            body[data-theme="dark"] .new-item {
                border-bottom-color: #1f2937;
            }

            body[data-theme="dark"] .new-item-number,
            body[data-theme="dark"] .new-item-rank,
            body[data-theme="dark"] .rank-num {
                background: #1f2937;
            }

            body[data-theme="dark"] .rss-item {
                background: #0f172a;
                border-color: #134e4a;
            }

            body[data-theme="dark"] .rss-summary,
            body[data-theme="dark"] .rss-time,
            body[data-theme="dark"] .rss-section-count {
                color: #94a3b8;
            }

            body[data-theme="dark"] .rss-section-title,
            body[data-theme="dark"] .feed-name,
            body[data-theme="dark"] .rss-link:hover {
                color: #5eead4;
            }

            body[data-theme="dark"] .feed-header {
                border-bottom-color: #0f766e;
            }

            body[data-theme="dark"] .ai-section {
                background: linear-gradient(135deg, #0b1220 0%, #111827 100%);
                border-color: #1e3a8a;
            }

            body[data-theme="dark"] .ai-section-title,
            body[data-theme="dark"] .ai-block-title {
                color: #7dd3fc;
            }

            body[data-theme="dark"] .ai-block {
                background: #0f172a;
                box-shadow: none;
                border: 1px solid #1f2937;
            }

            body[data-theme="dark"] .ai-block-content {
                color: #e2e8f0;
            }

            body[data-theme="dark"] .footer {
                background: #0f172a;
                border-top-color: #1f2937;
            }

            body[data-theme="dark"] .footer-content {
                color: #94a3b8;
            }

            body[data-theme="dark"] .error-section,
            body[data-theme="dark"] .ai-error {
                background: #3f1d1d;
                border-color: #7f1d1d;
                color: #fecaca;
            }
"""
