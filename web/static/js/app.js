// 기본 상수 설정
const APP_VERSION = '1.25.1';
const DEFAULT_CLIENT_ID = '335241298668-25j14dtk9qsc9bl2ij6ugm363kqo3vsk.apps.googleusercontent.com';
const DEFAULT_SHEET_ID = '1PZvpv4OAzosC4gRbcBR2NcCgbroR2-4VT9A9TmOmr0U';

// IndexedDB 비동기 저장 헬퍼 (LocalStorage 5MB 한도 초과 해결용)
const dbStore = {
  db: null,
  init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('WaveSurferDB', 1);
      request.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('kvStore')) {
          db.createObjectStore('kvStore');
        }
      };
      request.onsuccess = (e) => {
        this.db = e.target.result;
        resolve();
      };
      request.onerror = (e) => {
        console.error('IndexedDB 초기화 실패:', e.target.error);
        reject(e.target.error);
      };
    });
  },
  get(key) {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        return resolve(null);
      }
      try {
        const tx = this.db.transaction('kvStore', 'readonly');
        const store = tx.objectStore('kvStore');
        const request = store.get(key);
        request.onsuccess = (e) => {
          resolve(e.target.result || null);
        };
        request.onerror = (e) => {
          reject(e.target.error);
        };
      } catch (err) {
        reject(err);
      }
    });
  },
  set(key, val) {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        return reject(new Error('IndexedDB가 초기화되지 않았습니다.'));
      }
      try {
        const tx = this.db.transaction('kvStore', 'readwrite');
        const store = tx.objectStore('kvStore');
        const request = store.put(val, key);
        request.onsuccess = () => {
          resolve();
        };
        request.onerror = (e) => {
          reject(e.target.error);
        };
      } catch (err) {
        reject(err);
      }
    });
  },
  delete(key) {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        return resolve();
      }
      try {
        const tx = this.db.transaction('kvStore', 'readwrite');
        const store = tx.objectStore('kvStore');
        const request = store.delete(key);
        request.onsuccess = () => {
          resolve();
        };
        request.onerror = (e) => {
          reject(e.target.error);
        };
      } catch (err) {
        reject(err);
      }
    });
  },
  clear() {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        return resolve();
      }
      try {
        const tx = this.db.transaction('kvStore', 'readwrite');
        const store = tx.objectStore('kvStore');
        const request = store.clear();
        request.onsuccess = () => {
          resolve();
        };
        request.onerror = (e) => {
          reject(e.target.error);
        };
      } catch (err) {
        reject(err);
      }
    });
  },
  getAllKeys() {
    return new Promise((resolve, reject) => {
      if (!this.db) {
        return resolve([]);
      }
      try {
        const tx = this.db.transaction('kvStore', 'readonly');
        const store = tx.objectStore('kvStore');
        const request = store.getAllKeys ? store.getAllKeys() : null;
        if (request) {
          request.onsuccess = (e) => {
            resolve(e.target.result || []);
          };
          request.onerror = (e) => {
            reject(e.target.error);
          };
        } else {
          // Fallback using cursor
          const keys = [];
          const cursorReq = store.openKeyCursor ? store.openKeyCursor() : store.openCursor();
          cursorReq.onsuccess = (e) => {
            const cursor = e.target.result;
            if (cursor) {
              keys.push(cursor.key);
              cursor.continue();
            } else {
              resolve(keys);
            }
          };
          cursorReq.onerror = (e) => {
            reject(e.target.error);
          };
        }
      } catch (err) {
        reject(err);
      }
    });
  }
};

// 전역 상태 관리
let config = {
  clientId: DEFAULT_CLIENT_ID,
  sheets: [], 
  activeSheetId: ''
};
let accessToken = '';
let tokenExpiresAt = 0;
let tokenClient = null;
// 파싱된 일지 데이터 저장용
let jjDailyData = [];
let rawTransactions = []; // 차트 및 카드 렌더링용 변환 거래 데이터
let combinedRawData = []; // 예약 주문표(Order Guide) 데이터 저장용 전역 변수
// 요약 상단 영역 데이터
let summaryData = {
  ticker: 'SOXL',
  totalAsset: 0,
  totalCost: 0,
  totalProfit: 0,
  totalProfitRate: 0,
  realizedProfit: 0,
  currentCash: 0,
  currentHoldings: 0
};
// 모달/설정 탭 내 임시 시트 리스트 보관용
let tempSheets = [];
// 차트 인스턴스 저장용
let assetTrendChart = null;
let monthlyChart = null;
let simulationChart = null;
let simulationResult = null;
// DOM 요소 참조
const loadingOverlay = document.getElementById('loadingOverlay');
const welcomeScreen = document.getElementById('welcomeScreen');
const welcomeSetupSection = document.getElementById('welcomeSetupSection');
const welcomeLoginSection = document.getElementById('welcomeLoginSection');
const googleLoginBtn = document.getElementById('googleLoginBtn');
const mainDashboard = document.getElementById('mainDashboard');
const setupBtn = document.getElementById('setupBtn');
const refreshBtn = document.getElementById('refreshBtn');
const settingsBtn = document.getElementById('settingsBtn');
const logoutBtn = document.getElementById('logoutBtn');
const activeSheetSelector = document.getElementById('activeSheetSelector');
const bottomNavBar = document.getElementById('bottomNavBar');
// 설정 탭 DOM 요소
const themeSelector = document.getElementById('themeSelector');
const clientIdInput = document.getElementById('clientIdInput');
const newSheetNameInput = document.getElementById('newSheetNameInput');
const newSheetIdInput = document.getElementById('newSheetIdInput');
const addSheetBtn = document.getElementById('addSheetBtn');
const sheetListContainer = document.getElementById('sheetListContainer');
const settingsResetBtn = document.getElementById('settingsResetBtn');
// 테이블 및 필터 DOM 요소
const dailyCardList = document.getElementById('dailyCardList');
const transactionCardList = document.getElementById('transactionCardList');
const transactionSearch = document.getElementById('transactionSearch');
const transactionTypeFilter = document.getElementById('transactionTypeFilter');
const transactionSort = document.getElementById('transactionSort');
// 시뮬레이터 탭 DOM 요소
const runSimulationBtn = document.getElementById('runSimulationBtn');
const simTargetTicker = document.getElementById('simTargetTicker');
const simManualTickerWrapper = document.getElementById('simManualTickerWrapper');
const simTargetTickerManual = document.getElementById('simTargetTickerManual');
const simStartDate = document.getElementById('simStartDate');
const simEndDate = document.getElementById('simEndDate');
const simSafeBuyPct = document.getElementById('simSafeBuyPct');
const simSafeSellPct = document.getElementById('simSafeSellPct');
const simAggBuyPct = document.getElementById('simAggBuyPct');
const simAggSellPct = document.getElementById('simAggSellPct');
const simSplitCount = document.getElementById('simSplitCount');
const simUpdatePeriod = document.getElementById('simUpdatePeriod');
const simCompoundingProfitRate = document.getElementById('simCompoundingProfitRate');
const simCompoundingLossRate = document.getElementById('simCompoundingLossRate');
const simSeedAmt = document.getElementById('simSeedAmt');
const simRealizedProfit = document.getElementById('simRealizedProfit');
const simDetailTableBody = document.getElementById('simDetailTableBody');
const presetAggressive = document.getElementById('presetAggressive');
const presetActive = document.getElementById('presetActive');

// 백테스트 결과 저장/관리 DOM 바인딩
const simSavedList = document.getElementById('simSavedList');
const deleteSimBtn = document.getElementById('deleteSimBtn');
const importSimFileBtn = document.getElementById('importSimFileBtn');
const simFileInput = document.getElementById('simFileInput');
const saveSimResultBtn = document.getElementById('saveSimResultBtn');
const exportSimJsonBtn = document.getElementById('exportSimJsonBtn');
const simSaveActionArea = document.getElementById('simSaveActionArea');

// 초기화
document.addEventListener('DOMContentLoaded', async () => {
  loadConfig();
  initTheme();
  initTabs();
  initEventListeners();
  
  try {
    await dbStore.init();
    
    // v1.17.0 1회성 IndexedDB 내 옛날 규격 캐시 소거 가드
    const migrationFlag = 'stock_db_indexeddb_migrated_v1.17.0';
    if (!localStorage.getItem(migrationFlag)) {
      const keys = await dbStore.getAllKeys();
      const promises = keys.map(key => {
        if (key.startsWith('stock_db_cache_') || key.startsWith('stock_db_cache_sim_all_')) {
          return dbStore.delete(key);
        }
        return Promise.resolve();
      });
      await Promise.all(promises);
      localStorage.setItem(migrationFlag, 'true');
      console.log('[마이그레이션 가드] IndexedDB 내 옛날 규격 캐시를 1회성으로 안전하게 소거했습니다.');
    }
    
    await loadSavedSimList();
  } catch (err) {
    console.error('IndexedDB 초기화 실패:', err);
  }
  
  lucide.createIcons();
  loadAppVersion();
  
  if (typeof google !== 'undefined') {
    initGoogleAuth();
  } else {
    window.onload = () => {
      if (typeof google !== 'undefined') {
        initGoogleAuth();
      }
    };
  }
});

// 앱 버전 동적 로드 및 UI 바인딩
function loadAppVersion() {
  const headerEl = document.getElementById('appVersionHeader');
  if (headerEl) {
    headerEl.innerText = `v${APP_VERSION}`;
  }
  const settingsEl = document.getElementById('appVersionSettings');
  if (settingsEl) {
    settingsEl.innerHTML = `현재 프로그램 버전: <strong>v${APP_VERSION}</strong>`;
  }
}

