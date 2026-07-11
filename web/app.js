const APP_VERSION = '1.19.0';
let tasksData = [];
let simulationChart = null;


document.addEventListener('DOMContentLoaded', () => {
    // 0. Set Version
    const versionHeader = document.getElementById('appVersionHeader');
    if (versionHeader) versionHeader.innerText = `v${APP_VERSION}`;

    // 1. Initialize UI Elements
    lucide.createIcons();
    const bottomNavBar = document.getElementById('bottomNavBar');
    bottomNavBar.style.display = 'flex'; // show nav
    setupTabs();
    setupTheme();
    setupModals();
    setupSimulator();

    
    // 2. Load Global Data
    loadGlobalSettings();
    
    // 3. Check Auth (Mocked for now since backend is open)
    document.getElementById('welcomeScreen').style.display = 'none';
    document.getElementById('mainDashboard').style.display = 'block';
    
    // 4. Load Main Content
    refreshAllData();

    // Setup Global Buttons
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) refreshBtn.addEventListener('click', refreshAllData);

    const refreshLogsBtn = document.getElementById('refreshLogsBtn');
    if (refreshLogsBtn) refreshLogsBtn.addEventListener('click', loadSystemLogs);
    
    const triggerExecuteBtn = document.getElementById('triggerExecuteBtn');
    if (triggerExecuteBtn) {
        triggerExecuteBtn.addEventListener('click', async () => {
            try {
                await fetch('/api/v1/engine/execute', {method: 'POST'});
                alert("전체 수동 매매(Dry-run)가 백그라운드에 등록되었습니다.");
            } catch(e){ alert("오류 발생"); }
        });
    }
    
    const triggerSyncBtn = document.getElementById('triggerSyncBtn');
    if (triggerSyncBtn) {
        triggerSyncBtn.addEventListener('click', async () => {
            try {
                await fetch('/api/v1/engine/sync', {method: 'POST'});
                alert("전체 체결 동기화가 백그라운드에 등록되었습니다.");
            } catch(e) { alert("오류 발생"); }
        });
    }
});

function setupTabs() {
    const navItems = document.querySelectorAll('.nav-item');
    const tabContents = document.querySelectorAll('.tab-content');

    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            const targetTab = item.getAttribute('data-tab');
            tabContents.forEach(content => {
                content.style.display = (content.id === targetTab) ? 'block' : 'none';
            });
            
            if (targetTab === 'order-tab') loadGlobalOrderPreview();
            if (targetTab === 'history-tab') loadGlobalHistory();
            if (targetTab === 'simulator-tab') loadSimulatorTasks();
            if (targetTab === 'settings-tab') loadSystemLogs();
        });
    });
}

function setupTheme() {
    const themeSelector = document.getElementById('themeSelector');
    const savedTheme = localStorage.getItem('ws_theme') || 'theme-domino';
    document.body.className = savedTheme;
    themeSelector.value = savedTheme;

    themeSelector.addEventListener('change', (e) => {
        const selectedTheme = e.target.value;
        document.body.className = selectedTheme;
        localStorage.setItem('ws_theme', selectedTheme);
    });
}

function showLoading(show) {
    document.getElementById('loadingOverlay').style.display = show ? 'flex' : 'none';
}

async function refreshAllData() {
    showLoading(true);
    await loadTasks();
    showLoading(false);
}

/* ==========================================================================
   PORTFOLIO (HOME) TAB
   ========================================================================== */
async function loadTasks() {
    try {
        const res = await fetch('/api/v1/tasks');
        const data = await res.json();
        tasksData = data.tasks || [];
        
        renderPortfolioList(tasksData);
        updateAssetSummary(tasksData);
        loadSimulatorTasks();
    } catch (e) {
        console.error("Failed to load tasks:", e);
    }
}

