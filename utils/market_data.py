import yfinance as yf
import pandas as pd
import datetime
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class MarketDataManager:
    """
    야후 파이낸스(yfinance)를 통해 시장 데이터를 조회하고 캐싱하는 매니저 클래스.
    동일한 종목의 데이터를 반복해서 호출하는 것을 방지합니다.
    """
    _instance = None
    _cache: Dict[str, pd.DataFrame] = {}
    _last_update_date = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MarketDataManager, cls).__new__(cls)
        return cls._instance

    def _get_data(self, ticker: str, period: str = "6mo") -> Optional[pd.DataFrame]:
        today = datetime.date.today()
        # 캐시가 오늘 날짜가 아니면 초기화
        if self._last_update_date != today:
            self._cache.clear()
            self._last_update_date = today

        if ticker in self._cache:
            return self._cache[ticker]

        try:
            logger.info(f"Fetching market data for {ticker} (period: {period})")
            df = yf.download(ticker, period=period, progress=False)
            if df.empty:
                logger.error(f"데이터를 불러오지 못했습니다: {ticker}")
                return None
            self._cache[ticker] = df
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return None

    def get_latest_close(self, ticker: str) -> Optional[float]:
        """
        가장 최근의 종가를 반환합니다.
        """
        df = self._get_data(ticker)
        if df is None or df.empty:
            return None
        
        # yfinance 반환형의 MultiIndex 처리 방지 및 최신 종가 가져오기
        try:
            if isinstance(df.columns, pd.MultiIndex):
                close_series = df['Close'][ticker]
            else:
                close_series = df['Close']
            
            latest_close = close_series.dropna().iloc[-1]
            return float(latest_close)
        except Exception as e:
            logger.error(f"최근 종가 추출 오류 ({ticker}): {e}")
            return None

    def get_rsi(self, ticker: str, period: int = 14) -> Optional[float]:
        """
        주어진 기간(기본 14일)에 대한 가장 최근의 RSI를 계산하여 반환합니다.
        """
        df = self._get_data(ticker, period="1y") # RSI 계산을 위해 넉넉한 기간
        if df is None or df.empty:
            return None

        try:
            if isinstance(df.columns, pd.MultiIndex):
                close_series = df['Close'][ticker]
            else:
                close_series = df['Close']

            close_series = close_series.dropna()
            if len(close_series) < period:
                logger.warning(f"데이터가 부족하여 RSI 계산 불가: {ticker}")
                return None

            delta = close_series.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)

            # Wilder's Smoothing 적용 (보통 pandas.ewm 사용)
            avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            latest_rsi = rsi.iloc[-1]
            return float(latest_rsi)
        except Exception as e:
            logger.error(f"RSI 계산 오류 ({ticker}): {e}")
            return None

    def get_weekly_rsi_data(self, ticker: str, period: int = 14) -> Optional[Tuple[float, float, str]]:
        """
        14주봉 단위 Wilder's RSI를 계산하여 반환합니다.
        반환값: (2주전 RSI, 1주전(최신) RSI, 추세('상승' 또는 '하락'))
        """
        try:
            logger.info(f"Fetching weekly data for {ticker} (interval: 1wk)")
            df = yf.download(ticker, period="1y", interval="1wk", progress=False)
            if df.empty:
                return None
                
            if isinstance(df.columns, pd.MultiIndex):
                close_series = df['Close'][ticker]
            else:
                close_series = df['Close']
                
            close_series = close_series.dropna()
            if len(close_series) < period + 2:
                logger.warning(f"데이터가 부족하여 주간 RSI 계산 불가: {ticker}")
                return None
                
            delta = close_series.diff()
            gain = delta.where(delta > 0, 0.0)
            loss = -delta.where(delta < 0, 0.0)

            # Wilder's Smoothing (알파 = 1/period)
            avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
            avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            # 마지막 2개의 값을 추출 (1주전=latest, 2주전=prev)
            # yfinance의 1wk interval의 마지막 row는 보통 현재 진행중인 주봉입니다.
            prev_rsi = float(rsi.iloc[-2])
            latest_rsi = float(rsi.iloc[-1])
            
            trend = "상승" if latest_rsi >= prev_rsi else "하락"
            
            logger.info(f"Weekly RSI for {ticker} - 2w ago: {prev_rsi:.2f}, 1w ago: {latest_rsi:.2f}, Trend: {trend}")
            return (prev_rsi, latest_rsi, trend)
            
        except Exception as e:
            logger.error(f"주간 RSI 계산 오류 ({ticker}): {e}")
            return None