// 오전 8시 기점 캐시 유효성 판정 알고리즘
function isCacheValid(lastUpdatedTimestamp) {
  if (!lastUpdatedTimestamp) return false;
  const now = new Date();
  const lastUpdate = new Date(parseInt(lastUpdatedTimestamp, 10));
  
  // 오늘의 오전 8시 기준 시간 객체 생성
  const today8AM = new Date();
  today8AM.setHours(8, 0, 0, 0);
  
  // 1. 현재 시간이 오늘 오전 8시 이전인 경우: 어제 오전 8시 이후에 업데이트된 캐시가 있으면 유효
  if (now < today8AM) {
    const yesterday8AM = new Date(today8AM.getTime() - 24 * 60 * 60 * 1000);
    return lastUpdate >= yesterday8AM;
  }
  
  // 2. 현재 시간이 오늘 오전 8시 이후인 경우: 오늘 오전 8시 이후에 업데이트되었어야 캐시 유효
  return lastUpdate >= today8AM;
}
// 테마 초기 설정
function initTheme() {
  const savedTheme = localStorage.getItem('stock_db_selected_theme') || 'theme-domino';
  themeSelector.value = savedTheme;
  applyTheme(savedTheme);
}
// 테마 변경 적용 함수
function applyTheme(themeName) {
  document.body.className = themeName;
  localStorage.setItem('stock_db_selected_theme', themeName);
  // 테마에 맞는 색상으로 차트 리렌더링
  if (jjDailyData.length > 0) {
    renderAssetTrendChart();
    renderMonthlyChart();
  }
}
// 테마별 컬러 토큰 구하기
function getThemeChartOptions() {
  const bodyClass = document.body.className;
  if (bodyClass.includes('theme-rich')) {
    return {
      colors: ['#00f2fe', '#ff007f', '#00e676'], // 블루, 핑크, 그린
      foreColor: '#a7a7d4'
    };
  } else if (bodyClass.includes('theme-bank')) {
    return {
      colors: ['#3182f6', '#a0aec0', '#2ecc71'], // 토스블루, 그레이, 연두
      foreColor: '#909bb0'
    };
  } else {
    // theme-domino (기본값)
    return {
      colors: ['#9d4edd', '#ff007f', '#00e676'], // 퍼플, 핑크, 그린
      foreColor: '#9aa0a6'
    };
  }
}
// 하단 고정 탭 바 컨트롤
function initTabs() {
  const navItems = document.querySelectorAll('.nav-item');
  const tabContents = document.querySelectorAll('.tab-content');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetTab = item.getAttribute('data-tab');
      // 탭 버튼 활성화 클래스 토글
      navItems.forEach(nav => nav.classList.remove('active'));
      item.classList.add('active');
      // 탭 컨텐츠 보임 제어
      tabContents.forEach(content => {
        if (content.id === targetTab) {
          content.style.display = 'block';
        } else {
          content.style.display = 'none';
        }
      });
      
      // 설정 탭으로 갈 경우 임시 리스트 렌더링 갱신
      if (targetTab === 'system-tab' || targetTab === 'settings-tab') {
        tempSheets = [...config.sheets];
        renderTempSheetList();
      }
    });
  });
}
// 구글 OAuth 클라이언트 초기화
function initGoogleAuth() {
  // 로컬 파일 검토용 우회 제어
  if (window.location.protocol === 'file:') {
    showDashboard();
    fetchData();
    return;
  }
  if (!config.clientId) return;
  try {
    tokenClient = google.accounts.oauth2.initTokenClient({
      client_id: config.clientId,
      scope: 'https://www.googleapis.com/auth/spreadsheets',
      callback: (tokenResponse) => {
        if (tokenResponse && tokenResponse.access_token) {
          accessToken = tokenResponse.access_token;
          tokenExpiresAt = Date.now() + (tokenResponse.expires_in * 1000);
          
          localStorage.setItem('stock_db_access_token', accessToken);
          localStorage.setItem('stock_db_token_expires_at', tokenExpiresAt);
          
          updateSheetSelectorUI();
          showDashboard();
          fetchData();
        }
      },
    });
    
    if (isTokenValid() && config.activeSheetId) {
      updateSheetSelectorUI();
      showDashboard();
      fetchData();
    } else {
      showWelcome();
    }
  } catch (error) {
    console.error('Google Auth 초기화 실패:', error);
  }
}
// 토큰의 유효성 검사
function isTokenValid() {
  return accessToken && tokenExpiresAt > Date.now();
}
// 이벤트 리스너 설정
function initEventListeners() {
  setupBtn.addEventListener('click', () => {
    // 웰컴 화면에서 설정 탭으로 바로 이동시키기
    showDashboard();
    const settingsTabBtn = document.querySelector('[data-tab="settings-tab"]');
    if (settingsTabBtn) settingsTabBtn.click();
  });
  addSheetBtn.addEventListener('click', handleAddSheet);
  settingsResetBtn.addEventListener('click', resetConfig);
  googleLoginBtn.addEventListener('click', loginWithGoogle);
  logoutBtn.addEventListener('click', logout);
  refreshBtn.addEventListener('click', async () => {
    if (isTokenValid()) {
      // IndexedDB의 모든 대시보드/시뮬레이터 캐시 삭제 (강제 새로고침 시 타 계좌 캐시 불일치 차단)
      try {
        const keys = await dbStore.getAllKeys();
        const promises = keys.map(key => {
          if (key.startsWith('stock_db_cache_') || key.startsWith('stock_db_cache_sim_all_')) {
            return dbStore.delete(key);
          }
          return Promise.resolve();
        });
        await Promise.all(promises);
      } catch (err) {
        console.error('캐시 무효화 중 오류 발생:', err);
      }
      await fetchData(true);
    } else {
      loginWithGoogle();
    }
  });
  activeSheetSelector.addEventListener('change', (e) => {
    config.activeSheetId = e.target.value;
    localStorage.setItem('stock_db_active_sheet_id', config.activeSheetId);
    fetchData();
  });
  themeSelector.addEventListener('change', (e) => {
    applyTheme(e.target.value);
  });
  transactionSearch.addEventListener('input', renderTransactionCards);
  transactionTypeFilter.addEventListener('change', renderTransactionCards);
  transactionSort.addEventListener('change', renderTransactionCards);
  // 시뮬레이터 이벤트 리스너 및 프리셋 바인딩
  if (runSimulationBtn) runSimulationBtn.addEventListener('click', runSimulation);
  if (presetAggressive) {
    presetAggressive.addEventListener('click', () => {
      presetAggressive.className = 'btn btn-primary';
      presetActive.className = 'btn btn-secondary';
      simSafeBuyPct.value = 3;
      simSafeSellPct.value = 0.2;
      simAggBuyPct.value = 5;
      simAggSellPct.value = 2.5;
      simSplitCount.value = 7;
      simUpdatePeriod.value = 10;
      simCompoundingProfitRate.value = 80;
      simCompoundingLossRate.value = 30;
    });
  }
  if (presetActive) {
    presetActive.addEventListener('click', () => {
      presetAggressive.className = 'btn btn-secondary';
      presetActive.className = 'btn btn-primary';
      simSafeBuyPct.value = 2.5;
      simSafeSellPct.value = 0.5;
      simAggBuyPct.value = 4;
      simAggSellPct.value = 2;
      simSplitCount.value = 7;
      simUpdatePeriod.value = 10;
      simCompoundingProfitRate.value = 60;
      simCompoundingLossRate.value = 20;
    });
  }
  // 직접 입력(MANUAL) 선택 시 수동 입력창 노출/비노출 제어
  if (simTargetTicker && simManualTickerWrapper) {
    simTargetTicker.addEventListener('change', (e) => {
      if (e.target.value === 'MANUAL') {
        simManualTickerWrapper.style.display = 'block';
      } else {
        simManualTickerWrapper.style.display = 'none';
      }
    });
  }
  // 기본 시작일 및 종료일 설정 (기본값 최근 1년)
  if (simStartDate && simEndDate) {
    const today = new Date();
    const oneYearAgo = new Date();
    oneYearAgo.setFullYear(today.getFullYear() - 1);
    
    // YYYY-MM-DD 형식으로 포맷팅
    const formatDateStr = (d) => {
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    };
    simStartDate.value = formatDateStr(oneYearAgo);
    simEndDate.value = formatDateStr(today);
    // 하한선 설정
    simStartDate.min = "2018-07-27";
    simEndDate.min = "2018-07-27";
  }

  // 저장된 백테스트 결과 관련 이벤트 리스너 추가
  if (saveSimResultBtn) {
    saveSimResultBtn.addEventListener('click', async () => {
      if (!simulationResult) {
        alert('저장할 백테스트 결과가 없습니다. 먼저 실행해 주세요.');
        return;
      }
      let defaultAlias = '';
      if (simTargetTicker) {
        const tickerVal = simTargetTicker.value === 'MANUAL' ? simTargetTickerManual.value.trim().toUpperCase() : simTargetTicker.value;
        defaultAlias = `${tickerVal}_${simStartDate.value}_${simEndDate.value}`;
      } else {
        defaultAlias = `backtest_${Date.now()}`;
      }
      const alias = prompt('이 백테스트 결과의 별칭(이름)을 입력하세요:', defaultAlias);
      if (alias === null) return; // 취소
      const trimmed = alias.trim();
      if (!trimmed) {
        alert('이름을 입력해야 저장할 수 있습니다.');
        return;
      }
      await saveSimResult(trimmed);
    });
  }
  if (exportSimJsonBtn) {
    exportSimJsonBtn.addEventListener('click', async () => {
      const activeKey = simSavedList.value;
      if (!activeKey) {
        if (!simulationResult) {
          alert('내보낼 백테스트 결과가 없습니다.');
          return;
        }
        exportSimResultDirect(simulationResult);
      } else {
        await exportSimResultToJson(activeKey);
      }
    });
  }
  if (simSavedList) {
    simSavedList.addEventListener('change', async (e) => {
      const key = e.target.value;
      if (!key) {
        return;
      }
      try {
        const simData = await dbStore.get(key);
        if (simData) {
          restoreSimResult(simData);
        } else {
          alert('저장된 데이터를 찾을 수 없습니다.');
        }
      } catch (err) {
        console.error('불러오기 파싱 오류:', err);
        alert('데이터 복원에 실패했습니다.');
      }
    });
  }
  if (deleteSimBtn) {
    deleteSimBtn.addEventListener('click', async () => {
      const activeKey = simSavedList.value;
      if (!activeKey) {
        alert('삭제할 저장 이력을 선택해 주세요.');
        return;
      }
      try {
        const simData = await dbStore.get(activeKey);
        if (!simData) return;
        if (confirm(`'${simData.alias}' 백테스트 기록을 로컬에서 삭제하시겠습니까?`)) {
          await deleteSimResult(activeKey);
        }
      } catch (err) {
        console.error('삭제 처리 중 에러:', err);
      }
    });
  }
  if (importSimFileBtn && simFileInput) {
    importSimFileBtn.addEventListener('click', () => {
      simFileInput.click();
    });
    simFileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        importSimResultFromJson(file);
      }
      e.target.value = '';
    });
  }
}
// 로컬스토리지에서 설정 불러오기
function loadConfig() {
  // LocalStorage 내 옛날 중복 캐시 데이터 정리 (IndexedDB로 이관 완료에 따른 청소)
  for (let i = localStorage.length - 1; i >= 0; i--) {
    const key = localStorage.key(i);
    if (key && (key.startsWith('stock_db_cache_') || key.startsWith('stock_db_cache_sim_all_'))) {
      localStorage.removeItem(key);
    }
  }
  
  config.clientId = localStorage.getItem('stock_db_client_id') || DEFAULT_CLIENT_ID;
  
  const savedSheets = localStorage.getItem('stock_db_sheets');
  if (savedSheets) {
    config.sheets = JSON.parse(savedSheets);
  } else {
    config.sheets = [{
      name: '메인 계좌',
      id: DEFAULT_SHEET_ID
    }];
    localStorage.setItem('stock_db_sheets', JSON.stringify(config.sheets));
  }
  config.activeSheetId = localStorage.getItem('stock_db_active_sheet_id') || '';
  if (config.activeSheetId && config.activeSheetId !== 'combined-total' && config.sheets.length > 0) {
    if (!config.sheets.some(s => s.id === config.activeSheetId)) {
      config.activeSheetId = config.sheets[0].id;
      localStorage.setItem('stock_db_active_sheet_id', config.activeSheetId);
    }
  }
  if (!config.activeSheetId && config.sheets.length > 0) {
    config.activeSheetId = config.sheets[0].id;
    localStorage.setItem('stock_db_active_sheet_id', config.activeSheetId);
  }
  accessToken = localStorage.getItem('stock_db_access_token') || '';
  tokenExpiresAt = parseInt(localStorage.getItem('stock_db_token_expires_at') || '0', 10);
  
  clientIdInput.value = config.clientId === DEFAULT_CLIENT_ID ? '' : config.clientId;
  tempSheets = [...config.sheets];
}
function hasRegisteredSheets() {
  return config.sheets.length > 0;
}
function showWelcome() {
  welcomeScreen.style.display = 'flex';
  mainDashboard.style.display = 'none';
  bottomNavBar.style.display = 'none';
  activeSheetSelector.style.display = 'none';
  if (hasRegisteredSheets()) {
    welcomeSetupSection.style.display = 'none';
    welcomeLoginSection.style.display = 'block';
  } else {
    welcomeSetupSection.style.display = 'block';
    welcomeLoginSection.style.display = 'none';
  }
}
function showDashboard() {
  welcomeScreen.style.display = 'none';
  mainDashboard.style.display = 'block';
  bottomNavBar.style.display = 'flex';
  activeSheetSelector.style.display = 'inline-block';
}
async function handleAddSheet() {
  const name = newSheetNameInput.value.trim();
  const id = newSheetIdInput.value.trim();
  if (!name || !id) {
    alert('시트 별칭과 구글 스프레드시트 ID를 모두 입력해주세요.');
    return;
  }
  if (tempSheets.some(s => s.id === id)) {
    alert('이미 등록된 스프레드시트 ID입니다.');
    return;
  }
  tempSheets.push({ name, id });
  newSheetNameInput.value = '';
  newSheetIdInput.value = '';
  
  // 시트 추가 즉시 저장
  await saveConfigImmediate();
}
async function saveConfigImmediate() {
  // 기존의 모든 대시보드 캐시 무효화 (신규 계좌 추가/삭제로 인한 싱크 불일치 차단)
  try {
    const keys = await dbStore.getAllKeys();
    const promises = keys.map(key => {
      if (key.startsWith('stock_db_cache_') || key.startsWith('stock_db_cache_sim_all_')) {
        return dbStore.delete(key);
      }
      return Promise.resolve();
    });
    await Promise.all(promises);
  } catch (err) {
    console.error('캐시 무효화 중 오류 발생:', err);
  }
  config.sheets = [...tempSheets];
  localStorage.setItem('stock_db_sheets', JSON.stringify(config.sheets));
  const customClientId = clientIdInput.value.trim();
  config.clientId = customClientId ? customClientId : DEFAULT_CLIENT_ID;
  if (customClientId) {
    localStorage.setItem('stock_db_client_id', config.clientId);
  } else {
    localStorage.removeItem('stock_db_client_id');
  }
  if (config.sheets.length > 0) {
    if (!config.activeSheetId || !config.sheets.some(s => s.id === config.activeSheetId)) {
      config.activeSheetId = config.sheets[0].id;
    }
    localStorage.setItem('stock_db_active_sheet_id', config.activeSheetId);
  } else {
    config.activeSheetId = '';
    localStorage.removeItem('stock_db_active_sheet_id');
  }
  renderTempSheetList();
  updateSheetSelectorUI();
  
  if (isTokenValid()) {
    await fetchData();
  } else {
    loginWithGoogle();
  }
}
function renderTempSheetList() {
  sheetListContainer.innerHTML = '';
  if (tempSheets.length === 0) {
    sheetListContainer.innerHTML = `<div style="padding:1.5rem; text-align:center; color:var(--text-muted); font-size:0.85rem;">등록된 스프레드시트가 없습니다.</div>`;
    return;
  }
  tempSheets.forEach((sheet, index) => {
    const item = document.createElement('div');
    item.style.cssText = `
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.65rem 1rem;
      border-bottom: 1px solid rgba(255,255,255,0.04);
    `;
    if (index === tempSheets.length - 1) {
      item.style.borderBottom = 'none';
    }
    item.innerHTML = `
      <div style="max-width: 80%;">
        <div style="font-weight:700; font-size:0.8rem; color:var(--text-primary);">${sheet.name}</div>
        <div style="font-size:0.65rem; color:var(--text-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${sheet.id}</div>
      </div>
      <button class="btn" style="padding:0.25rem 0.45rem; background:rgba(255,23,68,0.08); border-color:rgba(255,23,68,0.15); color:var(--danger); height: 28px;" onclick="deleteTempSheet(${index})">
        <i data-lucide="trash-2" style="width: 13px; height: 13px;"></i>
      </button>
    `;
    sheetListContainer.appendChild(item);
  });
  
  lucide.createIcons();
}
window.deleteTempSheet = async function(index) {
  if (confirm('이 시트를 목록에서 삭제하시겠습니까?')) {
    tempSheets.splice(index, 1);
    await saveConfigImmediate();
  }
};
function updateSheetSelectorUI() {
  activeSheetSelector.innerHTML = '';
  
  // 등록된 시트가 2개 이상일 때 통합 계좌 선택 가능하도록 가상 옵션 추가
  if (config.sheets.length > 1) {
    const totalOpt = document.createElement('option');
    totalOpt.value = 'combined-total';
    totalOpt.innerText = '✨ [통합 계좌] 전체 보기';
    if (config.activeSheetId === 'combined-total') {
      totalOpt.selected = true;
    }
    activeSheetSelector.appendChild(totalOpt);
  }
  
  config.sheets.forEach(sheet => {
    const opt = document.createElement('option');
    opt.value = sheet.id;
    opt.innerText = sheet.name;
    if (sheet.id === config.activeSheetId) {
      opt.selected = true;
    }
    activeSheetSelector.appendChild(opt);
  });
}
function loginWithGoogle() {
  if (!tokenClient) {
    alert('Google API 클라이언트가 아직 로드되지 않았습니다. 잠시 후 다시 시도해 주세요.');
    return;
  }
  tokenClient.requestAccessToken({ prompt: '' });
}
function logout() {
  if (confirm('구글 연동을 해제하고 대시보드를 로그아웃 하시겠습니까?')) {
    localStorage.removeItem('stock_db_access_token');
    localStorage.removeItem('stock_db_token_expires_at');
    accessToken = '';
    tokenExpiresAt = 0;
    
    showWelcome();
    
    if (assetTrendChart) {
      assetTrendChart.destroy();
      assetTrendChart = null;
    }
    if (monthlyChart) {
      monthlyChart.destroy();
      monthlyChart = null;
    }
  }
}
async function resetConfig() {
  if (confirm('모든 연동 설정과 등록된 시트 목록을 완전히 초기화하시겠습니까?')) {
    localStorage.clear();
    try {
      await dbStore.clear();
    } catch (err) {
      console.error('IndexedDB 전체 소거 실패:', err);
    }
    loadConfig();
    initTheme();
    showWelcome();
    
    if (assetTrendChart) {
      assetTrendChart.destroy();
      assetTrendChart = null;
    }
    if (monthlyChart) {
      monthlyChart.destroy();
      monthlyChart = null;
    }
  }
}
// 수치 정제
function cleanNumber(val) {
  if (val === undefined || val === null) return 0;
  let str = String(val).trim();
  if (!str || str === '-' || str === '#n/a' || str === '#N/A') return 0;
  str = str.replace(/[₩$,%\s]/g, '');
  const num = parseFloat(str);
  return isNaN(num) ? 0 : num;
}
// 통화 포맷 (달러 기본값 고정)
function formatCurrency(value, currencySymbol = '$', decimals = 0) {
  const num = cleanNumber(value);
  const formatted = new Intl.NumberFormat('ko-KR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(num);
  return `${currencySymbol}${formatted}`;
}
// 퍼센트 포맷
function formatPercent(value) {
  const num = cleanNumber(value);
  const sign = num >= 0 ? '+' : '';
  return `${sign}${num.toFixed(2)}%`;
}
// 구글 시트 API 데이터 가져오기
// 구글 시트 API 데이터 가져오기
async function fetchData(forceRefresh = false) {
  // 로컬 파일 검토용 우회 및 더미 데이터 주입
  if (window.location.protocol === 'file:') {
    loadingOverlay.style.display = 'flex';
    setTimeout(() => {
      try {
        loadDummyData();
        renderDashboard();
      } catch (err) {
        console.error("로컬 더미 렌더링 중 에러 발생:", err);
      } finally {
        loadingOverlay.style.display = 'none';
      }
    }, 400);
    return;
  }
  if (!config.activeSheetId) {
    showWelcome();
    return;
  }
  
  // 캐시가 유효하면 네트워크 통신 생략
  const cacheKey = `stock_db_cache_${config.activeSheetId}`;
  if (!forceRefresh) {
    try {
      const cached = await dbStore.get(cacheKey);
      if (cached) {
        if (isCacheValid(cached.timestamp)) {
          console.log(`[캐시 히트] ${config.activeSheetId} 데이터를 로컬 캐시에서 불러옵니다.`);
          combinedRawData = cached.combinedRawData;
          jjDailyData = cached.jjDailyData;
          rawTransactions = cached.rawTransactions;
          summaryData = cached.summaryData;
          renderDashboard();
          return;
        }
      }
    } catch (cacheErr) {
      console.warn("캐시 로드 중 오류 발생, 네트워크 요청으로 대체합니다:", cacheErr);
    }
  }
  
  if (!isTokenValid()) {
    loginWithGoogle();
    return;
  }
  loadingOverlay.style.display = 'flex';
  
  try {
    if (config.activeSheetId === 'combined-total') {
      const promises = config.sheets.map(async (sheet) => {
        try {
          const vals = await fetchSheetValues('JJ', sheet.id);
          return { sheetName: sheet.name, values: vals, success: true };
        } catch (err) {
          console.error(`시트 [${sheet.name}] 로드 실패:`, err);
          return { sheetName: sheet.name, error: err, success: false };
        }
      });
      
      const results = await Promise.all(promises);
      const successfulResults = results.filter(r => r.success);
      
      if (successfulResults.length === 0) {
        throw new Error("모든 시트 데이터를 로드하는 데 실패했습니다.");
      }
      
      combinedRawData = successfulResults.map(r => ({ name: r.sheetName, values: r.values }));
      parseCombinedData(successfulResults);
      renderDashboard();
    } else {
      const rawData = await fetchSheetValues('JJ');
      const activeSheet = config.sheets.find(s => s.id === config.activeSheetId);
      const sheetName = activeSheet ? activeSheet.name : '기본 계좌';
      combinedRawData = [{ name: sheetName, values: rawData }];
      parseJJData(rawData);
      renderDashboard();
    }
    
    // 성공 시 캐시 저장
    try {
      const cacheData = {
        timestamp: Date.now(),
        combinedRawData,
        jjDailyData,
        rawTransactions,
        summaryData
      };
      await dbStore.set(cacheKey, cacheData);
      console.log(`[캐시 저장 완료] ${config.activeSheetId}`);
    } catch (saveErr) {
      console.error("캐시 저장 중 오류 발생:", saveErr);
    }
  } catch (error) {
    loadingOverlay.style.display = 'none'; // alert 창 띄우기 전 즉시 오버레이 선제 해제
    console.error(error);
    if (error.status === 401) {
      alert('인증이 만료되었습니다. 구글 로그인을 재진행합니다.');
      loginWithGoogle();
    } else {
      alert('구글 시트 데이터를 가져오는데 실패했습니다.\n선택하신 시트의 탭(시트) 이름(JJ)이 올바른지 확인해 주세요.\n\n에러 메시지: ' + error.message);
    }
  } finally {
    loadingOverlay.style.display = 'none';
  }
}
// 로컬 환경 검토용 고품질 더미 데이터 생성기
function loadDummyData() {
  summaryData.ticker = 'SOXL (데모)';
  summaryData.totalCost = 36111;
  summaryData.totalAsset = 45280;
  summaryData.totalProfit = 9169;
  summaryData.totalProfitRate = (summaryData.totalProfit / summaryData.totalCost) * 100;
  summaryData.realizedProfit = 2917;
  summaryData.currentCash = 10280;
  summaryData.currentHoldings = 550;
  // 15일간의 자산 평가액 변동 시뮬레이션
  jjDailyData = [
    { date: '06.01', close: 58.5, mode: '1단계 진입', cash: 25000, holdings: 190, evalAmt: 11115, totalAsset: 36115, profitRate: 0.01, dd: 0, accumProfit: 4, profit: 4, realized: 0 },
    { date: '06.02', close: 57.2, mode: '2단계 진입', cash: 21000, holdings: 260, evalAmt: 14872, totalAsset: 35872, profitRate: -0.66, dd: -0.7, accumProfit: -239, profit: -243, realized: 0 },
    { date: '06.03', close: 56.1, mode: '3단계 진입', cash: 18000, holdings: 310, evalAmt: 17391, totalAsset: 35391, profitRate: -1.99, dd: -2.0, accumProfit: -720, profit: -479, realized: 0 },
    { date: '06.04', close: 58.8, mode: '보유 관망', cash: 18000, holdings: 310, evalAmt: 18228, totalAsset: 36228, profitRate: 0.32, dd: 0, accumProfit: 117, profit: 837, realized: 0 },
    { date: '06.05', close: 60.5, mode: '보유 관망', cash: 18000, holdings: 310, evalAmt: 18755, totalAsset: 36755, profitRate: 1.78, dd: 0, accumProfit: 644, profit: 527, realized: 0 },
    { date: '06.08', close: 62.1, mode: '절반 매도', cash: 27615, holdings: 155, evalAmt: 9625, totalAsset: 37240, profitRate: 3.13, dd: 0, accumProfit: 1129, profit: 485, realized: 1210 },
    { date: '06.09', close: 61.2, mode: '1단계 진입', cash: 24000, holdings: 210, evalAmt: 12852, totalAsset: 36852, profitRate: 2.05, dd: -1.0, accumProfit: 741, profit: -388, realized: 0 },
    { date: '06.10', close: 63.4, mode: '보유 관망', cash: 24000, holdings: 210, evalAmt: 13314, totalAsset: 37314, profitRate: 3.33, dd: 0, accumProfit: 1203, profit: 462, realized: 0 },
    { date: '06.11', close: 65.8, mode: '일부 매도', cash: 33885, holdings: 100, evalAmt: 6580, totalAsset: 40465, profitRate: 12.06, dd: 0, accumProfit: 4354, profit: 3151, realized: 1707 },
    { date: '06.12', close: 63.6, mode: '수식 대기', cash: 10280, holdings: 550, evalAmt: 35000, totalAsset: 45280, profitRate: 25.39, dd: 0, accumProfit: 9169, profit: 4815, realized: 0 }
  ];
  // 매매 거래 내역 생성
  rawTransactions = [
    { date: '06.01', mode: '1단계 진입', type: 'BUY', qty: 190, price: 58.5, fee: 0, totalVal: 11115, realized: 0 },
    { date: '06.02', mode: '2단계 진입', type: 'BUY', qty: 70, price: 53.6, fee: 0, totalVal: 3757, realized: 0 },
    { date: '06.03', mode: '3단계 진입', type: 'BUY', qty: 50, price: 50.3, fee: 0, totalVal: 2519, realized: 0 },
    { date: '06.08', mode: '절반 매도', type: 'SELL', qty: 155, close: 62.1, price: 62.1, fee: 1.2, totalVal: 9624, realized: 1210 },
    { date: '06.09', mode: '1단계 진입', type: 'BUY', qty: 55, price: 65.7, fee: 0, totalVal: 3615, realized: 0 },
    { date: '06.11', mode: '일부 매도', type: 'SELL', qty: 110, close: 65.8, price: 65.8, fee: 1.8, totalVal: 7236, realized: 1707 }
  ];
  // 더미 주문 가이드 데이터 생성
  const dummyValues = Array(15).fill().map(() => Array(100).fill(''));
  // BN9 셀에 주문일 기입 (9행 65열)
  dummyValues[8][65] = '2026.06.13';
  // CJ10, CK10, CL10, CM10 매수 가이드 기입 (10행 87-90열)
  dummyValues[9][87] = '매수';
  dummyValues[9][88] = 'LOC';
  dummyValues[9][89] = '61.5';
  dummyValues[9][90] = '10';
  // CJ11, CK11, CL11, CM11 매도 가이드 기입 (11행 87-90열)
  dummyValues[10][87] = '매도';
  dummyValues[10][88] = 'LOC';
  dummyValues[10][89] = '65.2';
  dummyValues[10][90] = '5';
  combinedRawData = [{ name: 'SOXL (데모)', values: dummyValues }];
}
// 구글 시트 원본 2차원 배열 데이터의 불필요한 빈 행/열 트리밍 (localStorage 용량 최적화)
function trimSheetValues(values) {
  if (!values || values.length === 0) return [];
  
  // 1. 뒤에서부터 완전히 비어있는 행 제거 (아래쪽 트리밍)
  let lastNonEmptyRowIdx = -1;
  for (let i = values.length - 1; i >= 0; i--) {
    const row = values[i];
    if (row && row.some(cell => cell !== undefined && cell !== null && String(cell).trim() !== '')) {
      lastNonEmptyRowIdx = i;
      break;
    }
  }
  
  if (lastNonEmptyRowIdx === -1) return [];
  
  const trimmedRows = values.slice(0, lastNonEmptyRowIdx + 1);
  
  // 2. 각 행의 우측 빈 셀 제거 (오른쪽 트리밍)
  const processedRows = trimmedRows.map(row => {
    let lastNonEmptyColIdx = -1;
    for (let j = row.length - 1; j >= 0; j--) {
      const cell = row[j];
      if (cell !== undefined && cell !== null && String(cell).trim() !== '') {
        lastNonEmptyColIdx = j;
        break;
      }
    }
    return lastNonEmptyColIdx === -1 ? [] : row.slice(0, lastNonEmptyColIdx + 1);
  });
  
  return processedRows;
}

async function fetchSheetValues(sheetName, customSheetId) {
  const targetId = customSheetId || config.activeSheetId;
  const url = `https://sheets.googleapis.com/v4/spreadsheets/${targetId}/values/${sheetName}!A:ZZ?t=${Date.now()}`;
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${accessToken}`
    }
  });
  
  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const message = errData.error?.message || response.statusText;
    const err = new Error(`[${sheetName}] ${response.status} ${message}`);
    err.status = response.status;
    throw err;
  }
  
  const data = await response.json();
  if (!data.values || data.values.length === 0) {
    throw new Error(`[${sheetName}] 시트에 데이터가 없거나 형식이 일치하지 않습니다.`);
  }
  
  return trimSheetValues(data.values);
}
// 유연한 헤더 인덱스 찾기 헬퍼 함수
function findHeaderIndex(headers, possibleNames) {
  // 1단계: 완전 일치(Exact Match) 우선 검색
  for (let i = 0; i < headers.length; i++) {
    const header = String(headers[i]).trim().replace(/\s/g, '').toLowerCase();
    for (const name of possibleNames) {
      const target = name.replace(/\s/g, '').toLowerCase();
      if (header === target) {
        return i;
      }
    }
  }
  // 2단계: 부분 일치(Partial Match / Includes) 검색
  for (let i = 0; i < headers.length; i++) {
    const header = String(headers[i]).trim().replace(/\s/g, '').toLowerCase();
    for (const name of possibleNames) {
      const target = name.replace(/\s/g, '').toLowerCase();
      if (header.includes(target)) {
        return i;
      }
    }
  }
  return -1;
}
// 단일 일지 시트 (JJ) 데이터 파싱 및 정규화
function parseJJData(values) {
  const activeSheet = config.sheets.find(s => s.id === config.activeSheetId);
  const currentAccountName = activeSheet ? activeSheet.name : '기본 계좌';
  let headerRowIndex = -1;
  for (let i = 0; i < values.length; i++) {
    if (values[i].includes('거래일자') || values[i].includes('일자')) {
      headerRowIndex = i;
      break;
    }
  }
  if (headerRowIndex === -1) {
    throw new Error("JJ 시트 내에서 '거래일자' 헤더 행을 찾을 수 없습니다.");
  }
  const headers = values[headerRowIndex].map(h => h.trim());
  console.log("=== [구글 시트 헤더 분석 디버그] ===");
  console.log("시트 전체 헤더 목록 (1-based index 포함):", headers.map((h, idx) => `[${idx + 1}] ${h}`));
  // 유연한 매핑 규칙 적용
  const dateIdx = findHeaderIndex(headers, ['거래일자', '일자', '날짜', 'date']);
  const buyDateIdx = findHeaderIndex(headers, ['매수일', '매수일자', 'buydate']);
  const sellDateIdx = findHeaderIndex(headers, ['매도일', '매도일자', 'selldate']);
  const closeIdx = findHeaderIndex(headers, ['종가', '현재가', 'close']);
  const modeIdx = findHeaderIndex(headers, ['매매모드', '모드', 'mode']);
  const buyPriceIdx = findHeaderIndex(headers, ['매수가', '매수단가', 'buyprice']);
  const buyQtyIdx = findHeaderIndex(headers, ['매수량', '매수수량', 'buyqty']);
  const buyAmtIdx = findHeaderIndex(headers, ['매수금액', '매수금', 'buyamt']);
  const buyFeeIdx = findHeaderIndex(headers, ['수수료', 'fee']);
  
  const sellPriceIdx = findHeaderIndex(headers, ['매도가', '매도단가', 'sellprice']);
  const sellQtyIdx = findHeaderIndex(headers, ['매도량', '매도수량', 'sellqty']);
  const sellAmtIdx = findHeaderIndex(headers, ['매도금액', '매도금', 'sellamt']);
  
  // 두번째 수수료(매도용) 찾기
  let sellFeeIdx = -1;
  if (buyFeeIdx !== -1) {
    sellFeeIdx = headers.indexOf('수수료', buyFeeIdx + 1);
    if (sellFeeIdx === -1) sellFeeIdx = buyFeeIdx;
  }
  let realizedIdx = findHeaderIndex(headers, ['당일실현', '실현손익', '당일실현손익', '실현', 'realized', 'ae']);
  if (realizedIdx === -1 && headers.length > 30) {
    realizedIdx = 30; // AE열 폴백 (0-indexed 30번째)
  }
  console.log(`매핑된 실현손익 열 인덱스 (0-based): ${realizedIdx} -> 헤더명: "${headers[realizedIdx] || '없음(폴백적용)'}"`);
  const profitIdx = findHeaderIndex(headers, ['손익금액', '평가손익', '손익', 'profit']);
  const accumProfitIdx = findHeaderIndex(headers, ['누적손익', '평가손익누계', 'accumprofit']);
  const cashIdx = findHeaderIndex(headers, ['예수금', '잔고', 'cash']);
  const holdingsIdx = findHeaderIndex(headers, ['보유량', '보유수량', '보유주식', 'holdings']);
  const evalAmtIdx = findHeaderIndex(headers, ['평가금', '평가금액', 'evalamt']);
  const totalAssetIdx = findHeaderIndex(headers, ['총자산', '총 자산', '총자산가치', 'totalasset']);
  const profitRateIdx = findHeaderIndex(headers, ['수익률', '수익율', 'profitrate']);
  let ddIdx = findHeaderIndex(headers, ['mdd', 'dd', '낙폭', 'drawdown', 'ar']);
  if (ddIdx === -1 && headers.length > 43) {
    ddIdx = 43; // AR열 폴백 (0-indexed 43번째)
  }
  let seedIdx = findHeaderIndex(headers, ['시드증액', '원금증액', '입금', '증액', 'seedincrease', 'seed']);
  if (seedIdx === -1 && headers.length > 36) {
    seedIdx = 36; // AK열 폴백 (0-indexed 36번째)
  }
  // 1. 투자 종목(Ticker)명 유연하게 추출
  let ticker = 'SOXL';
  let hasFoundTicker = false;
  for (let i = 0; i < headerRowIndex; i++) {
    const row = values[i];
    if (!row) continue;
    for (let col = 0; col < row.length; col++) {
      const cellText = String(row[col]).trim().replace(/\s/g, '');
      if (cellText.includes('투자종목') || cellText.includes('종목명')) {
        if (row[col + 1]) {
          ticker = String(row[col + 1]).trim();
          hasFoundTicker = true;
          break;
        }
      }
    }
    if (hasFoundTicker) break;
  }
  summaryData.ticker = ticker;
  // 2. 투자원금 추출 (J5 셀인 values[4][9] 우선 탐색 및 텍스트 매칭 폴백)
  let totalCost = 0;
  let hasFoundCost = false;
  // J5 셀 직접 조회 (J열 = 10번째 열 즉 index 9, 5행 = index 4)
  if (values[4] && values[4][9] !== undefined && values[4][9] !== '') {
    const val = cleanNumber(values[4][9]);
    if (val > 0) {
      totalCost = val;
      hasFoundCost = true;
    }
  }
  // J5 셀에서 찾지 못했을 경우 텍스트 기반 폴백 탐색
  if (!hasFoundCost) {
    for (let i = 0; i < headerRowIndex; i++) {
      const row = values[i];
      if (!row) continue;
      for (let col = 0; col < row.length; col++) {
        const cellText = String(row[col]).trim().replace(/\s/g, '');
        if (cellText.includes('투자원금') || cellText.includes('원금')) {
          for (let offset = 1; offset <= 3; offset++) {
            if (row[col + offset] !== undefined && row[col + offset] !== '') {
              const val = cleanNumber(row[col + offset]);
              if (val > 0) {
                totalCost = val;
                hasFoundCost = true;
                break;
              }
            }
          }
        }
        if (hasFoundCost) break;
      }
      if (hasFoundCost) break;
    }
  }
  if (!hasFoundCost) totalCost = 36111; // 최종 폴백 기본값
  summaryData.totalCost = totalCost;
  // 3. 고정 누적실현손익 유연하게 추출
  let fixedRealizedProfit = 0;
  let hasFoundFixedRealized = false;
  for (let i = 0; i < headerRowIndex; i++) {
    const row = values[i];
    if (!row) continue;
    for (let col = 0; col < row.length; col++) {
      const cellText = String(row[col]).trim().replace(/\s/g, '');
      if (cellText.includes('누적실현') || cellText.includes('실현손익누계') || (cellText.includes('실현손익') && !cellText.includes('당일'))) {
        for (let offset = 1; offset <= 3; offset++) {
          if (row[col + offset] !== undefined && row[col + offset] !== '') {
            fixedRealizedProfit = cleanNumber(row[col + offset]);
            hasFoundFixedRealized = true;
            break;
          }
        }
      }
      if (hasFoundFixedRealized) break;
    }
    if (hasFoundFixedRealized) break;
  }
  jjDailyData = [];
  rawTransactions = [];
  for (let i = headerRowIndex + 1; i < values.length; i++) {
    const row = values[i];
    if (!row[dateIdx] || String(row[dateIdx]).trim() === '') continue;
    const dateStr = String(row[dateIdx]).trim();
    if (dateStr.includes('갱신') || dateStr.includes('수정') || dateStr.includes('거래일자')) continue;
    const mode = modeIdx !== -1 ? String(row[modeIdx]).trim() : '';
    const close = closeIdx !== -1 ? cleanNumber(row[closeIdx]) : 0;
    const cash = cashIdx !== -1 ? cleanNumber(row[cashIdx]) : 0;
    const holdings = holdingsIdx !== -1 ? cleanNumber(row[holdingsIdx]) : 0;
    const evalAmt = evalAmtIdx !== -1 ? cleanNumber(row[evalAmtIdx]) : 0;
    const totalAsset = totalAssetIdx !== -1 ? cleanNumber(row[totalAssetIdx]) : 0;
    const profitRate = profitRateIdx !== -1 ? cleanNumber(row[profitRateIdx]) : 0;
    let dd = ddIdx !== -1 ? cleanNumber(row[ddIdx]) : 0;
    const rawDdStr = ddIdx !== -1 ? String(row[ddIdx]) : '';
    if (!rawDdStr.includes('%') && Math.abs(dd) > 0 && Math.abs(dd) < 1) {
      dd = dd * 100;
    }
    const accumProfit = accumProfitIdx !== -1 ? cleanNumber(row[accumProfitIdx]) : 0;
    const profit = profitIdx !== -1 ? cleanNumber(row[profitIdx]) : 0;
    const realized = realizedIdx !== -1 ? cleanNumber(row[realizedIdx]) : 0;
    const seed = seedIdx !== -1 ? cleanNumber(row[seedIdx]) : 0;
    // ★ [버그 방지 필터링]: 예약 행 및 0원 행 제거
    if (totalAsset === 0 && holdings === 0 && cash === 0) continue;
    const dailyObj = {
      date: dateStr,
      close: close,
      mode: mode,
      cash: cash,
      holdings: holdings,
      evalAmt: evalAmt,
      totalAsset: totalAsset,
      profitRate: profitRate,
      dd: dd,
      accumProfit: accumProfit,
      profit: profit,
      realized: realized,
      seed: seed
    };
    jjDailyData.push(dailyObj);
    // 거래 내역 분할
    const buyQty = buyQtyIdx !== -1 ? cleanNumber(row[buyQtyIdx]) : 0;
    const buyPrice = buyPriceIdx !== -1 ? cleanNumber(row[buyPriceIdx]) : 0;
    const buyAmt = buyAmtIdx !== -1 ? cleanNumber(row[buyAmtIdx]) : 0;
    const buyFee = buyFeeIdx !== -1 ? cleanNumber(row[buyFeeIdx]) : 0;
    if (buyQty > 0) {
      const buyDate = (buyDateIdx !== -1 && row[buyDateIdx]) ? String(row[buyDateIdx]).trim() : dateStr;
      rawTransactions.push({
        date: buyDate && buyDate !== '-' ? buyDate : dateStr,
        mode: mode,
        type: 'BUY',
        qty: buyQty,
        price: buyPrice,
        fee: buyFee,
        totalVal: buyAmt,
        realized: 0,
        accountName: currentAccountName
      });
    }
    const sellQty = sellQtyIdx !== -1 ? cleanNumber(row[sellQtyIdx]) : 0;
    const sellPrice = sellPriceIdx !== -1 ? cleanNumber(row[sellPriceIdx]) : 0;
    const sellAmt = sellAmtIdx !== -1 ? cleanNumber(row[sellAmtIdx]) : 0;
    const sellFee = sellFeeIdx !== -1 ? cleanNumber(row[sellFeeIdx]) : 0;
    if (sellQty > 0) {
      const sellDate = (sellDateIdx !== -1 && row[sellDateIdx]) ? String(row[sellDateIdx]).trim() : dateStr;
      rawTransactions.push({
        date: sellDate && sellDate !== '-' ? sellDate : dateStr,
        mode: mode,
        type: 'SELL',
        qty: sellQty,
        price: sellPrice,
        fee: sellFee,
        totalVal: sellAmt,
        realized: realized,
        accountName: currentAccountName
      });
    }
  }
  // 상단 요약 데이터 동기화 (구글 시트 상단 3행, 5행 고정 요약 셀 우선 매핑)
  let totalAsset = 0;
  let totalProfit = 0;
  let totalProfitRate = 0;
  let currentCash = 0;
  let currentHoldings = 0;
  let hasSummaryRow = false;
  // 5행이 존재하고 H5(총자산), F5(누적손익)이 있는 경우 적용 (values[4]는 5행, 0-indexed)
  if (values[4] && values[4][7] !== undefined && values[4][5] !== undefined) {
    totalAsset = cleanNumber(values[4][7]);
    totalProfit = cleanNumber(values[4][5]);
    // E5 손익률 파싱
    totalProfitRate = cleanNumber(values[4][4]);
    hasSummaryRow = true;
  }
  // 3행이 존재하고 H3(예수금)이 있는 경우 적용 (values[2]는 3행)
  if (values[2] && values[2][7] !== undefined) {
    currentCash = cleanNumber(values[2][7]);
    currentHoldings = cleanNumber(values[2][9]); // J3 보유량
  }
  if (hasSummaryRow) {
    summaryData.totalAsset = totalAsset;
    summaryData.totalProfit = totalProfit;
    summaryData.totalProfitRate = totalProfitRate;
    summaryData.currentCash = currentCash;
    summaryData.currentHoldings = currentHoldings;
  } else if (jjDailyData.length > 0) {
    // 폴백: 일지 데이터 기반 추출
    const latest = jjDailyData[jjDailyData.length - 1];
    summaryData.totalAsset = latest.totalAsset;
    summaryData.totalProfit = latest.accumProfit;
    summaryData.totalProfitRate = latest.profitRate !== 0 ? latest.profitRate : 
      (summaryData.totalCost > 0 ? (summaryData.totalProfit / summaryData.totalCost) * 100 : 0);
    summaryData.currentCash = latest.cash;
    summaryData.currentHoldings = latest.holdings;
  }
  // 누적 실현손익 매핑 (사용자 요청: 구글 시트의 '누적(S)'(F5) 값을 '누적 실현손익'으로 일치하여 매핑)
  summaryData.realizedProfit = summaryData.totalProfit;
  // --- 날짜 역방향 연도 역산 보정 (跨年 crossover 버그 수정) ---
  if (jjDailyData.length > 0) {
    let currentYear = new Date().getFullYear();
    let dateMap = {}; // 원본 날짜 -> 보정된 날짜 매핑 맵
    
    // 1. 시트의 정렬 방향 감지 (오름차순 vs 내림차순)
    // 인접한 두 데이터 간에 월이 증가하는지 감소하는지 흐름 분석
    let ascCount = 0;
    let descCount = 0;
    let prevM = -1;
    for (let i = 0; i < jjDailyData.length; i++) {
      let dStr = jjDailyData[i].date;
      let cleaned = dStr.replace(/[^0-9.]/g, '').replace(/\.+/g, '.');
      if (cleaned.endsWith('.')) cleaned = cleaned.slice(0, -1);
      let parts = cleaned.split('.');
      if (parts.length >= 2) {
        let m = parseInt(parts[parts.length === 3 ? 1 : 0], 10);
        if (prevM !== -1) {
          if (m > prevM) ascCount++;
          else if (m < prevM) descCount++;
        }
        prevM = m;
      }
    }
    const isAscending = ascCount >= descCount;
    
    // 2. 최신 날짜의 월을 구하여 prevMonth 초기값 설정
    let latestIndex = isAscending ? jjDailyData.length - 1 : 0;
    let lastDateStr = jjDailyData[latestIndex].date;
    let cleanedLast = lastDateStr.replace(/[^0-9.]/g, '').replace(/\.+/g, '.');
    if (cleanedLast.endsWith('.')) cleanedLast = cleanedLast.slice(0, -1);
    let lastParts = cleanedLast.split('.');
    
    let prevMonth = 12;
    if (lastParts.length >= 2) {
      let mIdx = lastParts.length === 3 ? 1 : 0;
      prevMonth = parseInt(lastParts[mIdx], 10);
    }
    
    // 3. 방향에 따라 연도 역산 순회 수행
    const runYearCorrection = (i) => {
      let originalDateStr = jjDailyData[i].date;
      let normalized = originalDateStr.trim().replace(/[-/\s]/g, '.');
      let cleaned = normalized.replace(/[^0-9.]/g, '').replace(/\.+/g, '.');
      if (cleaned.endsWith('.')) cleaned = cleaned.slice(0, -1);
      let parts = cleaned.split('.');
      
      if (parts.length === 2) {
        let month = parseInt(parts[0], 10);
        let day = parseInt(parts[1], 10);
        
        // 해가 거꾸로 넘어가는 crossover 감지 (기입 오류 노이즈 방지를 위해 월 차이가 4 이상인 경우만 적용)
        if (month - prevMonth >= 4) {
          currentYear--;
        }
        
        let newDateStr = `${currentYear}.${parts[0].padStart(2, '0')}.${parts[1].padStart(2, '0')}`;
        jjDailyData[i].date = newDateStr;
        dateMap[originalDateStr] = newDateStr;
        prevMonth = month;
      } else if (parts.length === 3) {
        let y = parseInt(parts[0], 10);
        if (y < 100) y += 2000;
        let newDateStr = `${y}.${parts[1].padStart(2, '0')}.${parts[2].padStart(2, '0')}`;
        jjDailyData[i].date = newDateStr;
        dateMap[originalDateStr] = newDateStr;
        prevMonth = parseInt(parts[1], 10);
        currentYear = y; // 연도 기준값 실시간 동기화
      } else {
        dateMap[originalDateStr] = originalDateStr;
      }
    };
    
    if (isAscending) {
      for (let i = jjDailyData.length - 1; i >= 0; i--) {
        runYearCorrection(i);
      }
    } else {
      for (let i = 0; i < jjDailyData.length; i++) {
        runYearCorrection(i);
      }
    }
    // 4. 거래 내역(rawTransactions) 날짜 동기화
    rawTransactions.forEach(t => {
      if (dateMap[t.date]) {
        t.date = dateMap[t.date];
      } else {
        let cleaned = t.date.replace(/[^0-9.]/g, '').replace(/\.+/g, '.');
        if (cleaned.endsWith('.')) cleaned = cleaned.slice(0, -1);
        let parts = cleaned.split('.');
        if (parts.length === 2) {
          t.date = `${currentYear}.${parts[0].padStart(2, '0')}.${parts[1].padStart(2, '0')}`;
        }
      }
    });
    // 5. 보정이 완료된 데이터를 날짜 오름차순으로 완벽히 정렬
    jjDailyData.sort((a, b) => parseDate(a.date) - parseDate(b.date));
    rawTransactions.sort((a, b) => parseDate(a.date) - parseDate(b.date));
    // 6. 누적손익 데이터 전방 채우기 (Forward Fill)
    // 누적손익이 0이거나 유실된 행에 대해, 이전 행(가장 가까운 과거 행)의 유효한 누적손익을 상속
    let lastValidAccumProfit = 0;
    for (let i = 0; i < jjDailyData.length; i++) {
      if (jjDailyData[i].accumProfit !== 0) {
        lastValidAccumProfit = jjDailyData[i].accumProfit;
      } else if (lastValidAccumProfit !== 0) {
        jjDailyData[i].accumProfit = lastValidAccumProfit;
      }
    }
  }
}
// 대시보드 렌더링 총괄
function renderDashboard() {
  renderSummary();
  renderDailyCards();
  renderTransactionCards();
  renderAssetTrendChart();
  renderMonthlyChart();
  calculatePeriodPerformance();
  renderOrderGuideTable();
}
// 요약 카드 렌더링
function renderSummary() {
  const assetSummaryCard = document.getElementById('assetSummaryCard');
  
  document.getElementById('totalValue').innerText = formatCurrency(summaryData.totalAsset);
  document.getElementById('totalCostBase').innerText = formatCurrency(summaryData.totalCost);
  document.getElementById('realizedProfit').innerText = formatCurrency(summaryData.realizedProfit);
  document.getElementById('cashValue').innerText = formatCurrency(summaryData.currentCash);
  const profitRateEl = document.getElementById('totalProfitRateBadge');
  const profitValEl = document.getElementById('totalProfitVal');
  profitRateEl.innerText = formatPercent(summaryData.totalProfitRate);
  if (profitValEl) {
    profitValEl.innerText = `${formatCurrency(summaryData.totalProfit)} (누적손익)`;
  }
  // 플러스/마이너스 색상 정밀 적용
  if (summaryData.totalProfit >= 0) {
    assetSummaryCard.className = 'glass-card main-summary-card text-up';
    profitRateEl.className = 'profit-rate-badge up';
  } else {
    assetSummaryCard.className = 'glass-card main-summary-card text-down';
    profitRateEl.className = 'profit-rate-badge down';
  }
  lucide.createIcons();
}
// 일자별 분석 카드 피드 리스트 렌더링
function renderDailyCards() {
  dailyCardList.innerHTML = '';
  if (jjDailyData.length === 0) {
    dailyCardList.innerHTML = `<div class="empty-state">분석 가능한 일지 데이터가 없습니다.</div>`;
    return;
  }
  // 최신순 정렬 후 표시
  const sortedDaily = [...jjDailyData].reverse();
  sortedDaily.forEach(item => {
    const isUp = item.profitRate >= 0;
    const profitClass = isUp ? 'text-up' : 'text-down';
    const rateSign = isUp ? '+' : '';
    
    // 매매 모드 배지 분기
    let modeBadgeStyle = 'background: rgba(157, 78, 221, 0.15); color: var(--neon-purple);';
    if (item.mode.includes('공세')) {
      modeBadgeStyle = 'background: rgba(255, 0, 127, 0.15); color: var(--neon-pink);';
    }
    const card = document.createElement('div');
    card.className = 'daily-card';
    card.innerHTML = `
      <div class="daily-card-header">
        <span class="daily-date">${item.date}</span>
        <span class="daily-mode" style="${modeBadgeStyle}">${item.mode}</span>
      </div>
      <div class="daily-card-body">
        <div class="daily-info-item">
          <span class="daily-info-label">총자산</span>
          <span class="daily-info-val" style="font-weight:700; color:var(--text-primary);">${formatCurrency(item.totalAsset, '$')}</span>
        </div>
        <div class="daily-info-item">
          <span class="daily-info-label">예수금</span>
          <span class="daily-info-val">${formatCurrency(item.cash, '$')}</span>
        </div>
        <div class="daily-info-item">
          <span class="daily-info-label">평가금</span>
          <span class="daily-info-val">${formatCurrency(item.evalAmt, '$')}</span>
        </div>
        <div class="daily-info-item">
          <span class="daily-info-label">수익률(DD)</span>
          <span class="daily-info-val ${profitClass}" style="font-weight:700;">${rateSign}${item.profitRate.toFixed(2)}% (${item.dd.toFixed(1)}%)</span>
        </div>
        <div class="daily-info-item">
          <span class="daily-info-label">종가/수량</span>
          <span class="daily-info-val">${formatCurrency(item.close, '$')} / ${(item.holdings || 0).toLocaleString()}주</span>
        </div>
        <div class="daily-info-item">
          <span class="daily-info-label">당일손익</span>
          <span class="daily-info-val ${isUp ? 'text-up' : 'text-down'}">${formatCurrency(item.profit, '$')}</span>
        </div>
      </div>
    `;
    dailyCardList.appendChild(card);
  });
}
// 체결 내역 카드 리스트 렌더링
function renderTransactionCards() {
  transactionCardList.innerHTML = '';
  const searchVal = transactionSearch.value.trim().toLowerCase();
  const typeFilter = transactionTypeFilter.value;
  const sortOption = transactionSort.value;
  let filtered = rawTransactions.filter(t => {
    const matchSearch = t.date.toLowerCase().includes(searchVal) || t.mode.toLowerCase().includes(searchVal);
    const matchType = typeFilter === 'ALL' || t.type === typeFilter;
    return matchSearch && matchType;
  });
  // 정렬 제어
  if (sortOption === 'DATE_DESC') {
    filtered.sort((a, b) => parseDate(b.date) - parseDate(a.date));
  } else if (sortOption === 'DATE_ASC') {
    filtered.sort((a, b) => parseDate(a.date) - parseDate(b.date));
  } else if (sortOption === 'VAL_DESC') {
    filtered.sort((a, b) => b.totalVal - a.totalVal);
  }
  if (filtered.length === 0) {
    transactionCardList.innerHTML = `<div class="empty-state">해당하는 체결 기록이 없습니다.</div>`;
    return;
  }
  filtered.forEach(t => {
    const isBuy = t.type === 'BUY';
    const typeClass = isBuy ? 'buy' : 'sell';
    const typeLabel = isBuy ? '매수' : '매도';
    const amtColorClass = isBuy ? 'text-up' : 'text-down';
    
    let realizedText = '';
    if (!isBuy && t.realized !== 0) {
      const realizedColor = t.realized >= 0 ? 'color: var(--success);' : 'color: var(--danger);';
      realizedText = `<div class="tx-realized" style="${realizedColor}">실현손익: ${formatCurrency(t.realized, '$')}</div>`;
    }
    const card = document.createElement('div');
    card.className = 'tx-card';
    const accountLabel = t.accountName ? `<span class="tx-type-badge" style="background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15); color: var(--text-muted); margin-right: 4px; font-weight: 500;">${t.accountName}</span>` : '';
    card.innerHTML = `
      <div class="tx-left">
        <div style="display: flex; align-items: center; gap: 4px; margin-bottom: 2px;">
          ${accountLabel}
          <span class="tx-type-badge ${typeClass}">${typeLabel}</span>
        </div>
        <div class="tx-date-mode">${t.date} <span style="opacity: 0.6;">[${t.mode}]</span></div>
        <div class="tx-qty-price">${(t.qty || 0).toLocaleString()}주 • 단가: ${formatCurrency(t.price, '$')}</div>
      </div>
      <div class="tx-right">
        <div class="tx-amt ${amtColorClass}">${formatCurrency(t.totalVal, '$')}</div>
        ${t.fee > 0 ? `<div style="font-size:0.65rem; color:var(--text-muted);">수수료: ${formatCurrency(t.fee, '$')}</div>` : ''}
        ${realizedText}
      </div>
    `;
    transactionCardList.appendChild(card);
  });
}
// 1. 자산 추이 및 예수금 비율 차트 그리기
function renderAssetTrendChart() {
  try {
    if (assetTrendChart) {
      assetTrendChart.destroy();
    }
    if (jjDailyData.length === 0) return;
    // 전체 데이터 로드 (전체 추이 표현)
    const chartData = jjDailyData;
    const dates = chartData.map(d => d.date);
    const evalAmts = chartData.map(d => d.evalAmt);
    const cashes = chartData.map(d => d.cash);
    const totalAssets = chartData.map(d => d.totalAsset);
    // 시트에서 파싱된 MDD 값 (ar열) 사용하며 안정적인 매핑을 위해 항상 양수 퍼센트로 변환
    const mddVals = chartData.map(d => {
      return Math.abs(d.dd || 0);
    });
    // MDD 최대값(양수 기준)을 계산하여 보조 y축 범위를 결정 (예: 최대 낙폭이 25.5%이면 30%까지 표시)
    const validMddVals = mddVals.filter(v => !isNaN(v));
    const maxMddVal = validMddVals.length > 0 ? Math.max(...validMddVals) : 10;
    const finalMaxMdd = maxMddVal > 0 ? Math.ceil(maxMddVal / 10) * 10 : 10;

    // Y축 금액 최댓값 자동 산출 (주식 평가금, 보유 예수금, 총자산 가치 전체 중 최댓값 기준)
    const allAssetVals = [...evalAmts, ...cashes, ...totalAssets].filter(v => v !== undefined && v !== null && !isNaN(v));
    const maxAssetVal = allAssetVals.length > 0 ? Math.max(...allAssetVals) : 10000;
    
    // 금액 규모에 따라 올림 단위(Step) 결정 (약 5~10% 마진 적용)
    let step = 50000;
    if (maxAssetVal <= 30000) {
      step = 5000;
    } else if (maxAssetVal <= 100000) {
      step = 10000;
    } else if (maxAssetVal <= 250000) {
      step = 25000;
    }
    const finalMaxAsset = Math.ceil((maxAssetVal * 1.05) / step) * step;

    // 테마별 속성 불러오기
    const themeOpts = getThemeChartOptions();
    const options = {
      series: [
        {
          name: '주식 평가금',
          type: 'area',
          data: evalAmts
        },
        {
          name: '보유 예수금',
          type: 'area',
          data: cashes
        },
        {
          name: '총자산 가치',
          type: 'line',
          data: totalAssets
        },
        {
          name: 'MDD',
          type: 'line',
          data: mddVals
        }
      ],
      chart: {
        height: 220,
        type: 'line',
        foreColor: themeOpts.foreColor,
        toolbar: {
          show: false
        },
        zoom: {
          enabled: false
        }
      },
      colors: themeOpts.colors.concat(['#ff1744']),
      stroke: {
        width: [1.5, 1.5, 2.5, 2],
        curve: 'smooth'
      },
      fill: {
        type: 'solid',
        opacity: [0.2, 0.2, 1, 1]
      },
      dataLabels: {
        enabled: false
      },
      xaxis: {
        categories: dates,
        labels: {
          show: false // X축 날짜 라벨 표시하지 않음 (전체 곡선 흐름 강조)
        },
        axisBorder: {
          show: false
        },
        axisTicks: {
          show: false
        }
      },
      yaxis: [
        {
          seriesName: '주식 평가금',
          showForNullSeries: true,
          min: 0,
          max: finalMaxAsset,
          labels: {
            style: { fontSize: '9px' },
            formatter: function (val) {
              return formatCurrency(val, '$');
            }
          }
        },
        {
          seriesName: '보유 예수금',
          showForNullSeries: true,
          min: 0,
          max: finalMaxAsset,
          show: false
        },
        {
          seriesName: '총자산 가치',
          showForNullSeries: true,
          min: 0,
          max: finalMaxAsset,
          show: false
        },
        {
          seriesName: 'MDD',
          showForNullSeries: true,
          opposite: true,
          reversed: true, // 0%가 최상단에 위치하고 양수 낙폭이 하단 방향으로 뻗음
          min: 0,
          max: finalMaxMdd,
          labels: {
            style: { fontSize: '11px' },
            formatter: function (val) {
              if (val === undefined || val === null || isNaN(val)) return '0.0%';
              // 양수 스케일 값을 마이너스 기호를 붙여 음수 퍼센트로 라벨링
              return val > 0 ? `-${val.toFixed(1)}%` : '0.0%';
            }
          }
        }
      ],
      tooltip: {
        theme: 'dark',
        shared: true,
        y: {
          formatter: function (val, opts) {
            if (opts.seriesIndex === 3) {
              if (val === undefined || val === null || isNaN(val)) return '0.00%';
              // 툴팁에서도 양수 MDD 값을 마이너스 기호를 붙여 음수로 표기
              return val > 0 ? `-${val.toFixed(2)}%` : '0.00%';
            }
            return formatCurrency(val, '$');
          }
        }
      },
      grid: {
        borderColor: 'rgba(255,255,255,0.03)',
        padding: {
          left: 5,
          right: 5
        }
      },
      legend: {
        position: 'top',
        fontSize: '10px',
        fontFamily: 'Inter, sans-serif',
        offsetX: 0,
        offsetY: 0,
        itemMargin: {
          horizontal: 6,
          vertical: 0
        }
      }
    };
    assetTrendChart = new ApexCharts(document.querySelector("#assetTrendChart"), options);
    assetTrendChart.render();
  } catch (err) {
    console.error("Trend Chart Error:", err);
    alert("자산 추이 차트 렌더링 중 런타임 오류 감지:\n" + err.message + "\n\n스택: " + err.stack);
  }
}
// 2. 12개월 실현손익 축없는 막대 차트 (도미노/금융 앱 스타일)
function renderMonthlyChart(year) {
  if (monthlyChart) {
    monthlyChart.destroy();
  }
  // 데이터 내 존재하는 연도 목록 추출
  const yearSet = new Set();
  jjDailyData.forEach(d => {
    const y = parseDate(d.date).getFullYear();
    if (y > 2000) yearSet.add(y);
  });
  const availableYears = Array.from(yearSet).sort((a, b) => b - a);
  // 선택 연도: 파라미터 없으면 가장 최신 연도
  const latestDate = jjDailyData.length > 0 ? parseDate(jjDailyData[jjDailyData.length - 1].date) : new Date();
  const targetYear = year || latestDate.getFullYear();
  // 연도 선택 버튼 렌더링
  const btnContainer = document.getElementById('yearSelectorBtns');
  if (btnContainer) {
    btnContainer.innerHTML = '';
    availableYears.forEach(y => {
      const btn = document.createElement('button');
      btn.className = 'year-btn' + (y === targetYear ? ' active' : '');
      btn.textContent = String(y);
      btn.onclick = () => renderMonthlyChart(y);
      btnContainer.appendChild(btn);
    });
  }
  // 선택 연도 기준 월별 손익 집계
  const monthlyProfit = Array(12).fill(0);
  const monthLabels = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'];
  console.log(`=== [${targetYear}년 월별 실현손익 집계 디버그] ===`);
  let debugSum = 0;
  jjDailyData.forEach(d => {
    const dateObj = parseDate(d.date);
    if (dateObj.getFullYear() === targetYear) {
      const monthIdx = dateObj.getMonth();
      monthlyProfit[monthIdx] += d.realized;
      if (d.realized !== 0) {
        console.log(`  [집계 행] 날짜: ${d.date}, 당일실현손익: ${d.realized}, 누적손익: ${d.accumProfit}`);
        debugSum += d.realized;
      }
    }
  });
  console.log(`>>> ${targetYear}년 총합계 (AE열 계산값): ${debugSum}`);
  // 선택 연도의 총 실현손익 합산 및 렌더링
  const yearlyTotalProfit = monthlyProfit.reduce((sum, val) => sum + val, 0);
  const yearlyProfitTextEl = document.getElementById('yearlyTotalProfitText');
  if (yearlyProfitTextEl) {
    const absAmt = Math.abs(yearlyTotalProfit);
    const formattedAmt = formatCurrency(absAmt, '$');
    const colorClass = yearlyTotalProfit >= 0 ? 'var(--success)' : 'var(--danger)';
    const sign = yearlyTotalProfit >= 0 ? '+' : '-';
    yearlyProfitTextEl.innerHTML = `${targetYear}년 누적 실현손익: <span style="color: ${colorClass}; font-weight: 700;">${sign}${formattedAmt}</span>`;
  }
  const themeOpts = getThemeChartOptions();
  const options = {
    series: [
      {
        name: '실현 손익',
        data: monthlyProfit
      }
    ],
    chart: {
      height: 180,
      type: 'bar',
      foreColor: themeOpts.foreColor,
      toolbar: {
        show: false
      },
      zoom: {
        enabled: false
      }
    },
    plotOptions: {
      bar: {
        columnWidth: '60%',
        borderRadius: 4,
        dataLabels: {
          position: 'top'
        }
      }
    },
    // 플러스 실현손익은 테마 메인컬러, 마이너스는 네온레드 지정
    colors: [
      function({ value }) {
        return value >= 0 ? themeOpts.colors[0] : '#ff1744';
      }
    ],
    grid: {
      show: false, // 가로선 그리드 제거
      padding: {
        left: 5,
        right: 5
      }
    },
    xaxis: {
      categories: monthLabels,
      axisBorder: {
        show: false
      },
      axisTicks: {
        show: false
      },
      labels: {
        style: { fontSize: '9px', fontWeight: 'bold' }
      }
    },
    yaxis: {
      show: false // Y축 완벽 차단
    },
    dataLabels: {
      enabled: true,
      formatter: function (val) {
        if (val === 0) return '';
        const sign = val > 0 ? '+' : '-';
        const abs = Math.abs(val);
        if (abs >= 1000000) return `${sign}${(abs / 1000000).toFixed(1)}M`;
        if (abs >= 1000) return `${sign}${(abs / 1000).toFixed(1)}K`;
        return `${sign}${abs.toFixed(0)}`;
      },
      offsetY: -20,
      style: {
        fontSize: '11px',
        fontWeight: '700',
        colors: ['#ffffff'],
        fontFamily: 'Outfit, Inter, sans-serif'
      },
      background: {
        enabled: true,
        foreColor: '#000',
        padding: 2,
        borderRadius: 3,
        borderWidth: 0,
        opacity: 0.35
      }
    },
    tooltip: {
      theme: 'dark',
      y: {
        formatter: function (val) {
          return formatCurrency(val, '$');
        }
      }
    },
    legend: {
      show: false
    }
  };
  monthlyChart = new ApexCharts(document.querySelector("#monthlyChart"), options);
  monthlyChart.render();
}
function parseDate(dateStr) {
  // 1. 하이픈(-), 슬래시(/), 공백 등을 모두 마침표(.)로 변환
  let normalized = String(dateStr).trim().replace(/[-/\s]/g, '.');
  
  // 2. 숫자와 마침표(.)만 남기고 요일 괄호 등 완전히 제거 (예: '2026.06.13.(토)' -> '2026.06.13.')
  let cleaned = normalized.replace(/[^0-9.]/g, '');
  
  // 3. 맨 마지막에 남은 불필요한 마침표 제거 (예: '2026.06.13.' -> '2026.06.13')
  if (cleaned.endsWith('.')) {
    cleaned = cleaned.slice(0, -1);
  }
  
  // 4. 연속된 마침표 하나로 축소 (예: '2026..06..13' -> '2026.06.13')
  cleaned = cleaned.replace(/\.+/g, '.');
  
  // 5. 마침표 기준 분할 후 Date 객체 생성
  const parts = cleaned.split('.');
  if (parts.length >= 3) {
    let y = parseInt(parts[0], 10);
    if (y < 100) y += 2000;
    return new Date(y, parseInt(parts[1]) - 1, parseInt(parts[2]));
  } else if (parts.length === 2) {
    let y = parseInt(parts[0], 10);
    // parts.length가 2인 경우는 MM.DD일 가능성이 높으므로 연도 보정을 하지 않고 기존과 동일하게 처리합니다.
    return new Date(y, parseInt(parts[1]) - 1, 1);
  }
  return new Date(cleaned);
}
// 기간별 수익률 계산 및 UI 표시
function calculatePeriodPerformance() {
  if (!jjDailyData || jjDailyData.length < 2) return;
  const latest = jjDailyData[jjDailyData.length - 1];
  const latestDate = parseDate(latest.date);
  const currentYear = latestDate.getFullYear();
  // 기간 기준 날짜 산정
  const oneMonthAgo = new Date(latestDate);
  oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);
  const threeMonthsAgo = new Date(latestDate);
  threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
  const oneYearAgo = new Date(latestDate);
  oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
  // 가장 근접한 과거 행 탐색
  let oneMonthAgoIdx = 0;
  let threeMonthsAgoIdx = 0;
  let ytdIdx = 0;
  let oneYearAgoIdx = 0;
  for (let i = 0; i < jjDailyData.length; i++) {
    const rowDate = parseDate(jjDailyData[i].date);
    // 1개월전 기준 - 가장 가까운 행
    if (rowDate <= oneMonthAgo) {
      oneMonthAgoIdx = i;
    }
    // 3개월전 기준
    if (rowDate <= threeMonthsAgo) {
      threeMonthsAgoIdx = i;
    }
    // 1년전 기준
    if (rowDate <= oneYearAgo) {
      oneYearAgoIdx = i;
    }
    // 올해 누적(YTD) - 올해의 첫번째 관측 행 찾기
    if (rowDate.getFullYear() === currentYear) {
      const ytdDate = parseDate(jjDailyData[ytdIdx].date);
      if (ytdDate.getFullYear() !== currentYear || rowDate < ytdDate) {
        ytdIdx = i;
      }
    }
  }
  
  // 시계열 데이터가 1개보다 많을 때 계산 기준 행이 최신 행과 동일하면 0.00%가 나오는 오작동 방지용 안전 장치
  if (latest.date === jjDailyData[oneMonthAgoIdx].date && jjDailyData.length > 1) {
    oneMonthAgoIdx = 0;
  }
  if (latest.date === jjDailyData[threeMonthsAgoIdx].date && jjDailyData.length > 1) {
    threeMonthsAgoIdx = 0;
  }
  if (latest.date === jjDailyData[oneYearAgoIdx].date && jjDailyData.length > 1) {
    oneYearAgoIdx = 0;
  }
  
  const oneMonthAgoRow = jjDailyData[oneMonthAgoIdx];
  const threeMonthsAgoRow = jjDailyData[threeMonthsAgoIdx];
  const ytdRow = jjDailyData[ytdIdx];
  const oneYearAgoRow = jjDailyData[oneYearAgoIdx];
  // 특정 기준일부터 최신일 직전까지 발생한 시드증액의 총합 산출 (과거일 다음 날부터 일어난 시드증액 누계)
  function getPeriodSeedIncrease(startIndex) {
    let total = 0;
    for (let i = startIndex + 1; i < jjDailyData.length; i++) {
      total += jjDailyData[i].seed || 0;
    }
    return total;
  }
  const seed1M = getPeriodSeedIncrease(oneMonthAgoIdx);
  const seed3M = getPeriodSeedIncrease(threeMonthsAgoIdx);
  const seedYTD = getPeriodSeedIncrease(ytdIdx);
  const seed1Y = getPeriodSeedIncrease(oneYearAgoIdx);
  
  const perf1MVal = calculatePeriodReturn(latest.accumProfit, oneMonthAgoRow.accumProfit, oneMonthAgoRow.totalAsset, latest.totalAsset, seed1M);
  const perf3MVal = calculatePeriodReturn(latest.accumProfit, threeMonthsAgoRow.accumProfit, threeMonthsAgoRow.totalAsset, latest.totalAsset, seed3M);
  const perfYTDVal = calculatePeriodReturn(latest.accumProfit, ytdRow.accumProfit, ytdRow.totalAsset, latest.totalAsset, seedYTD);
  const perf1YVal = calculatePeriodReturn(latest.accumProfit, oneYearAgoRow.accumProfit, oneYearAgoRow.totalAsset, latest.totalAsset, seed1Y);
  // 연환산 수익률 계산
  // 1개월 → 12배 복리 환산: (1 + r)^12 - 1
  const annual1MVal = (Math.pow(1 + perf1MVal / 100, 12) - 1) * 100;
  // 3개월 → 4배 복리 환산: (1 + r)^4 - 1
  const annual3MVal = (Math.pow(1 + perf3MVal / 100, 4) - 1) * 100;
  // YTD → 경과일 기준 환산: (1 + r)^(365/경과일수) - 1
  const ytdDate = parseDate(ytdRow.date);
  const daysElapsed = Math.max(1, Math.round((latestDate - ytdDate) / (1000 * 60 * 60 * 24)));
  const annualYTDVal = (Math.pow(1 + perfYTDVal / 100, 365 / daysElapsed) - 1) * 100;
  // 디버깅을 위한 상세 데이터 덤프
  console.log("=== [기간별 수익률 계산 디버그] ===");
  console.log("jjDailyData 최근 5개 행 원본 데이터:");
  const sliceStart = Math.max(0, jjDailyData.length - 5);
  for (let idx = sliceStart; idx < jjDailyData.length; idx++) {
    const d = jjDailyData[idx];
    console.log(`  행[${idx}]: 날짜 = ${d.date}, 누적손익 = ${d.accumProfit}, 총자산 = ${d.totalAsset}, 시드증액 = ${d.seed}`);
  }
  console.log(`최신일 (${latest.date}): 누적손익 = ${latest.accumProfit}, 총자산 = ${latest.totalAsset}`);
  console.log(`1개월전 (${oneMonthAgoRow.date}): 누적손익 = ${oneMonthAgoRow.accumProfit}, 총자산 = ${oneMonthAgoRow.totalAsset}, 기간시드증액 = ${seed1M} -> 수익률 = ${perf1MVal.toFixed(2)}% -> 연환산 = ${annual1MVal.toFixed(2)}%`);
  console.log(`3개월전 (${threeMonthsAgoRow.date}): 누적손익 = ${threeMonthsAgoRow.accumProfit}, 총자산 = ${threeMonthsAgoRow.totalAsset}, 기간시드증액 = ${seed3M} -> 수익률 = ${perf3MVal.toFixed(2)}% -> 연환산 = ${annual3MVal.toFixed(2)}%`);
  console.log(`올해초 (${ytdRow.date}): 누적손익 = ${ytdRow.accumProfit}, 총자산 = ${ytdRow.totalAsset}, 기간시드증액 = ${seedYTD} -> 수익률 = ${perfYTDVal.toFixed(2)}% -> 연환산 = ${annualYTDVal.toFixed(2)}% (${daysElapsed}일 경과)`);
  console.log(`1년전 (${oneYearAgoRow.date}): 누적손익 = ${oneYearAgoRow.accumProfit}, 총자산 = ${oneYearAgoRow.totalAsset}, 기간시드증액 = ${seed1Y} -> 수익률 = ${perf1YVal.toFixed(2)}%`);
  
  displayPerf('perf1M', perf1MVal);
  displayPerf('perf3M', perf3MVal);
  displayPerf('perfYTD', perfYTDVal);
  displayPerf('perf1Y', perf1YVal);
  // 각 수익률 밑 연환산 표시
  displayAnnualEst('annual1M', annual1MVal);
  displayAnnualEst('annual3M', annual3MVal);
  displayAnnualEst('annualYTD', annualYTDVal);
}
// 입출금 왜곡 방지를 위해 누적손익 변화량과 과거 총자산(+시드증액액)을 기준으로 기간 수익률 계산
function calculatePeriodReturn(currentProfit, baseProfit, baseAsset, currentAsset, periodSeed) {
  const adjustedBase = baseAsset + periodSeed;
  if (adjustedBase <= 0) return 0;
  // 매매 거래가 없어도 자산 평가액 변동이 반영되도록, 입금/출금(시드증액)을 제외한 순수 총자산 변화량 기준으로 수익률을 계산합니다.
  const netAssetChange = currentAsset - baseAsset - periodSeed;
  return (netAssetChange / adjustedBase) * 100;
}
function displayPerf(elementId, val) {
  const el = document.getElementById(elementId);
  if (!el) return;
  
  el.innerText = formatPercent(val);
  if (val >= 0) {
    el.className = 'perf-value text-up';
  } else {
    el.className = 'perf-value text-down';
  }
}
function displayAnnualEst(elementId, val) {
  const el = document.getElementById(elementId);
  if (!el) return;
  const sign = val >= 0 ? '+' : '';
  el.innerText = `연환산 ${sign}${val.toFixed(1)}%`;
  el.style.color = val >= 0 ? 'var(--success)' : 'var(--danger)';
}
// 개별 시트 격리 파싱 함수
function parseSingleSheet(values, sheetName) {
  const backup_jjDailyData = [...jjDailyData];
  const backup_rawTransactions = [...rawTransactions];
  const backup_summaryData = { ...summaryData };
  summaryData = {
    ticker: 'SOXL',
    totalAsset: 0,
    totalCost: 0,
    totalProfit: 0,
    totalProfitRate: 0,
    realizedProfit: 0,
    currentCash: 0,
    currentHoldings: 0
  };
  parseJJData(values);
  const result = {
    summaryData: { ...summaryData },
    dailyData: [...jjDailyData],
    transactions: [...rawTransactions]
  };
  jjDailyData = backup_jjDailyData;
  rawTransactions = backup_rawTransactions;
  summaryData = backup_summaryData;
  return result;
}
// 통합 계좌 데이터 병합 및 통계 누계 가공 함수
function parseCombinedData(results) {
  const parsedSheets = results.map(r => {
    const p = parseSingleSheet(r.values, r.sheetName);
    p.transactions.forEach(t => {
      t.accountName = r.sheetName;
    });
    return p;
  });
  summaryData.ticker = '통합 계좌 (ALL)';
  summaryData.totalCost = parsedSheets.reduce((sum, s) => sum + s.summaryData.totalCost, 0);
  summaryData.realizedProfit = parsedSheets.reduce((sum, s) => sum + s.summaryData.realizedProfit, 0);
  const dateSet = new Set();
  parsedSheets.forEach(ps => {
    ps.dailyData.forEach(d => {
      const dateObj = parseDate(d.date);
      if (!isNaN(dateObj.getTime())) {
        const formattedDate = `${dateObj.getFullYear()}.${String(dateObj.getMonth() + 1).padStart(2, '0')}.${String(dateObj.getDate()).padStart(2, '0')}`;
        dateSet.add(formattedDate);
      }
    });
  });
  const sortedDates = Array.from(dateSet).sort((a, b) => {
    return new Date(a.replace(/\./g, '-')) - new Date(b.replace(/\./g, '-'));
  });
  const combinedDaily = [];
  sortedDates.forEach(dateStr => {
    let combinedObj = {
      date: dateStr,
      close: 0,
      mode: '통합 계좌',
      cash: 0,
      holdings: 0,
      evalAmt: 0,
      totalAsset: 0,
      profitRate: 0,
      dd: 0,
      accumProfit: 0,
      profit: 0,
      realized: 0,
      seed: 0
    };
    parsedSheets.forEach(ps => {
      let activeRow = null;
      for (let i = 0; i < ps.dailyData.length; i++) {
        const rowDateObj = parseDate(ps.dailyData[i].date);
        const rowDateStr = `${rowDateObj.getFullYear()}.${String(rowDateObj.getMonth() + 1).padStart(2, '0')}.${String(rowDateObj.getDate()).padStart(2, '0')}`;
        if (rowDateStr === dateStr) {
          activeRow = ps.dailyData[i];
          break;
        }
        if (rowDateStr < dateStr) {
          activeRow = ps.dailyData[i];
        } else {
          break;
        }
      }
      if (activeRow) {
        combinedObj.cash += activeRow.cash;
        combinedObj.holdings += activeRow.holdings;
        combinedObj.evalAmt += activeRow.evalAmt;
        combinedObj.totalAsset += activeRow.totalAsset;
        combinedObj.accumProfit += activeRow.accumProfit;
        combinedObj.profit += activeRow.profit;
        
        // 종가(close) 데이터가 유실되지 않도록 첫 번째로 발견되는 유효한 개별 계좌 종가를 상속
        if (activeRow.close > 0 && combinedObj.close === 0) {
          combinedObj.close = activeRow.close;
        }

        const exactMatch = ps.dailyData.find(d => {
          const dObj = parseDate(d.date);
          const dStr = `${dObj.getFullYear()}.${String(dObj.getMonth() + 1).padStart(2, '0')}.${String(dObj.getDate()).padStart(2, '0')}`;
          return dStr === dateStr;
        });
        if (exactMatch) {
          combinedObj.realized += exactMatch.realized;
          combinedObj.seed += exactMatch.seed;
        }
      }
    });
    const baseVal = combinedObj.totalAsset - combinedObj.accumProfit;
    combinedObj.profitRate = baseVal > 0 ? (combinedObj.accumProfit / baseVal) * 100 : 0;
    combinedDaily.push(combinedObj);
  });
  let peakAsset = 0;
  combinedDaily.forEach(d => {
    if (d.totalAsset > peakAsset) {
      peakAsset = d.totalAsset;
    }
    d.dd = peakAsset > 0 ? ((d.totalAsset - peakAsset) / peakAsset) * 100 : 0;
  });
  const combinedTransactions = [];
  parsedSheets.forEach(ps => {
    combinedTransactions.push(...ps.transactions);
  });
  combinedTransactions.sort((a, b) => parseDate(b.date) - parseDate(a.date));
  jjDailyData = combinedDaily;
  rawTransactions = combinedTransactions;
  if (jjDailyData.length > 0) {
    const latest = jjDailyData[jjDailyData.length - 1];
    summaryData.totalAsset = latest.totalAsset;
    summaryData.totalProfit = latest.accumProfit;
    summaryData.totalProfitRate = summaryData.totalCost > 0 ? (summaryData.totalProfit / summaryData.totalCost) * 100 : 0;
    summaryData.currentCash = latest.cash;
    summaryData.currentHoldings = latest.holdings;
  }
}
// 구글 시트 CJ10~CM열 예약 주문표 테이블 및 BN8 기준일 렌더러
function renderOrderGuideTable() {
  const container = document.getElementById('orderTableContainer');
  const baseDateEl = document.getElementById('orderBaseDate');
  if (!container) return;
  container.innerHTML = '';
  if (combinedRawData.length === 0) {
    container.innerHTML = `<div class="empty-state">불러온 주문표 데이터가 없습니다.</div>`;
    if (baseDateEl) baseDateEl.innerText = '-';
    return;
  }
  // 상단 공통 주문일 텍스트 채우기 (통합 모드 시 첫 번째 유효한 계정의 주문일 사용)
  if (baseDateEl && combinedRawData.length > 0) {
    const firstAccountValues = combinedRawData[0].values;
    let mainBaseDate = '-';
    if (firstAccountValues[8] && firstAccountValues[8][65] !== undefined && firstAccountValues[8][65] !== '') {
      mainBaseDate = String(firstAccountValues[8][65]).trim();
      // 날짜 문자열 정제 (요일 괄호 제거 등)
      mainBaseDate = mainBaseDate.replace(/[^0-9.]/g, '');
      if (mainBaseDate.endsWith('.')) {
        mainBaseDate = mainBaseDate.slice(0, -1);
      }
    }
    baseDateEl.innerText = mainBaseDate;
  }
  combinedRawData.forEach(accountData => {
    const values = accountData.values;
    const accountName = accountData.name;
    // BN9 셀의 주문일 구하기 (9행=index 8, BN열=index 65)
    let baseDate = '-';
    if (values[8] && values[8][65] !== undefined && values[8][65] !== '') {
      baseDate = String(values[8][65]).trim();
      baseDate = baseDate.replace(/[^0-9.]/g, '');
      if (baseDate.endsWith('.')) {
        baseDate = baseDate.slice(0, -1);
      }
    }
    // F7 셀 (7행 F열 = values[6][5]) 데이터를 직접 바인딩하여 기준종가를 노출하고 대비(%) 변동률 계산에 연계
    let baseClose = 0;
    if (values[6] && values[6][5] !== undefined && values[6][5] !== '') {
      baseClose = cleanNumber(values[6][5]);
    }
    
    // 폴백: F7 셀에서 획득 실패 시, 주문일 전날(직전 영업일)의 종가를 jjDailyData에서 탐색
    if (baseClose === 0 && baseDate !== '-') {
      try {
        const targetDateObj = parseDate(baseDate);
        if (!isNaN(targetDateObj.getTime())) {
          const targetDateStr = `${targetDateObj.getFullYear()}.${String(targetDateObj.getMonth() + 1).padStart(2, '0')}.${String(targetDateObj.getDate()).padStart(2, '0')}`;
          
          for (let j = jjDailyData.length - 1; j >= 0; j--) {
            const d = jjDailyData[j];
            const dObj = parseDate(d.date);
            const dStr = `${dObj.getFullYear()}.${String(dObj.getMonth() + 1).padStart(2, '0')}.${String(dObj.getDate()).padStart(2, '0')}`;
            if (dStr < targetDateStr) {
              if (d.close > 0) {
                baseClose = d.close;
                break;
              }
            }
          }
        }
      } catch (e) {
        console.error("전일 종가 탐색 오류:", e);
      }
    }
    
    // 최종 폴백: 가장 최신 영업일의 종가 사용
    if (baseClose === 0 && jjDailyData.length > 0) {
      baseClose = jjDailyData[jjDailyData.length - 1].close;
    }
    const tableRows = [];
    const headers = ['구분', '유형', '주문 단가', '대비', '주문 수량']; // '대비' 열이 추가된 5열 구조
    
    // 10행(index 9)의 CJ(87)열 값이 매수/매도 데이터인지 판별하여 시작 인덱스 설정
    let startRowIdx = 10;
    if (values[9]) {
      const firstCol = String(values[9][87]).trim();
      if (firstCol === '매수' || firstCol === '매도' || firstCol === 'BUY' || firstCol === 'SELL') {
        startRowIdx = 9;
      }
    }
    // 데이터 파싱
    for (let i = startRowIdx; i < values.length; i++) {
      const row = values[i];
      if (!row || row[87] === undefined || String(row[87]).trim() === '') {
        continue;
      }
      const side = String(row[87]).trim(); // 매수 / 매도
      const type = row[88] !== undefined ? String(row[88]).trim() : ''; // LOC 등
      const price = row[89] !== undefined ? cleanNumber(row[89]) : 0; // 단가
      const qty = row[90] !== undefined ? cleanNumber(row[90]) : 0; // 수량
      tableRows.push({ side, type, price, qty });
    }
    const orderCard = document.createElement('div');
    orderCard.className = 'glass-card';
    orderCard.style.margin = '1rem 0';
    orderCard.style.padding = '1.25rem 1rem';
    const headerHtml = `<div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:0.6rem; margin-bottom:0.75rem;">
           <span style="font-weight:700; color:var(--text-primary); font-size:0.95rem;">${accountName}</span>
           <span style="font-size:0.7rem; color:var(--text-muted); display: flex; gap: 8px;">
             <span>주문일: ${baseDate}</span>
             ${baseClose > 0 ? `<span>(기준종가: ${formatCurrency(baseClose, '$', 2)})</span>` : ''}
           </span>
         </div>`;
    if (tableRows.length === 0) {
      orderCard.innerHTML = `
        ${headerHtml}
        <div class="empty-state" style="padding:1rem;">해당 계좌에 활성화된 주문표 정보가 없습니다.</div>
      `;
    } else {
      let tableBody = '';
      tableRows.forEach(row => {
        const isBuy = row.side === '매수' || row.side.toUpperCase() === 'BUY';
        
        // 매수/매도에 따라 라벨 스킨 분리
        const sideBadge = isBuy 
          ? `<span style="background: rgba(0, 230, 118, 0.12); color: var(--success); padding: 3px 6px; border-radius: 4px; font-size: 0.72rem; font-weight:700; display: inline-block;">매수</span>`
          : `<span style="background: rgba(255, 23, 68, 0.12); color: var(--danger); padding: 3px 6px; border-radius: 4px; font-size: 0.72rem; font-weight:700; display: inline-block;">매도</span>`;
        // 전일 종가 기준 변동률(%) 독립 칼럼 데이터 생성
        let pctDiffText = '-';
        if (baseClose > 0 && row.price > 0) {
          const pctDiff = ((row.price - baseClose) / baseClose) * 100;
          const pctSign = pctDiff >= 0 ? '+' : '';
          const pctColor = pctDiff >= 0 ? 'var(--success)' : 'var(--danger)';
          pctDiffText = `<span style="color: ${pctColor}; font-weight: 700;">${pctSign}${pctDiff.toFixed(2)}%</span>`;
        }
        tableBody += `
          <tr style="border-bottom: 1px solid rgba(255,255,255,0.04);">
            <td style="padding: 0.75rem 0.5rem; text-align: left; vertical-align: middle;">${sideBadge}</td>
            <td style="padding: 0.75rem 0.5rem; color: var(--text-primary); text-align: left; vertical-align: middle; font-weight: 500;">${row.type}</td>
            <td style="padding: 0.75rem 0.5rem; color: var(--text-primary); text-align: right; vertical-align: middle; font-weight: 600;">${formatCurrency(row.price, '$', 2)}</td>
            <td style="padding: 0.75rem 0.5rem; text-align: right; vertical-align: middle;">${pctDiffText}</td>
            <td style="padding: 0.75rem 0.5rem; color: var(--text-primary); text-align: right; vertical-align: middle; font-weight: 600;">${(row.qty || 0).toLocaleString()}주</td>
          </tr>
        `;
      });
      orderCard.innerHTML = `
        ${headerHtml}
        <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
          <thead>
            <tr style="border-bottom: 2px solid rgba(255,255,255,0.08); color: var(--text-muted); font-size: 0.72rem;">
              <th style="padding: 0.5rem; text-align: left; font-weight: 600;">${headers[0]}</th>
              <th style="padding: 0.5rem; text-align: left; font-weight: 600;">${headers[1]}</th>
              <th style="padding: 0.5rem; text-align: right; font-weight: 600;">${headers[2]}</th>
              <th style="padding: 0.5rem; text-align: right; font-weight: 600;">${headers[3]}</th>
              <th style="padding: 0.5rem; text-align: right; font-weight: 600;">${headers[4]}</th>
            </tr>
          </thead>
          <tbody>
            ${tableBody}
          </tbody>
        </table>
      `;
    }
    container.appendChild(orderCard);
  });
}
// ==========================================
// 시뮬레이터 구글 시트 D2/D3 변수 쓰기 API
// ==========================================
async function updateSimulationParams(ticker, startDate) {
  if (window.location.protocol === 'file:') {
    console.log("로컬 환경 우회: 구글 시트 쓰기 스킵", ticker, startDate);
    return;
  }
  
  const targetId = DEFAULT_SHEET_ID; // 시뮬레이터 대상 시트 고정
  const url = `https://sheets.googleapis.com/v4/spreadsheets/${targetId}/values/CAL!D2:D3?valueInputOption=USER_ENTERED`;
  
  const response = await fetch(url, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      range: 'CAL!D2:D3',
      majorDimension: 'COLUMNS', // 1열에 D2, D3를 순서대로 채워 넣음
      values: [[ticker, startDate]]
    })
  });
  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    const message = errData.error?.message || response.statusText;
    throw new Error(`구글 시트 변수 쓰기 실패: ${message}`);
  }
}
// ==========================================
// 시뮬레이션 엔진 (SI 백테스트 로직)
// ==========================================
async function runSimulation() {
  if (!simTargetTicker) return;
  let ticker = simTargetTicker.value;
  if (ticker === 'MANUAL') {
    ticker = simTargetTickerManual.value.trim().toUpperCase();
    if (!ticker) {
      alert('직접 입력할 티커명을 기입해 주세요.');
      if (typeof loadingOverlay !== 'undefined') {
        loadingOverlay.style.display = 'none';
      }
      return;
    }
  }
  let startDate = simStartDate ? simStartDate.value : '2025-06-14';
  const endDate = simEndDate ? simEndDate.value : '';
  // 날짜 하한선 강제 제약 (2018-07-27)
  const minDate = new Date('2018-07-27');
  const selectedStartDate = new Date(startDate);
  if (selectedStartDate < minDate) {
    startDate = '2018-07-27';
    if (simStartDate) simStartDate.value = '2018-07-27';
  }
  const safeBuyPct = parseFloat(simSafeBuyPct.value) || 0;
  const safeSellPct = parseFloat(simSafeSellPct.value) || 0;
  const aggBuyPct = parseFloat(simAggBuyPct.value) || 0;
  const aggSellPct = parseFloat(simAggSellPct.value) || 0;
  
  const splitCount = parseInt(simSplitCount.value) || 7;
  const updatePeriod = parseInt(simUpdatePeriod.value) || 10;
  const compoundingProfitRate = parseFloat(simCompoundingProfitRate.value) || 80;
  const compoundingLossRate = parseFloat(simCompoundingLossRate.value) || 30;
  loadingOverlay.style.display = 'flex';
  
  try {
    const targetSheetId = DEFAULT_SHEET_ID;
    const simCacheKey = `stock_db_cache_sim_all_${ticker}`;
    let qqqrsiRaw, calRaw;
    let usedCache = false;
    
    try {
      const cachedSim = await dbStore.get(simCacheKey);
      if (cachedSim) {
        if (isCacheValid(cachedSim.timestamp)) {
          console.log(`[시뮬 캐시 히트] 티커:${ticker} 전체 데이터를 로컬 캐시에서 즉시 불러옵니다.`);
          qqqrsiRaw = cachedSim.qqqrsiRaw;
          calRaw = cachedSim.calRaw;
          usedCache = true;
        }
      }
    } catch (simCacheErr) {
      console.warn("시뮬레이터 캐시 로딩 중 오류 발생, 구글 시트 요청으로 대체합니다:", simCacheErr);
    }
    
    if (!usedCache) {
      // 1. 구글 시트 CAL!D2:D3 에 티커와 전체 시작일(2018-07-27) 쓰기 전송
      await updateSimulationParams(ticker, '2018-07-27');
      // 2. GOOGLEFINANCE 수식이 시트 내에서 재계산되도록 2.5초 지연 대기
      await new Promise(resolve => setTimeout(resolve, 2.5 * 1000));
      // 3. 갱신된 QQQRSI 와 CAL 시트 값 다시 로드
      qqqrsiRaw = await fetchSheetValues('QQQRSI', targetSheetId);
      calRaw = await fetchSheetValues('CAL', targetSheetId);
      
      // 성공 시 캐시 저장
      try {
        const cacheData = {
          timestamp: Date.now(),
          qqqrsiRaw,
          calRaw
        };
        await dbStore.set(simCacheKey, cacheData);
        console.log(`[시뮬 캐시 저장 완료] 티커:${ticker} 전체 데이터`);
      } catch (saveErr) {
        console.error("시뮬레이터 캐시 저장 중 오류 발생:", saveErr);
      }
    }
    
    const cVals = calRaw;
    const qVals = qqqrsiRaw;
    // 날짜/종가 열 인덱스를 데이터 행 스캔으로 자동 탐지
    // CAL 시트는 헤더행이 없고, GOOGLEFINANCE 데이터가 C열(날짜)과 D열(종가)에 위치
    let dateColIdx = 2;
    let closeColIdx = 3;
    
    let detectedDate = false;
    for (let scanRow = 4; scanRow < Math.min(20, cVals.length); scanRow++) {
      if (!cVals[scanRow] || cVals[scanRow].length < 2) continue;
      for (let ci = 0; ci < cVals[scanRow].length; ci++) {
        const cellVal = String(cVals[scanRow][ci] || '').trim();
        if (!detectedDate && /^\d{2,4}[.\-\/]\d{1,2}[.\-\/]\d{1,2}/.test(cellVal.replace(/[^0-9.\-\/]/g, ''))) {
          dateColIdx = ci;
          if (ci + 1 < cVals[scanRow].length) {
            const nextVal = cleanNumber(cVals[scanRow][ci + 1]);
            if (nextVal > 0) {
              closeColIdx = ci + 1;
            }
          }
          detectedDate = true;
          break;
        }
      }
      if (detectedDate) break;
    }
    // 날짜별 파싱 (오름차순 정렬)
    const datesData = [];
    
    for (let i = 1; i < cVals.length; i++) {
      if (!cVals[i] || !cVals[i][dateColIdx]) continue;
      const dateStr = String(cVals[i][dateColIdx]).trim();
      const closePrice = cleanNumber(cVals[i][closeColIdx]);
      
      // 날짜 형식이 아닌 행 스킵
      if (!/\d/.test(dateStr)) continue;
      
      const testParsed = parseDate(dateStr);
      const isValid = !isNaN(testParsed.getTime());
      if (!isValid || closePrice <= 0) continue;
      
      const cDateObj = parseDate(dateStr);
      const cYear = cDateObj.getFullYear();
      const cMonth = String(cDateObj.getMonth() + 1).padStart(2, '0');
      const cDay = String(cDateObj.getDate()).padStart(2, '0');
      const cDateStrKey = `${cYear}-${cMonth}-${cDay}`;
      
      // QQQRSI 시트(qVals)의 날짜 열과 매매모드 열 인덱스를 헤더 기반으로 자동 탐지
      let qDateColIdx = 9;  // 기본값 J열 (index 9)
      let qModeColIdx = 15; // 기본값 P열 (index 15)
      
      // qVals의 첫 번째 또는 상위 행들 중 헤더 행을 탐색
      let qHeaderRowIdx = -1;
      for (let rIdx = 0; rIdx < Math.min(10, qVals.length); rIdx++) {
        const row = qVals[rIdx];
        if (row && (row.includes('날짜') || row.includes('거래일자') || row.includes('일자') || row.includes('매매모드') || row.includes('모드'))) {
          qHeaderRowIdx = rIdx;
          break;
        }
      }
      
      if (qHeaderRowIdx !== -1) {
        const qHeaders = qVals[qHeaderRowIdx].map(h => String(h).trim());
        const dIdx = findHeaderIndex(qHeaders, ['거래일자', '일자', '날짜', 'date']);
        if (dIdx !== -1) qDateColIdx = dIdx;
        const mIdx = findHeaderIndex(qHeaders, ['매매모드', '모드', 'mode']);
        if (mIdx !== -1) qModeColIdx = mIdx;
      }
      
      // 주차(Week Number) 구하는 헬퍼 함수
      const getWeekNumber = (d) => {
        const date = new Date(d.getTime());
        date.setHours(0, 0, 0, 0);
        // 목요일 기준 주차 계산 (ISO-8601 기준 주차)
        date.setDate(date.getDate() + 3 - (date.getDay() + 6) % 7);
        const week1 = new Date(date.getFullYear(), 0, 4);
        return 1 + Math.round(((date.getTime() - week1.getTime()) / 86400000 - 3 + (week1.getDay() + 6) % 7) / 7);
      };
      const cYearVal = cDateObj.getFullYear();
      const cWeekVal = getWeekNumber(cDateObj);
      let mode = '안전모드';
      for (let j = qHeaderRowIdx + 1; j < qVals.length; j++) {
        if (qVals[j] && qVals[j][qDateColIdx]) {
          const qDateObj = parseDate(String(qVals[j][qDateColIdx]).trim());
          if (!isNaN(qDateObj.getTime())) {
            const qYearVal = qDateObj.getFullYear();
            const qWeekVal = getWeekNumber(qDateObj);
            
            // 연도와 주차(Week Number)가 둘 다 일치하는 행을 매핑
            if (qYearVal === cYearVal && qWeekVal === cWeekVal) {
              const modeVal = String(qVals[j][qModeColIdx] || '').trim();
              if (modeVal.includes('공세')) mode = '공세모드';
              break;
            }
          }
        }
      }
      
      datesData.push({ date: dateStr, close: closePrice, mode: mode });
    }
    // parseDate 기반 안전 오름차순 정렬
    datesData.sort((a, b) => parseDate(a.date) - parseDate(b.date));
    // 날짜 필터링 (사용자 범위 simStartDate ~ simEndDate)
    const startFilterDateObj = parseDate(startDate);
    const endFilterDateObj = endDate ? parseDate(endDate) : new Date();
    
    startFilterDateObj.setHours(0, 0, 0, 0);
    endFilterDateObj.setHours(23, 59, 59, 999);
    const filteredDatesData = datesData.filter(d => {
      const dObj = parseDate(d.date);
      if (isNaN(dObj.getTime())) return false;
      dObj.setHours(12, 0, 0, 0);
      return dObj >= startFilterDateObj && dObj <= endFilterDateObj;
    });
    if (filteredDatesData.length === 0) {
      if (datesData.length > 0) {
        const firstParsed = parseDate(datesData[0].date);
        const lastParsed = parseDate(datesData[datesData.length - 1].date);
        throw new Error(`설정하신 날짜 범위 내에 시뮬레이션 가능한 주가 데이터가 없습니다.\n\n시트 데이터 범위: ${firstParsed.toLocaleDateString()} ~ ${lastParsed.toLocaleDateString()}\n필터 범위: ${startFilterDateObj.toLocaleDateString()} ~ ${endFilterDateObj.toLocaleDateString()}`);
      } else {
        throw new Error(`CAL 시트에서 주가 데이터를 추출하지 못했습니다.`);
      }
    }
    // 백테스트 시뮬레이션 시작
    let seedAmt = 10000;
    if (simSeedAmt) {
      seedAmt = parseFloat(simSeedAmt.value) || 10000;
    }
    let cash = seedAmt;
    
    // 개별 매수 배치 관리 배열: { buyPrice, qty, cycleDays, buyMode }
    let buyBatches = [];
    
    let lastCompoundingCash = seedAmt; // 10거래일 기준 직전 예수금 기준점
    const simHistory = [];
    let simTxLog = []; // 상세 거래 로그 저장용
    for (let i = 0; i < filteredDatesData.length; i++) {
      const today = filteredDatesData[i];
      const globalIdx = datesData.findIndex(d => d.date === today.date);
      const prev = globalIdx > 0 ? datesData[globalIdx - 1] : null;
      // 1. 매도 판정 (각 배치별 독립 판정 - 매수보다 먼저 일어나야 함)
      // 배치를 뒤에서부터 순회하여 매도 조건 충족 시 청산
      for (let b = buyBatches.length - 1; b >= 0; b--) {
        const batch = buyBatches[b];
        
        // LOC 매도 목표가 결정 (매수 단가 batch.buyPrice 대비 이 배치가 매수되었을 당시의 모드 기준)
        let targetSell = 0;
        if (batch.buyMode === '공세모드') {
          targetSell = batch.buyPrice * (1 + (aggSellPct / 100));
        } else {
          targetSell = batch.buyPrice * (1 + (safeSellPct / 100));
        }
        // MOC 강제 청산 제한 일수
        const limitDays = (batch.buyMode === '공세모드') ? 7 : 30;
        let shouldSell = false;
        let sellType = 'LOC 매도';
        // 조건 A: 오늘 종가가 매도 목표가 도달 (단, 당일 매수한 배치는 당일 매도 대상에서 제외)
        if (batch.cycleDays > 0 && today.close >= targetSell) {
          shouldSell = true;
          sellType = 'LOC 매도';
        }
        // 조건 B: 청산 제한일 경과 (MOC)
        else if (batch.cycleDays >= limitDays) {
          shouldSell = true;
          sellType = 'MOC 청산';
        }
        if (shouldSell) {
          const revenue = batch.qty * today.close;
          cash += revenue;
          
          simTxLog.push({
            date: today.date,
            type: sellType,
            price: today.close,
            qty: batch.qty,
            amount: revenue,
            holdings: buyBatches.reduce((sum, x) => sum + x.qty, 0) - batch.qty,
            cash: cash,
            buyDate: batch.buyDate,
            buyPrice: batch.buyPrice
          });
          buyBatches.splice(b, 1); // 해당 배치 삭제
        }
      }
      // 3. LOC 매수 검사 및 실행 (전일 종가 기준)
      const basePriceForBuy = prev ? prev.close : today.close;
      let targetBuy = 0;
      if (today.mode === '공세모드') {
        targetBuy = basePriceForBuy * (1 + (aggBuyPct / 100));
      } else {
        targetBuy = basePriceForBuy * (1 + (safeBuyPct / 100));
      }
      if (today.close <= targetBuy) {
        // 1회 매수 분량: (예수금 기준점 / 7) -> 손익 갱신 주기(10일) 전에는 항상 고정된 lastCompoundingCash 분량 사용
        const buyLimitAmt = lastCompoundingCash / splitCount;
        const buyQty = Math.floor(buyLimitAmt / targetBuy);
        const cost = buyQty * today.close;
        if (buyQty > 0 && cash >= cost) {
          cash -= cost;
          buyBatches.push({
            buyPrice: today.close,
            qty: buyQty,
            cycleDays: 0, // 당일 매수 시점의 경과일은 0
            buyMode: today.mode,
            buyDate: today.date
          });
          simTxLog.push({
            date: today.date,
            type: 'LOC 매수',
            price: today.close,
            qty: buyQty,
            amount: cost,
            holdings: buyBatches.reduce((sum, x) => sum + x.qty, 0),
            cash: cash
          });
        }
      }
      // 3. 10거래일 단위 복리 주기 반영 (엑셀 수식 기반)
      // 각 일자별 실현 손익 추적
      let todayRealizedProfit = 0;
      const todaySells = simTxLog.filter(tx => tx.date === today.date && (tx.type.includes('매도') || tx.type.includes('청산')));
      todaySells.forEach(tx => {
        if (tx.buyPrice !== undefined) {
          const buyCost = tx.buyPrice * tx.qty;
          const sellAmt = tx.price * tx.qty;
          todayRealizedProfit += (sellAmt - buyCost);
        }
      });
      today.realized = todayRealizedProfit;
      
      // 당일 장 시작 시각 기준(전날 마감 기준)의 1회당 분할 매수 예정액 및 기준 예수금을 history에 선기록합니다.
      const buyLimitAmt = lastCompoundingCash / splitCount;
      let compoundingAmtVal = 0;
      let isCompoundingDay = false;
      // 10거래일 단위 복리가 적용되는 시점을 엑셀과 1:1로 맞추기 위해 인덱스 계산을 조정합니다.
      // 1/15일은 filteredDatesData 기준 10번째 행(인덱스 i = 9)입니다.
      // 따라서 (i + 1) % updatePeriod === 0 조건일 때 복리를 계산하고 1/15일자에 표시하도록 설정합니다.
      if (i > 0 && (i + 1) % updatePeriod === 0) {
        // BFS: 최근 updatePeriod(10거래일) 동안의 당일실현손익 합산
        let bfs = 0;
        for (let idx = i - (updatePeriod - 1); idx <= i; idx++) {
          if (filteredDatesData[idx]) {
            bfs += (filteredDatesData[idx].realized || 0);
          }
        }
        if (bfs < 0) {
          compoundingAmtVal = bfs * (compoundingLossRate / 100);
        } else {
          compoundingAmtVal = bfs * (compoundingProfitRate / 100);
        }
        
        lastCompoundingCash += compoundingAmtVal;
        lastCompoundingCash = Math.max(1000, lastCompoundingCash);
        isCompoundingDay = true;
      }
      
      // 4. 기존 매수 배치들의 경과일(cycleDays) 1씩 증가 (당일 매수분은 다음날부터 경과일 카운트가 증가해야 1일 차 청산 대상이 됨)
      buyBatches.forEach(batch => batch.cycleDays++);
      const evalAmt = buyBatches.reduce((sum, b) => sum + (b.qty * today.close), 0);
      const totalAsset = cash + evalAmt;
      
      simHistory.push({ 
        date: today.date, 
        totalAsset, 
        cash, 
        evalAmt, 
        close: today.close, 
        mdd: 0, 
        buyLimitAmt,
        compoundingAmt: isCompoundingDay ? compoundingAmtVal : 0,
        updatedCompoundingCash: isCompoundingDay ? lastCompoundingCash : 0
      });
    }
    const lastDay = filteredDatesData[filteredDatesData.length - 1];
    const finalHoldingsQty = buyBatches.reduce((sum, b) => sum + b.qty, 0);
    const finalAsset = cash + buyBatches.reduce((sum, b) => sum + (b.qty * lastDay.close), 0);
    const totalReturn = ((finalAsset - seedAmt) / seedAmt) * 100;
    const realizedProfitVal = finalAsset - seedAmt;
    
    // MDD 계산 및 각 히스토리 항목에 기록
    let peak = seedAmt;
    let mdd = 0;
    simHistory.forEach(h => {
      if (h.totalAsset > peak) peak = h.totalAsset;
      const dd = ((h.totalAsset - peak) / peak) * 100;
      h.mdd = Math.abs(dd); // 양수로 저장 (차트에서 reversed 축 사용)
      if (dd < mdd) mdd = dd;
    });
    const years = filteredDatesData.length / 252;
    const cagr = years > 0 ? ((Math.pow(finalAsset / seedAmt, 1 / years)) - 1) * 100 : totalReturn;
    document.getElementById('simTotalReturn').innerText = `${totalReturn >= 0 ? '+' : ''}${totalReturn.toFixed(2)}%`;
    document.getElementById('simTotalReturn').className = totalReturn >= 0 ? 'text-up' : 'text-down';
    document.getElementById('simMDD').innerText = `${mdd.toFixed(2)}%`;
    document.getElementById('simCAGR').innerText = `${cagr >= 0 ? '+' : ''}${cagr.toFixed(2)}%`;
    
    if (simRealizedProfit) {
      simRealizedProfit.innerText = formatCurrency(realizedProfitVal, '$');
      simRealizedProfit.className = realizedProfitVal >= 0 ? 'text-up font-title' : 'text-down font-title';
    }
    // 상세 거래 내역 표 렌더링 (엑셀 1줄 형식으로 변환)
    if (simDetailTableBody) {
      if (filteredDatesData.length === 0) {
        simDetailTableBody.innerHTML = `<tr><td colspan="14" style="padding: 1rem; text-align: center; color: var(--text-muted);">데이터가 없습니다.</td></tr>`;
      } else {
        // 일자별로 매수/매도 내역 매핑용 구조화
        const rowMap = {};
        
        // 날짜별 빈 행 뼈대 생성
        filteredDatesData.forEach(d => {
          rowMap[d.date] = {
            date: d.date,
            close: d.close,
            mode: d.mode,
            buyLimitAmt: '',
            buyQty: '',
            buyAmt: '',
            targetSell: '',
            sellDate: '',
            sellPrice: '',
            sellQty: '',
            sellAmt: '',
            cash: '',
            todayRealized: '', // 실제 매도 완료일 기준 당일 실현 금액
            compoundingAmt: '', // 복리 금액
            updatedCompoundingCash: '', // 자금 갱신 금액
            profitAmt: '', // 1:1 대응 거래의 순수 손익 금액
            accumProfit: ''
          };
        });
        // simHistory를 기반으로 예수금(cash), 매수예정금액, 추가복리 및 자금갱신 기입
        simHistory.forEach(h => {
          if (rowMap[h.date]) {
            rowMap[h.date].cash = formatCurrency(h.cash, '$', 2);
            rowMap[h.date].buyLimitAmt = formatCurrency(h.buyLimitAmt, '$', 2);
            if (h.compoundingAmt !== 0) {
              rowMap[h.date].compoundingAmt = formatCurrency(h.compoundingAmt, '$', 2);
              rowMap[h.date].updatedCompoundingCash = formatCurrency(h.updatedCompoundingCash, '$', 2);
            }
          }
        });
        // 1. 매수 기록은 해당 매수일 행에 직접 기입
        simTxLog.forEach(tx => {
          if (tx.type === 'LOC 매수') {
            if (rowMap[tx.date]) {
              rowMap[tx.date].buyQty = `${tx.qty}주`;
              rowMap[tx.date].buyAmt = formatCurrency(tx.amount, '$', 2);
              
              // 해당 매수분에 대한 목표가 산정
              let targetVal = 0;
              if (rowMap[tx.date].mode === '공세모드') {
                targetVal = tx.price * (1 + (aggSellPct / 100));
              } else {
                targetVal = tx.price * (1 + (safeSellPct / 100));
              }
              rowMap[tx.date].targetSell = formatCurrency(targetVal, '$', 2);
            }
          }
        });
        // 2. 매도 기록 매칭 및 매매 손익 기입 (매수일 기준 행 우측에 매도 정보 기록)
        const sellTxs = simTxLog.filter(tx => tx.type.includes('매도') || tx.type.includes('청산'));
        sellTxs.forEach(sellTx => {
          if (sellTx.buyDate && rowMap[sellTx.buyDate]) {
            const r = rowMap[sellTx.buyDate];
            r.sellDate = sellTx.date;
            r.sellPrice = formatCurrency(sellTx.price, '$', 2);
            r.sellQty = `${sellTx.qty}주`;
            r.sellAmt = formatCurrency(sellTx.amount, '$', 2);
            
            // 손익 계산: 매도금액 - 매수금액
            const buyAmtNum = sellTx.qty * sellTx.buyPrice;
            const sellAmtNum = sellTx.amount;
            const profitNum = sellAmtNum - buyAmtNum;
            
            r.profitAmt = formatCurrency(profitNum, '$', 2);
          }
        });
        // 3. 실제 날짜 순서대로 돌면서 실제 매도가 확정된(sellDate가 도래한) 날에 누적손익(accumProfit)과 당일실현(todayRealized)을 기록합니다.
        let accumRealized = 0;
        filteredDatesData.forEach(d => {
          const r = rowMap[d.date];
          // 오늘 매도 완료된 모든 건들의 실현손익 합산
          let todayTotalRealized = 0;
          Object.values(rowMap).forEach(row => {
            if (row.sellDate === d.date && row.profitAmt) {
              todayTotalRealized += cleanNumber(row.profitAmt);
            }
          });
          if (todayTotalRealized !== 0) {
            accumRealized += todayTotalRealized;
            r.todayRealized = formatCurrency(todayTotalRealized, '$', 2);
            r.accumProfit = formatCurrency(accumRealized, '$', 2);
          } else {
            r.todayRealized = '-';
            if (accumRealized !== 0) {
              // 오늘 매도는 안되었지만 과거 누적금액이 있으면 누적 손익란에 이월액 유지 표시
              r.accumProfit = formatCurrency(accumRealized, '$', 2);
            }
          }
        });

        // HTML 문자열 렌더링 (17열 구조)
        simDetailTableBody.innerHTML = filteredDatesData.map(d => {
          const r = rowMap[d.date];
          const modeColor = r.mode.includes('공세') ? 'color: var(--danger); font-weight:700;' : 'color: var(--success); font-weight:700;';
          const buyColor = r.buyQty ? 'background: rgba(0, 230, 118, 0.04); font-weight:600;' : '';
          const sellColor = r.sellQty ? 'background: rgba(255, 23, 68, 0.04); font-weight:600;' : '';
          const compoundingColor = r.compoundingAmt ? 'background: rgba(157, 78, 221, 0.08); font-weight:700;' : '';
          
          return `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
              <td style="padding: 0.45rem 0.4rem; font-weight:600;">${r.date}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right;">${formatCurrency(r.close, '$', 2)}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:center; ${modeColor}">${r.mode}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right;">${r.buyLimitAmt || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:center; ${buyColor}">${r.buyQty || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; ${buyColor}">${r.buyAmt || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right;">${r.targetSell || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:center; ${sellColor}">${r.sellDate || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; ${sellColor}">${r.sellPrice || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:center; ${sellColor}">${r.sellQty || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; ${sellColor}">${r.sellAmt || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right;">${r.cash || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; color: var(--success); font-weight:700;">${r.todayRealized || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; color: var(--success);">${r.profitAmt || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; font-weight:700;">${r.accumProfit || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; color: #a29bfe; ${compoundingColor}">${r.compoundingAmt || '-'}</td>
              <td style="padding: 0.45rem 0.4rem; text-align:right; color: #e84393; ${compoundingColor}">${r.updatedCompoundingCash || '-'}</td>
            </tr>
          `;
        }).join('');
      }
    }
    let targetBuy = 0;
    let targetSell = 0;
    if (filteredDatesData.length > 0) {
      const lastDay = filteredDatesData[filteredDatesData.length - 1];
      const prev = filteredDatesData.length > 1 ? filteredDatesData[filteredDatesData.length - 2] : null;
      const basePrice = prev ? prev.close : lastDay.close;
      if (lastDay.mode === '공세모드') {
        targetBuy = basePrice * (1 + (aggBuyPct / 100));
        targetSell = finalHoldingsQty > 0 ? basePrice * (1 + (aggSellPct / 100)) : 0;
      } else {
        targetBuy = basePrice * (1 + (safeBuyPct / 100));
        targetSell = finalHoldingsQty > 0 ? basePrice * (1 + (safeSellPct / 100)) : 0;
      }
    }
    // 백테스트 전체 결과 저장용 데이터 구조화
    simulationResult = {
      ticker: ticker,
      startDate: startDate,
      endDate: endDate,
      params: { safeBuyPct, safeSellPct, aggBuyPct, aggSellPct, splitCount, updatePeriod, compoundingProfitRate, compoundingLossRate, seedAmt },
      summary: { totalReturn, mdd, cagr, realizedProfitVal },
      history: simHistory,
      txLog: simTxLog
    };
    if (simSaveActionArea) {
      simSaveActionArea.style.display = 'grid';
    }
    renderSimulationChart(simHistory);
    renderOrderGuideTable();
  } catch (e) {
    console.error(e);
    alert("시뮬레이션 중 오류가 발생했습니다: " + e.message);
  } finally {
    loadingOverlay.style.display = 'none';
  }
}
function renderSimulationChart(history) {
  const chartEl = document.querySelector("#simulationChart");
  if (!chartEl) return;
  chartEl.innerHTML = '';
  
  if (simulationChart) simulationChart.destroy();
  const dates = history.map(h => h.date);
  const evalAmts = history.map(h => h.evalAmt);
  const cashes = history.map(h => h.cash);
  const totalAssets = history.map(h => h.totalAsset);
  const mddVals = history.map(h => h.mdd || 0);
  // MDD 최대값 계산하여 보조 y축 범위 결정
  const validMddVals = mddVals.filter(v => !isNaN(v));
  const maxMddVal = validMddVals.length > 0 ? Math.max(...validMddVals) : 10;
  const finalMaxMdd = maxMddVal > 0 ? Math.ceil(maxMddVal / 10) * 10 : 10;

  // Y축 금액 최댓값 자동 산출 (주식 평가금, 보유 예수금, 총자산 가치 전체 중 최댓값 기준)
  const allAssetVals = [...evalAmts, ...cashes, ...totalAssets].filter(v => v !== undefined && v !== null && !isNaN(v));
  const maxAssetVal = allAssetVals.length > 0 ? Math.max(...allAssetVals) : 10000;
  
  // 금액 규모에 따라 올림 단위(Step) 결정 (약 5~10% 마진 적용)
  let step = 50000;
  if (maxAssetVal <= 30000) {
    step = 5000;
  } else if (maxAssetVal <= 100000) {
    step = 10000;
  } else if (maxAssetVal <= 250000) {
    step = 25000;
  }
  const finalMaxAsset = Math.ceil((maxAssetVal * 1.05) / step) * step;

  const themeOpts = getThemeChartOptions();
  const options = {
    series: [
      { name: '주식 평가금', type: 'area', data: evalAmts },
      { name: '보유 예수금', type: 'area', data: cashes },
      { name: '총자산 가치', type: 'line', data: totalAssets },
      { name: 'MDD', type: 'line', data: mddVals }
    ],
    chart: {
      height: 240,
      type: 'line',
      foreColor: themeOpts.foreColor,
      toolbar: { show: false },
      zoom: { enabled: false }
    },
    colors: themeOpts.colors.concat(['#ff1744']),
    stroke: {
      width: [1.5, 1.5, 2.5, 2],
      curve: 'smooth'
    },
    fill: {
      type: 'solid',
      opacity: [0.2, 0.2, 1, 1]
    },
    dataLabels: { enabled: false },
    xaxis: {
      categories: dates,
      labels: { show: false },
      axisBorder: { show: false },
      axisTicks: { show: false }
    },
    yaxis: [
      {
        seriesName: '주식 평가금',
        showForNullSeries: true,
        min: 0,
        max: finalMaxAsset,
        labels: {
          style: { fontSize: '9px' },
          formatter: function (val) { return formatCurrency(val, '$'); }
        }
      },
      {
        seriesName: '보유 예수금',
        showForNullSeries: true,
        min: 0,
        max: finalMaxAsset,
        show: false
      },
      {
        seriesName: '총자산 가치',
        showForNullSeries: true,
        min: 0,
        max: finalMaxAsset,
        show: false
      },
      {
        seriesName: 'MDD',
        showForNullSeries: true,
        opposite: true,
        reversed: true,
        min: 0,
        max: finalMaxMdd,
        labels: {
          style: { fontSize: '11px' },
          formatter: function (val) {
            if (val === undefined || val === null || isNaN(val)) return '0.0%';
            return val > 0 ? `-${val.toFixed(1)}%` : '0.0%';
          }
        }
      }
    ],
    tooltip: {
      theme: 'dark',
      shared: true,
      y: {
        formatter: function (val, opts) {
          if (opts.seriesIndex === 3) {
            if (val === undefined || val === null || isNaN(val)) return '0.00%';
            return val > 0 ? `-${val.toFixed(2)}%` : '0.00%';
          }
          return formatCurrency(val, '$');
        }
      }
    },
    grid: {
      borderColor: 'rgba(255,255,255,0.03)',
      padding: {
        left: 5,
        right: 5
      }
    },
    legend: {
      position: 'top',
      fontSize: '10px',
      fontFamily: 'Inter, sans-serif',
      offsetX: 0,
      offsetY: 0,
      itemMargin: {
        horizontal: 6,
        vertical: 0
      }
    }
  };
  simulationChart = new ApexCharts(chartEl, options);
  simulationChart.render();
}