function renderPortfolioList(tasks) {
    const container = document.getElementById('portfolioTaskList');
    container.innerHTML = '';
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = `
            <div class="glass-card" style="padding: 2rem; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
                운영 중인 테스크가 없습니다.<br>우측 상단의 '테스크 추가' 버튼을 눌러보세요.
            </div>`;
        return;
    }
    
    tasks.forEach(task => {
        const card = document.createElement('div');
        card.className = 'glass-card';
        card.style.padding = '1rem';
        card.style.cursor = 'pointer';
        card.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <div style="background: rgba(0, 242, 254, 0.1); border-radius: 8px; width: 40px; height: 40px; display: flex; align-items: center; justify-content: center;">
                        <i data-lucide="bot" style="color: var(--neon-blue); width: 24px; height: 24px;"></i>
                    </div>
                    <div>
                        <div style="font-weight: 700; font-size: 0.95rem; color: #fff;">${task.nickname || task.id}</div>
                        <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 2px;">
                            <span style="font-weight:600; color:var(--text-primary);">${task.ticker}</span> • 
                            자금 $${task.seed_amt} • ${task.split_count}분할
                        </div>
                    </div>
                </div>
                <button class="btn btn-outline edit-task-btn" data-id="${task.id}" style="padding: 0.3rem 0.5rem;">
                    <i data-lucide="settings" style="width:14px; height:14px;"></i>
                </button>
            </div>
        `;
        
        // 클릭하면 상세 모달(배치/사이클) 띄우기
        card.addEventListener('click', (e) => {
            if (e.target.closest('.edit-task-btn')) {
                e.stopPropagation();
                openTaskModal(task);
            } else {
                openBatchModal(task.id);
            }
        });
        
        container.appendChild(card);
    });
    lucide.createIcons();
}

function updateAssetSummary(tasks) {
    let totalSeed = 0;
    tasks.forEach(t => {
        if(t.seed_amt) totalSeed += parseFloat(t.seed_amt);
    });
    
    document.getElementById('totalCostBase').textContent = '$' + totalSeed.toLocaleString();
    document.getElementById('totalValue').textContent = '$' + totalSeed.toLocaleString(); // TBD with actual stock values
}

/* ==========================================================================
   ORDER TAB (GLOBAL PREVIEW)
   ========================================================================== */
async function loadGlobalOrderPreview() {
    const container = document.getElementById('orderTaskCards');
    if (!container) return;
    container.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted);">주문 목록을 불러오는 중...</div>';
    
    if (tasksData.length === 0) {
        container.innerHTML = '<div class="glass-card" style="padding:2rem; text-align:center; color:var(--text-muted);">등록된 테스크가 없습니다.</div>';
        return;
    }

    const now = new Date();
    document.getElementById('orderBaseDate').textContent = `${now.getMonth()+1}월 ${now.getDate()}일 기준`;
    container.innerHTML = '';

    for (const task of tasksData) {
        let orders = [];
        try {
            const res = await fetch(`/api/v1/tasks/${task.id}/orders/preview`);
            if (res.ok) {
                const data = await res.json();
                orders = data.orders || [];
            }
        } catch(e) { console.error(e); }

        const card = document.createElement('div');
        card.className = 'glass-card';
        card.style.marginBottom = '1rem';
        card.style.padding = '1.25rem 1rem';

        // 헤더: 태스크 이름 + 수동 실행 버튼
        let headerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                <div style="display:flex; align-items:center; gap:0.5rem;">
                    <div style="background:rgba(0,242,254,0.1); border-radius:8px; width:36px; height:36px; display:flex; align-items:center; justify-content:center;">
                        <i data-lucide="zap" style="color:var(--neon-blue); width:18px; height:18px;"></i>
                    </div>
                    <div>
                        <div style="font-weight:700; font-size:0.95rem; color:#fff;">${task.nickname || task.id}</div>
                        <div style="font-size:0.7rem; color:var(--text-muted);">${task.ticker} • 계좌 ${task.account_no || '-'}</div>
                    </div>
                </div>
                <button class="btn task-execute-btn" data-task-id="${task.id}" style="padding:0.4rem 0.8rem; font-size:0.75rem; background:rgba(0,242,254,0.1); border:1px solid rgba(0,242,254,0.3); color:var(--neon-blue); font-weight:600;">
                    <i data-lucide="send" style="width:12px; height:12px; margin-right:3px;"></i>주문 전송
                </button>
            </div>
        `;

        // 주문 목록 테이블
        let ordersHTML = '';
        if (orders.length === 0) {
            ordersHTML = '<div style="text-align:center; padding:1rem; color:var(--text-muted); font-size:0.8rem;">오늘 실행될 주문이 없습니다.</div>';
        } else {
            ordersHTML = `<table style="width:100%; border-collapse:collapse; font-size:0.8rem;">
                <thead><tr style="border-bottom:1px solid rgba(255,255,255,0.08); color:var(--text-muted); font-size:0.72rem;">
                    <th style="padding:0.5rem; text-align:left;">구분</th>
                    <th style="padding:0.5rem; text-align:right;">수량</th>
                    <th style="padding:0.5rem; text-align:right;">단가</th>
                    <th style="padding:0.5rem; text-align:right;">총액</th>
                </tr></thead><tbody>`;
            orders.forEach(o => {
                const isBuy = (o.type || '').toUpperCase() === 'BUY';
                const color = isBuy ? 'var(--danger)' : 'var(--neon-blue)';
                const typeStr = isBuy ? '매수' : '매도';
                const qty = o.qty || 0;
                const price = o.price || 0;
                ordersHTML += `<tr style="border-bottom:1px solid rgba(255,255,255,0.03);">
                    <td style="padding:0.5rem; color:${color}; font-weight:700;">${typeStr} (${o.order_type})</td>
                    <td style="padding:0.5rem; text-align:right; color:#fff;">${qty}</td>
                    <td style="padding:0.5rem; text-align:right; color:var(--text-muted);">$${price.toFixed(2)}</td>
                    <td style="padding:0.5rem; text-align:right; color:#fff; font-weight:600;">$${(qty * price).toFixed(2)}</td>
                </tr>`;
            });
            ordersHTML += '</tbody></table>';
        }

        // 결과 상태 영역 (실행 후 채워짐)
        let resultHTML = `<div class="task-result-area" id="result-${task.id}" style="margin-top:0.75rem; display:none;"></div>`;

        card.innerHTML = headerHTML + ordersHTML + resultHTML;
        container.appendChild(card);
    }

    // 수동 실행 버튼 이벤트 바인딩
    container.querySelectorAll('.task-execute-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const taskId = btn.dataset.taskId;
            const resultArea = document.getElementById('result-' + taskId);
            
            // 로딩 상태
            btn.disabled = true;
            btn.innerHTML = '<i data-lucide="loader" style="width:12px;height:12px;margin-right:3px;animation:spin 1s linear infinite;"></i>전송 중...';
            resultArea.style.display = 'block';
            resultArea.innerHTML = '<div style="text-align:center; padding:0.5rem; color:var(--text-muted); font-size:0.8rem;">키움 API로 주문 전송 중...</div>';

            try {
                const res = await fetch(`/api/v1/tasks/${taskId}/execute`, {method: 'POST'});
                const data = await res.json();

                if (data.results && data.results.length > 0) {
                    let html = '<div style="border-top:1px solid rgba(255,255,255,0.05); padding-top:0.75rem;">';
                    html += '<div style="font-size:0.75rem; font-weight:600; color:var(--text-muted); margin-bottom:0.5rem;">📋 전송 결과</div>';
                    data.results.forEach(r => {
                        const isSuccess = r.status === 'success';
                        const icon = isSuccess ? '✅' : '❌';
                        const color = isSuccess ? 'var(--success)' : 'var(--danger)';
                        const isBuy = (r.type || '').toUpperCase() === 'BUY';
                        const typeStr = isBuy ? '매수' : '매도';
                        html += `<div style="display:flex; justify-content:space-between; align-items:center; padding:0.4rem 0; border-bottom:1px solid rgba(255,255,255,0.03); font-size:0.8rem;">
                            <span>${icon} ${typeStr} ${r.ticker} ${r.qty}주 @ $${(r.price||0).toFixed(2)}</span>
                            <span style="color:${color}; font-weight:600; font-size:0.75rem;">${r.status === 'success' ? '성공' : '실패'}</span>
                        </div>`;
                        if (r.message) {
                            html += `<div style="font-size:0.65rem; color:var(--text-muted); padding:0.2rem 0 0.3rem 1.2rem;">${r.message}</div>`;
                        }
                    });
                    html += '</div>';
                    resultArea.innerHTML = html;
                } else {
                    resultArea.innerHTML = `<div style="text-align:center; padding:0.5rem; color:var(--text-muted); font-size:0.8rem;">${data.message || '주문 내역 없음'}</div>`;
                }
            } catch(err) {
                resultArea.innerHTML = `<div style="text-align:center; padding:0.5rem; color:var(--danger); font-size:0.8rem;">오류: ${err.message}</div>`;
            }

            btn.disabled = false;
            btn.innerHTML = '<i data-lucide="send" style="width:12px;height:12px;margin-right:3px;"></i>주문 전송';
            lucide.createIcons();
        });
    });

    lucide.createIcons();
}


/* ==========================================================================
   HISTORY TAB
   ========================================================================== */
async function loadGlobalHistory() {
    const tbody = document.getElementById('globalTransactionTableBody');
    if(!tbody) return;
    tbody.innerHTML = '<tr><td colspan="6" style="padding:1rem; color:var(--text-muted);">내역을 불러오는 중...</td></tr>';
    
    if (tasksData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="padding:1rem; color:var(--text-muted);">등록된 태스크가 없습니다.</td></tr>';
        return;
    }
    
    try {
        let allHistory = [];
        for (const task of tasksData) {
            const res = await fetch(`/api/v1/tasks/${task.id}/history`);
            if (res.ok) {
                const data = await res.json();
                if (data.history && data.history.length > 0) {
                    data.history.forEach(h => {
                        h.taskName = task.nickname || task.id;
                        h.ticker = task.ticker;
                        allHistory.push(h);
                    });
                }
            }
        }
        
        tbody.innerHTML = '';
        if (allHistory.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="padding:1rem; color:var(--text-muted);">체결 내역이 없습니다.</td></tr>';
            return;
        }
        
        allHistory.sort((a,b) => new Date(b.date) - new Date(a.date));
        
        allHistory.forEach(item => {
            const isBuy = (item.type || item.action || '').toUpperCase() === 'BUY';
            const color = isBuy ? 'var(--danger)' : 'var(--neon-blue)';
            const typeStr = isBuy ? '매수' : '매도';
            const qty = item.qty || item.quantity || 0;
            const total = qty * item.price;
            
            const tr = document.createElement('tr');
            tr.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
            tr.innerHTML = `
                <td style="padding: 0.75rem; color: #fff; font-size: 0.8rem;">${item.date}</td>
                <td style="padding: 0.75rem; color: ${color}; font-weight: 700;">${typeStr}</td>
                <td style="padding: 0.75rem;">
                    <div style="font-weight: 600; color: #fff;">${item.ticker}</div>
                    <div style="font-size: 0.7rem; color: var(--text-muted);">${item.taskName}</div>
                </td>
                <td style="padding: 0.75rem; color: #fff;">${qty}</td>
                <td style="padding: 0.75rem; color: var(--text-muted);">$${item.price.toFixed(2)}</td>
                <td style="padding: 0.75rem; color: #fff; font-weight: 600;">$${total.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });
        
        // Setup copy button
        const copyBtn = document.getElementById('copyHistoryBtn');
        if(copyBtn) {
            copyBtn.onclick = () => {
                let text = "일자\t구분\t종목\t태스크\t수량\t단가\t총액\n";
                allHistory.forEach(item => {
                    const isBuy = (item.type || item.action || '').toUpperCase() === 'BUY';
                    const typeStr = isBuy ? '매수' : '매도';
                    const qty = item.qty || item.quantity || 0;
                    const total = qty * item.price;
                    text += `${item.date}\t${typeStr}\t${item.ticker}\t${item.taskName}\t${qty}\t${item.price.toFixed(2)}\t${total.toFixed(2)}\n`;
                });
                navigator.clipboard.writeText(text).then(() => {
                    alert('엑셀용 데이터가 클립보드에 복사되었습니다. 엑셀에 붙여넣기(Ctrl+V) 하세요.');
                });
            };
        }
        
    } catch (e) {
        console.error(e);
        const tbody = document.getElementById('globalTransactionTableBody');
        if(tbody) {
            tbody.innerHTML = '<tr><td colspan="6" style="padding:1rem; text-align:center; color:var(--danger);">오류가 발생했습니다.</td></tr>';
        }
    }
}

/* ==========================================================================
   SETTINGS TAB
   ========================================================================== */
async function loadGlobalSettings() {
    try {
        const res = await fetch('/api/v1/settings');
        if (res.ok) {
            const data = await res.json();
            document.getElementById('globalOrderTime').value = data.order_execution_time || "06:00";
            document.getElementById('globalSyncTime').value = data.sync_execution_time || "06:10";
            document.getElementById('globalSchedulerActive').checked = data.scheduler_active !== false;
        }
    } catch (e) {
        console.error("Failed to load settings", e);
    }
}

document.getElementById('saveGlobalSettingsBtn').addEventListener('click', async () => {
    const payload = {
        order_execution_time: document.getElementById('globalOrderTime').value,
        sync_execution_time: document.getElementById('globalSyncTime').value,
        scheduler_active: document.getElementById('globalSchedulerActive').checked
    };
    try {
        const res = await fetch('/api/v1/settings', {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            alert('글로벌 시스템 설정이 성공적으로 저장 및 반영되었습니다.');
        } else {
            alert('설정 저장 실패');
        }
    } catch (e) {
        alert('오류 발생');
    }
});

async function loadSystemLogs() {
    const viewer = document.getElementById('systemLogViewer');
    try {
        viewer.innerHTML = '로딩 중...';
        const res = await fetch('/api/v1/logs');
        if (res.ok) {
            const data = await res.json();
            if(data.logs) {
                viewer.innerHTML = data.logs.join('<br>') || '로그 내용이 없습니다.';
                viewer.scrollTop = viewer.scrollHeight;
            }
        }
    } catch (e) {
        viewer.innerHTML = '로그를 불러오지 못했습니다.';
    }
}

/* ==========================================================================
   MODALS (TASK / BATCH)
   ========================================================================== */
let editingTaskId = null;

function setupModals() {
    const taskModal = document.getElementById('taskModal');
    const batchModal = document.getElementById('batchModal');
    
    document.getElementById('openNewTaskModalBtn').addEventListener('click', () => {
        editingTaskId = null;
        document.getElementById('taskModalTitle').innerHTML = '<i data-lucide="plus-circle" style="color: var(--neon-blue); width: 20px; height: 20px;"></i><span>새 테스크 추가</span>';
        document.getElementById('taskModalDeleteBtn').style.display = 'none';
        
        document.getElementById('taskModalAccountNo').value = '';
        document.getElementById('taskModalNickname').value = '';
        document.getElementById('taskModalTicker').value = 'SOXL';
        document.getElementById('taskModalSeed').value = '10000';
        taskModal.style.display = 'flex';
        lucide.createIcons();
    });

    document.getElementById('closeTaskModalBtn').addEventListener('click', () => {
        taskModal.style.display = 'none';
    });
    
    document.getElementById('closeBatchModalBtn').addEventListener('click', () => {
        batchModal.style.display = 'none';
    });
    
    document.getElementById('taskModalSaveBtn').addEventListener('click', async () => {
        const payload = {
            strategy: document.getElementById('taskModalStrategy').value,
            account_no: document.getElementById('taskModalAccountNo').value,
            nickname: document.getElementById('taskModalNickname').value,
            ticker: document.getElementById('taskModalTicker').value.toUpperCase(),
            seed_amt: parseFloat(document.getElementById('taskModalSeed').value),
            split_count: parseInt(document.getElementById('taskModalSplitCount').value),
            safe_buy_pct: parseFloat(document.getElementById('taskModalSafeBuy').value),
            safe_sell_pct: parseFloat(document.getElementById('taskModalSafeSell').value),
            agg_buy_pct: parseFloat(document.getElementById('taskModalAggBuy').value),
            agg_sell_pct: parseFloat(document.getElementById('taskModalAggSell').value),
            update_period: parseInt(document.getElementById('taskModalUpdatePeriod').value),
            compounding_profit_rate: parseFloat(document.getElementById('taskModalProfitRate').value),
            compounding_loss_rate: parseFloat(document.getElementById('taskModalLossRate').value)
        };

        try {
            let res;
            if (editingTaskId) {
                res = await fetch(`/api/v1/tasks/${editingTaskId}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
            } else {
                res = await fetch('/api/v1/tasks', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
            }

            if (res.ok) {
                taskModal.style.display = 'none';
                refreshAllData();
            } else {
                alert('테스크 저장 실패!');
            }
        } catch (e) {
            console.error(e);
            alert('오류 발생');
        }
    });

    document.getElementById('taskModalDeleteBtn').addEventListener('click', async () => {
        if (!editingTaskId) return;
        if (!confirm('정말 이 테스크를 삭제하시겠습니까? 관련 데이터가 모두 지워집니다.')) return;
        
        try {
            const res = await fetch(`/api/v1/tasks/${editingTaskId}`, { method: 'DELETE' });
            if (res.ok) {
                taskModal.style.display = 'none';
                refreshAllData();
            }
        } catch (e) {
            alert('삭제 실패');
        }
    });
}