// ==========================================
// 백테스트 결과 로컬 저장소 (LocalStorage) CRUD 연동
// ==========================================

// 1. 저장된 이력 목록 불러오기 및 UI 갱신
async function loadSavedSimList() {
  if (!simSavedList) return;
  simSavedList.innerHTML = '<option value="">-- 불러올 이력을 선택하세요 --</option>';
  
  try {
    const savedList = await dbStore.get('stock_db_saved_sim_list') || [];
    
    savedList.forEach(item => {
      const opt = document.createElement('option');
      opt.value = item.key;
      opt.innerText = item.alias;
      simSavedList.appendChild(opt);
    });
  } catch (err) {
    console.error('저장된 백테스트 목록 로딩 실패:', err);
  }
}

// 2. 현재 백테스트 결과 저장
async function saveSimResult(alias) {
  if (!simulationResult) return;
  
  try {
    const timestamp = Date.now();
    // 마이크로초 대용 난수 덧붙임으로 단위테스트 환경 등에서 고유성 확보
    const key = `stock_db_sim_saved_${timestamp}_${Math.floor(Math.random() * 1000)}`;
    
    const saveData = {
      key: key,
      alias: alias,
      timestamp: timestamp,
      ticker: simulationResult.ticker,
      startDate: simulationResult.startDate,
      endDate: simulationResult.endDate,
      params: simulationResult.params,
      summary: simulationResult.summary,
      history: simulationResult.history,
      txLog: simulationResult.txLog
    };
    
    // IndexedDB 데이터 저장
    await dbStore.set(key, saveData);
    
    // 인덱스 목록 갱신
    const savedList = await dbStore.get('stock_db_saved_sim_list') || [];
    savedList.push({ key: key, alias: alias });
    await dbStore.set('stock_db_saved_sim_list', savedList);
    
    await loadSavedSimList();
    // 저장된 항목을 드롭다운에서 선택된 상태로 변경
    if (simSavedList) {
      simSavedList.value = key;
    }
    alert(`'${alias}' 백테스트 결과가 브라우저에 성공적으로 저장되었습니다.`);
  } catch (err) {
    console.error('백테스트 결과 저장 실패:', err);
    alert('결과 저장에 실패했습니다: ' + err.message);
  }
}