/* ==========================================================================
   SIMULATOR TAB
   ========================================================================== */
function loadSimulatorTasks() {
    const selector = document.getElementById('simTaskSelector');
    if (!selector) return;
    
    const selectedVal = selector.value;
    
    selector.innerHTML = '<option value="">-- 직접 입력 / 선택 해제 --</option>';
    tasksData.forEach(task => {
        const opt = document.createElement('option');
        opt.value = task.id;
        opt.textContent = `${task.nickname || task.id} (${task.ticker} • $${task.seed_amt})`;
        selector.appendChild(opt);
    });
    
    selector.value = selectedVal;
}

function setupSimulator() {
    const simTaskSelector = document.getElementById('simTaskSelector');
    const simTargetTicker = document.getElementById('simTargetTicker');
    const simManualTickerWrapper = document.getElementById('simManualTickerWrapper');
    const simTargetTickerManual = document.getElementById('simTargetTickerManual');
    const runSimulationBtn = document.getElementById('runSimulationBtn');
    
    const presetAggressive = document.getElementById('presetAggressive');
    const presetActive = document.getElementById('presetActive');
    
    simTaskSelector.addEventListener('change', () => {
        const taskId = simTaskSelector.value;
        if (!taskId) return;
        
        const task = tasksData.find(t => t.id === taskId);
        if (!task) return;
        
        const ticker = task.ticker || 'SOXL';
        if (ticker === 'SOXL' || ticker === 'TQQQ') {
            simTargetTicker.value = ticker;
            simManualTickerWrapper.style.display = 'none';
        } else {
            simTargetTicker.value = 'MANUAL';
            simTargetTickerManual.value = ticker;
            simManualTickerWrapper.style.display = 'block';
        }
        
        document.getElementById('simSeedAmt').value = task.seed_amt || 10000;
        document.getElementById('simSafeBuyPct').value = task.safe_buy_pct !== undefined ? task.safe_buy_pct : 3.0;
        document.getElementById('simSafeSellPct').value = task.safe_sell_pct !== undefined ? task.safe_sell_pct : 0.2;
        document.getElementById('simAggBuyPct').value = task.agg_buy_pct !== undefined ? task.agg_buy_pct : 5.0;
        document.getElementById('simAggSellPct').value = task.agg_sell_pct !== undefined ? task.agg_sell_pct : 2.5;
        document.getElementById('simSplitCount').value = task.split_count || 7;
        document.getElementById('simUpdatePeriod').value = task.update_period || 10;
        document.getElementById('simCompoundingProfitRate').value = task.compounding_profit_rate || 80;
        document.getElementById('simCompoundingLossRate').value = task.compounding_loss_rate || 30;
        
        runSimulation();
    });
    
    simTargetTicker.addEventListener('change', (e) => {
        if (e.target.value === 'MANUAL') {
            simManualTickerWrapper.style.display = 'block';
        } else {
            simManualTickerWrapper.style.display = 'none';
        }
    });
    
    presetAggressive.addEventListener('click', () => {
        document.getElementById('simSafeBuyPct').value = 3.0;
        document.getElementById('simSafeSellPct').value = 0.2;
        document.getElementById('simAggBuyPct').value = 5.0;
        document.getElementById('simAggSellPct').value = 2.5;
        document.getElementById('simSplitCount').value = 7;
        document.getElementById('simUpdatePeriod').value = 10;
        document.getElementById('simCompoundingProfitRate').value = 80;
        document.getElementById('simCompoundingLossRate').value = 30;
        simTaskSelector.value = '';
    });
    
    presetActive.addEventListener('click', () => {
        document.getElementById('simSafeBuyPct').value = 2.5;
        document.getElementById('simSafeSellPct').value = 0.5;
        document.getElementById('simAggBuyPct').value = 4.0;
        document.getElementById('simAggSellPct').value = 2.0;
        document.getElementById('simSplitCount').value = 7;
        document.getElementById('simUpdatePeriod').value = 10;
        document.getElementById('simCompoundingProfitRate').value = 80;
        document.getElementById('simCompoundingLossRate').value = 30;
        simTaskSelector.value = '';
    });
    
    runSimulationBtn.addEventListener('click', () => {
        simTaskSelector.value = '';
        runSimulation();
    });
    
    const today = new Date();
    const formattedToday = today.toISOString().split('T')[0];
    document.getElementById('simEndDate').value = formattedToday;
}