// 3. 저장된 백테스트 이력 삭제
async function deleteSimResult(key) {
  try {
    await dbStore.delete(key);
    
    let savedList = await dbStore.get('stock_db_saved_sim_list') || [];
    savedList = savedList.filter(item => item.key !== key);
    await dbStore.set('stock_db_saved_sim_list', savedList);
    
    await loadSavedSimList();
    
    // 화면상의 액션 버튼 및 결과 초기화
    if (simSaveActionArea) {
      simSaveActionArea.style.display = 'none';
    }
    simulationResult = null;
    alert('백테스트 기록이 삭제되었습니다.');
  } catch (err) {
    console.error('백테스트 이력 삭제 실패:', err);
  }
}

// 4. 저장 이력 화면 복원
function restoreSimResult(data) {
  if (!data) return;
  
  // 파라미터 폼 복원
  if (simTargetTicker) {
    if (['SOXL', 'TQQQ'].includes(data.ticker)) {
      simTargetTicker.value = data.ticker;
      if (simManualTickerWrapper) simManualTickerWrapper.style.display = 'none';
    } else {
      simTargetTicker.value = 'MANUAL';
      if (simManualTickerWrapper) {
        simManualTickerWrapper.style.display = 'block';
        if (simTargetTickerManual) simTargetTickerManual.value = data.ticker;
      }
    }
  }
  if (simStartDate) simStartDate.value = data.startDate;
  if (simEndDate) simEndDate.value = data.endDate;
  if (simSeedAmt) simSeedAmt.value = data.params.seedAmt;
  if (simSafeBuyPct) simSafeBuyPct.value = data.params.safeBuyPct;
  if (simSafeSellPct) simSafeSellPct.value = data.params.safeSellPct;
  if (simAggBuyPct) simAggBuyPct.value = data.params.aggBuyPct;
  if (simAggSellPct) simAggSellPct.value = data.params.aggSellPct;
  if (simSplitCount) simSplitCount.value = data.params.splitCount;
  if (simUpdatePeriod) simUpdatePeriod.value = data.params.updatePeriod;
  if (simCompoundingProfitRate) simCompoundingProfitRate.value = data.params.compoundingProfitRate;
  if (simCompoundingLossRate) simCompoundingLossRate.value = data.params.compoundingLossRate;
  
  // 요약 성적 표기 복원
  const summary = data.summary;
  document.getElementById('simTotalReturn').innerText = `${summary.totalReturn >= 0 ? '+' : ''}${summary.totalReturn.toFixed(2)}%`;
  document.getElementById('simTotalReturn').className = summary.totalReturn >= 0 ? 'text-up' : 'text-down';
  document.getElementById('simMDD').innerText = `${summary.mdd.toFixed(2)}%`;
  document.getElementById('simCAGR').innerText = `${summary.cagr >= 0 ? '+' : ''}${summary.cagr.toFixed(2)}%`;
  
  if (simRealizedProfit) {
    simRealizedProfit.innerText = formatCurrency(summary.realizedProfitVal, '$');
    simRealizedProfit.className = summary.realizedProfitVal >= 0 ? 'text-up font-title' : 'text-down font-title';
  }
  
  // 상세 거래 내역 표 복원 렌더링
  if (simDetailTableBody && data.history && data.txLog) {
    const rowMap = {};
    
    // 날짜 뼈대 구축
    data.history.forEach(h => {
      rowMap[h.date] = {
        date: h.date,
        close: h.close,
        mode: h.date === data.history[0].date ? '안전모드' : '', // 기본 바인딩용 예외 가드
        buyLimitAmt: formatCurrency(h.buyLimitAmt, '$', 2),
        buyQty: '',
        buyAmt: '',
        targetSell: '',
        sellDate: '',
        sellPrice: '',
        sellQty: '',
        sellAmt: '',
        cash: formatCurrency(h.cash, '$', 2),
        todayRealized: '',
        compoundingAmt: h.compoundingAmt !== 0 ? formatCurrency(h.compoundingAmt, '$', 2) : '',
        updatedCompoundingCash: h.updatedCompoundingCash !== 0 ? formatCurrency(h.updatedCompoundingCash, '$', 2) : '',
        profitAmt: '',
        accumProfit: ''
      };
    });
    
    // 매수 기록 채우기
    data.txLog.forEach(tx => {
      if (tx.type === 'LOC MY' || tx.type === 'LOC 매수') {
        if (rowMap[tx.date]) {
          rowMap[tx.date].buyQty = `${tx.qty}주`;
          rowMap[tx.date].buyAmt = formatCurrency(tx.amount, '$', 2);
          
          // 매매 모드 바인딩 복원용 예외 추적
          rowMap[tx.date].mode = tx.buyMode || '안전모드';
          
          const targetVal = tx.buyMode === '공세모드' 
            ? tx.price * (1 + (data.params.aggSellPct / 100))
            : tx.price * (1 + (data.params.safeSellPct / 100));
          rowMap[tx.date].targetSell = formatCurrency(targetVal, '$', 2);
        }
      }
    });
    
    // 매도 매칭 및 1:1 손익 채우기
    const sellTxs = data.txLog.filter(tx => tx.type.includes('매도') || tx.type.includes('청산'));
    sellTxs.forEach(sellTx => {
      if (sellTx.buyDate && rowMap[sellTx.buyDate]) {
        const r = rowMap[sellTx.buyDate];
        r.sellDate = sellTx.date;
        r.sellPrice = formatCurrency(sellTx.price, '$', 2);
        r.sellQty = `${sellTx.qty}주`;
        r.sellAmt = formatCurrency(sellTx.amount, '$', 2);
        
        const buyAmtNum = sellTx.qty * sellTx.buyPrice;
        const sellAmtNum = sellTx.amount;
        const profitNum = sellAmtNum - buyAmtNum;
        r.profitAmt = formatCurrency(profitNum, '$', 2);
      }
    });
    
    // 매도완료일 기준 당일실현 및 누적손익 복원 계산
    let accumRealized = 0;
    data.history.forEach(h => {
      const r = rowMap[h.date];
      
      // 모드 매핑 복원 보완
      const activeTx = data.txLog.find(tx => tx.date === h.date);
      if (activeTx) {
        r.mode = activeTx.buyMode || '안전모드';
      } else {
        // 이전 행 모드 상속
        const idx = data.history.findIndex(x => x.date === h.date);
        if (idx > 0) {
          r.mode = rowMap[data.history[idx - 1].date].mode || '안전모드';
        }
      }
      
      let todayTotalRealized = 0;
      Object.values(rowMap).forEach(row => {
        if (row.sellDate === h.date && row.profitAmt) {
          todayTotalRealized += cleanNumber(row.profitAmt);
        }
      });
      if (todayTotalRealized !== 0) {
        accumRealized += todayTotalRealized;
        r.todayRealized = formatCurrency(todayTotalRealized, '$', 2);
        r.accumProfit = formatCurrency(accumRealized, '$', 2);
      } else {
        r.todayRealized = '-';
        if (accumRealized !== 0) {
          r.accumProfit = formatCurrency(accumRealized, '$', 2);
        }
      }
    });
    
    // 표 HTML 렌더링
    simDetailTableBody.innerHTML = data.history.map(h => {
      const r = rowMap[h.date];
      const modeColor = r.mode.includes('공세') ? 'color: var(--danger); font-weight:700;' : 'color: var(--success); font-weight:700;';
      const buyColor = r.buyQty ? 'background: rgba(0, 230, 118, 0.04); font-weight:600;' : '';
      const sellColor = r.sellQty ? 'background: rgba(255, 23, 68, 0.04); font-weight:600;' : '';
      const compoundingColor = r.compoundingAmt ? 'background: rgba(157, 78, 221, 0.08); font-weight:700;' : '';
      
      return `
        <tr style="border-bottom: 1px solid rgba(255,255,255,0.03);">
          <td style="padding: 0.45rem 0.4rem; font-weight:600;">${r.date}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:right;">${formatCurrency(r.close, '$', 2)}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:center; ${modeColor}">${r.mode}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:right;">${r.buyLimitAmt || '-'}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:center; ${buyColor}">${r.buyQty || '-'}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:right; ${buyColor}">${r.buyAmt || '-'}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:right;">${r.targetSell || '-'}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:center; ${sellColor}">${r.sellDate || '-'}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:right; ${sellColor}">${r.sellPrice || '-'}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:center; ${sellColor}">${r.sellQty || '-'}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:right; ${sellColor}">${r.sellAmt || '-'}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:right;">${r.cash || '-'}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:right; color: var(--success); font-weight:700;">${r.todayRealized || '-'}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:right; color: var(--success);">${r.profitAmt || '-'}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:right; font-weight:700;">${r.accumProfit || '-'}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:right; color: #a29bfe; ${compoundingColor}">${r.compoundingAmt || '-'}</td>
          <td style="padding: 0.45rem 0.4rem; text-align:right; color: #e84393; ${compoundingColor}">${r.updatedCompoundingCash || '-'}</td>
        </tr>
      `;
    }).join('');
  }
  
  // 차트 복원
  renderSimulationChart(data.history);
  
  // 결과 저장용 활성 변수 주입
  simulationResult = data;
  if (simSaveActionArea) {
    simSaveActionArea.style.display = 'grid';
  }
  
  lucide.createIcons();
}