async function runSimulation() {
    const simTaskSelector = document.getElementById('simTaskSelector');
    const taskId = simTaskSelector ? simTaskSelector.value : '';
    const simTargetTicker = document.getElementById('simTargetTicker');
    const simTargetTickerManual = document.getElementById('simTargetTickerManual');
    
    let ticker = simTargetTicker.value;
    if (ticker === 'MANUAL') {
        ticker = simTargetTickerManual.value.trim().toUpperCase();
        if (!ticker) {
            alert('직접 입력할 티커명을 기입해 주세요.');
            return;
        }
    }
    
    const seedAmt = parseFloat(document.getElementById('simSeedAmt').value) || 10000;
    const startDate = document.getElementById('simStartDate').value || '2018-07-27';
    const endDate = document.getElementById('simEndDate').value;
    
    const safeBuyPct = parseFloat(document.getElementById('simSafeBuyPct').value) || 0;
    const safeSellPct = parseFloat(document.getElementById('simSafeSellPct').value) || 0;
    const aggBuyPct = parseFloat(document.getElementById('simAggBuyPct').value) || 0;
    const aggSellPct = parseFloat(document.getElementById('simAggSellPct').value) || 0;
    
    const splitCount = parseInt(document.getElementById('simSplitCount').value) || 7;
    const updatePeriod = parseInt(document.getElementById('simUpdatePeriod').value) || 10;
    const compoundingProfitRate = parseFloat(document.getElementById('simCompoundingProfitRate').value) || 80;
    const compoundingLossRate = parseFloat(document.getElementById('simCompoundingLossRate').value) || 30;
    
    showLoading(true);
    
    try {
        let res;
        if (taskId) {
            res = await fetch(`/api/v1/tasks/${taskId}/matching`, {
                method: 'GET'
            });
        } else {
            const payload = {
                ticker,
                start_date: startDate,
                end_date: endDate || null,
                seed_amt: seedAmt,
                safe_buy_pct: safeBuyPct,
                safe_sell_pct: safeSellPct,
                agg_buy_pct: aggBuyPct,
                agg_sell_pct: aggSellPct,
                split_count: splitCount,
                update_period: updatePeriod,
                compounding_profit_rate: compoundingProfitRate,
                compounding_loss_rate: compoundingLossRate
            };
            
            res = await fetch('/api/v1/backtest', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
        }
        
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.message || '서버 연산 중 오류가 발생했습니다.');
        }
        
        const result = await res.json();
        
        renderSimulationSummary(result.summary);
        renderSimulationTable(result.detailedTxTable);
        renderSimulationChart(result.history);
        
    } catch (e) {
        console.error(e);
        alert("시뮬레이션 중 오류가 발생했습니다: " + e.message);
    } finally {
        showLoading(false);
    }
}

function renderSimulationSummary(summary) {
    const totalReturn = summary.totalReturn;
    const rProfVal = summary.realizedProfitVal;
    
    const trEl = document.getElementById('simTotalReturn');
    trEl.innerText = `${totalReturn >= 0 ? '+' : ''}${totalReturn.toFixed(2)}%`;
    trEl.className = totalReturn >= 0 ? 'text-up font-title' : 'text-down font-title';
    
    const mddEl = document.getElementById('simMDD');
    mddEl.innerText = `${summary.mdd.toFixed(2)}%`;
    
    const rpEl = document.getElementById('simRealizedProfit');
    rpEl.innerText = `$${rProfVal.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    rpEl.className = rProfVal >= 0 ? 'text-up font-title' : 'text-down font-title';
    
    const cagrEl = document.getElementById('simCAGR');
    cagrEl.innerText = `${summary.cagr >= 0 ? '+' : ''}${summary.cagr.toFixed(2)}%`;
    cagrEl.className = summary.cagr >= 0 ? 'text-up' : 'text-down';
}

function renderSimulationTable(detailedTxTable) {
    const tbody = document.getElementById('simDetailTableBody');
    if (!tbody) return;
    
    if (!detailedTxTable || detailedTxTable.length === 0) {
        tbody.innerHTML = '<tr><td colspan="17" style="padding:1rem; text-align:center; color:var(--text-muted);">거래 내역이 없습니다.</td></tr>';
        return;
    }
    
    const formatCurrency = (val, symbol = '$', decimals = 2) => {
        if (val === undefined || val === '' || val === null || val === '-') return '-';
        return `${symbol}${parseFloat(val).toLocaleString(undefined, {minimumFractionDigits: decimals, maximumFractionDigits: decimals})}`;
    };
    
    tbody.innerHTML = detailedTxTable.map(r => {
        const modeColor = r.mode.includes('공세') ? 'color: var(--danger); font-weight:700;' : 'color: var(--success); font-weight:700;';
        const buyColor = r.buyQty ? 'background: rgba(0, 230, 118, 0.04); font-weight:600;' : '';
        const sellColor = r.sellQty ? 'background: rgba(255, 23, 68, 0.04); font-weight:600;' : '';
        const compoundingColor = r.compoundingAmt ? 'background: rgba(157, 78, 221, 0.08); font-weight:700;' : '';
        
        return `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
              <td style="padding: 0.45rem 0.4rem; font-weight:600; text-align:center;">${r.date}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right;">${formatCurrency(r.close, '$', 2)}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:center; ${modeColor}">${r.mode}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right;">${formatCurrency(r.buyLimitAmt, '$', 2)}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:center; ${buyColor}">${r.buyQty || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; ${buyColor}">${formatCurrency(r.buyAmt, '$', 2)}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right;">${formatCurrency(r.targetSell, '$', 2)}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:center; ${sellColor}">${r.sellDate || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; ${sellColor}">${formatCurrency(r.sellPrice, '$', 2)}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:center; ${sellColor}">${r.sellQty || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; ${sellColor}">${formatCurrency(r.sellAmt, '$', 2)}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right;">${formatCurrency(r.cash, '$', 2)}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; color: var(--success); font-weight:700;">${formatCurrency(r.todayRealized, '$', 2)}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; color: var(--success);">${formatCurrency(r.profitAmt, '$', 2)}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; font-weight:700;">${formatCurrency(r.accumProfit, '$', 2)}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; color: #a29bfe; ${compoundingColor}">${formatCurrency(r.compoundingAmt, '$', 2)}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; color: #e84393; ${compoundingColor}">${formatCurrency(r.updatedCompoundingCash, '$', 2)}</td>
            </tr>
        `;
    }).join('');
}

function renderSimulationChart(history) {
    const chartEl = document.querySelector("#simulationChart");
    if (!chartEl) return;
    
    if (simulationChart) {
        simulationChart.destroy();
    }
    
    const categories = history.map(h => h.date);
    const assetData = history.map(h => Math.round(h.totalAsset));
    const cashData = history.map(h => Math.round(h.cash));
    const mddData = history.map(h => parseFloat(h.mdd.toFixed(2)));
    
    const options = {
        series: [
            { name: '총 자산 가치', type: 'area', data: assetData },
            { name: '보유 예수금', type: 'line', data: cashData },
            { name: 'MDD (%)', type: 'line', data: mddData }
        ],
        chart: {
            height: 280,
            type: 'line',
            background: 'transparent',
            toolbar: { show: false }
        },
        colors: ['#9d4edd', '#00f2fe', '#ff3366'],
        stroke: {
            width: [3, 2, 2],
            curve: 'smooth',
            dashArray: [0, 4, 0]
        },
        fill: {
            type: ['gradient', 'solid', 'solid'],
            gradient: {
                type: 'vertical',
                shadeIntensity: 0.5,
                inverseColors: false,
                opacityFrom: [0.2, 0, 0],
                opacityTo: [0.01, 0, 0],
                stops: [0, 100]
            }
        },
        xaxis: {
            categories: categories,
            labels: {
                show: true,
                rotate: -30,
                rotateAlways: false,
                style: { colors: '#9aa0a6', fontSize: '10px' },
                tickAmount: 10
            },
            axisBorder: { show: false },
            axisTicks: { show: false }
        },
        yaxis: [
            {
                title: { text: '자산 가치 ($)', style: { color: '#9aa0a6' } },
                labels: {
                    style: { colors: '#9aa0a6' },
                    formatter: (val) => `$${Math.round(val).toLocaleString()}`
                }
            },
            {
                show: false
            },
            {
                opposite: true,
                title: { text: 'MDD (%)', style: { color: '#ff3366' } },
                labels: {
                    style: { colors: '#ff3366' },
                    formatter: (val) => `${val}%`
                },
                min: 0,
                max: 100,
                reversed: true
            }
        ],
        grid: {
            borderColor: 'rgba(255,255,255,0.05)',
            yaxis: { lines: { show: true } }
        },
        legend: {
            show: true,
            position: 'top',
            labels: { colors: '#9aa0a6' }
        },
        tooltip: {
            theme: 'dark',
            x: { show: true },
            shared: true,
            intersect: false
        }
    };
    
    simulationChart = new ApexCharts(chartEl, options);
    simulationChart.render();
}

function openTaskModal(task) {
    editingTaskId = task.id;
    
    document.getElementById('taskModalTitle').innerHTML = '<i data-lucide="settings" style="color: var(--neon-blue); width: 20px; height: 20px;"></i><span>테스크 설정 수정</span>';
    document.getElementById('taskModalDeleteBtn').style.display = 'flex';
    
    document.getElementById('taskModalStrategy').value = task.strategy || 'SURFER_BATCH';
    document.getElementById('taskModalAccountNo').value = task.account_no || '';
    document.getElementById('taskModalNickname').value = task.nickname || '';
    document.getElementById('taskModalTicker').value = task.ticker || 'SOXL';
    document.getElementById('taskModalSeed').value = task.seed_amt || 10000;
    document.getElementById('taskModalSafeBuy').value = task.safe_buy_pct || 3.0;
    document.getElementById('taskModalSafeSell').value = task.safe_sell_pct || 0.2;
    document.getElementById('taskModalAggBuy').value = task.agg_buy_pct || 5.0;
    document.getElementById('taskModalAggSell').value = task.agg_sell_pct || 2.5;
    document.getElementById('taskModalSplitCount').value = task.split_count || 7;
    document.getElementById('taskModalUpdatePeriod').value = task.update_period || 10;
    document.getElementById('taskModalProfitRate').value = task.compounding_profit_rate || 80;
    document.getElementById('taskModalLossRate').value = task.compounding_loss_rate || 30;
    
    document.getElementById('taskModal').style.display = 'flex';
    lucide.createIcons();
}

async function openBatchModal(taskId) {
    const batchModal = document.getElementById('batchModal');
    const content = document.getElementById('batchModalContent');
    content.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted);">데이터 불러오는 중...</div>';
    batchModal.style.display = 'flex';
    
    try {
        const res = await fetch(`/api/v1/tasks/${taskId}/batches`);
        if (res.ok) {
            const data = await res.json();
            const batches = data.batches || [];
            if (batches.length === 0) {
                content.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--text-muted);">진행 중인 사이클이 없습니다.</div>';
                return;
            }
            
            content.innerHTML = '';
            batches.forEach((batch, index) => {
                const card = document.createElement('div');
                card.style.background = 'rgba(255,255,255,0.03)';
                card.style.border = '1px solid rgba(255,255,255,0.08)';
                card.style.borderRadius = '8px';
                card.style.padding = '1rem';
                card.innerHTML = `
                    <div style="font-weight:700; font-size:0.85rem; color:var(--text-primary); margin-bottom:0.5rem;">[${index+1}회차 사이클] ${batch.start_date || '진행중'}</div>
                    <div style="font-size:0.75rem; color:var(--text-muted);">
                        평단가: $${batch.avg_price ? batch.avg_price.toFixed(2) : '0.00'}<br>
                        수량: ${batch.total_quantity || 0}<br>
                        모드: ${batch.mode === 'AGGRESSIVE' ? '<span style="color:var(--danger);">공세모드</span>' : '<span style="color:var(--neon-blue);">안전모드</span>'}
                    </div>
                `;
                content.appendChild(card);
            });
        }
    } catch (e) {
        content.innerHTML = '<div style="text-align:center; padding:2rem; color:var(--danger);">오류가 발생했습니다.</div>';
    }
}