// 5. 백테스트 데이터를 JSON 텍스트 파일로 즉시 다운로드하는 단독 함수
function exportSimResultDirect(data) {
  if (!data) return;
  try {
    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${data.alias || 'backtest_result'}_${data.ticker}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('JSON 내보내기 실패:', err);
    alert('JSON 파일 내보내기에 실패했습니다.');
  }
}

// 6. 저장된 키값을 찾아 JSON 내보내기 수행
async function exportSimResultToJson(key) {
  try {
    const data = await dbStore.get(key);
    if (!data) return;
    exportSimResultDirect(data);
  } catch (err) {
    console.error('JSON 다운로드 처리 실패:', err);
  }
}

// 7. 업로드된 JSON 백업 파일로부터 결과 복원
function importSimResultFromJson(file) {
  const reader = new FileReader();
  reader.onload = function(e) {
    try {
      const data = JSON.parse(e.target.result);
      if (!data.ticker || !data.history || !data.txLog) {
        throw new Error('유효한 백테스트 결과 구조가 아닙니다.');
      }
      
      // 화면 복원 실행
      restoreSimResult(data);
      
      // 사용자에게 로컬 저장소 목록에도 등록할 것인지 권유
      const alias = data.alias || `${data.ticker}_가져옴_${Date.now()}`;
      if (confirm(`가져온 백테스트 결과('${alias}')를 브라우저 로컬 저장 목록에도 등록하시겠습니까?`)) {
        saveSimResult(alias);
      } else {
        alert('백테스트 결과가 화면에만 복원되었습니다. (저장 목록 등록 안 함)');
        if (simSavedList) simSavedList.value = '';
      }
    } catch (err) {
      console.error('JSON 파일 로딩 실패:', err);
      alert('백업 파일 해석에 실패했습니다. 올바른 백테스트 JSON 파일인지 확인해 주세요.');
    }
  };
  reader.readAsText(file);
}


