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
            fallback_prices = {"TQQQ": 77.03, "SOXL": 48.50, "QQQ": 480.00}
            val = fallback_prices.get(ticker.upper(), 50.0)
            logger.warning(f"yfinance 데이터 조회 실패로 fallback 가격 적용 ({ticker}): ${val}")
            return val
        
        # yfinance 반환형의 MultiIndex 처리 방지 및 최신 종가 가져오기
        try:
            if isinstance(df.columns, pd.MultiIndex):
                close_series = df['Close'][ticker]
            else:
                close_series = df['Close']
                
            close_series = close_series.dropna()
            if close_series.empty:
                raise ValueError("종가 데이터가 비어있습니다.")

            # 미국 동부시간(NY) 기준 현재 장중 여부 판별
            try:
                from zoneinfo import ZoneInfo
                ny_tz = ZoneInfo("America/New_York")
                now_ny = datetime.datetime.now(ny_tz)
                today_ny_str = now_ny.strftime("%Y-%m-%d")
                
                last_date_str = close_series.index[-1].strftime("%Y-%m-%d")
                
                # 마지막 행이 오늘(미국 날짜)이고, 아직 장 마감시간(16:00 EDT) 전이라면 미완성 장중 데이터로 판단하여 직전 영업일 종가 사용
                if last_date_str == today_ny_str and now_ny.hour < 16:
                    if len(close_series) >= 2:
                        latest_close = close_series.iloc[-2]
                    else:
                        latest_close = close_series.iloc[-1]
                else:
                    latest_close = close_series.iloc[-1]
            except Exception:
                latest_close = close_series.iloc[-1]
            
            return float(latest_close)
        except Exception as e:
            fallback_prices = {"TQQQ": 77.03, "SOXL": 48.50, "QQQ": 480.00}
            val = fallback_prices.get(ticker.upper(), 50.0)
            logger.error(f"최근 종가 추출 오류 ({ticker}): {e}. fallback 가격 적용: ${val}")
            return val

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
        매주 금요일 종가를 기준으로 단순 이동평균(SMA) 기반 주간 RSI를 계산합니다.
        오늘이 속한 주의 월요일 이전까지 완전히 확정된 주봉들만 반영하여 구글 시트의 날짜 매핑과 일치시킵니다.
        """
        try:
            logger.info(f"Fetching daily data for {ticker} to build Friday-based weekly RSI")
            df = yf.download(ticker, period="2y", auto_adjust=False, progress=False)
            if df.empty:
                return None
                
            if isinstance(df.columns, pd.MultiIndex):
                close_series = df['Close'][ticker]
            else:
                close_series = df['Close']
                
            close_series = close_series.dropna()
            
            # 오늘이 속한 주의 월요일 구하기
            today = datetime.date.today()
            today_monday = today - datetime.timedelta(days=today.weekday())
            today_monday_ts = pd.Timestamp(today_monday)
            
            # 월요일 이전의 일봉 데이터만 필터링하여 주간 종가 재구성
            close_series_filtered = close_series[close_series.index < today_monday_ts]
            
            # 금요일 종가 필터링 (금요일 휴장 시 목요일 종가)
            weekly_close = close_series_filtered.resample('W-FRI').last().dropna()
            
            if len(weekly_close) < period + 2:
                logger.warning(f"데이터가 부족하여 주간 RSI 계산 불가: {ticker}")
                return None
                
            # SMA 기반 RSI 계산
            delta = weekly_close.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            rsi = rsi.round(2)
            
            # 마지막 2개의 값을 추출 (1주전=latest, 2주전=prev)
            prev_rsi = float(rsi.iloc[-2])
            latest_rsi = float(rsi.iloc[-1])
            
            trend = "상승" if latest_rsi >= prev_rsi else "하락"
            
            logger.info(f"Weekly SMA RSI for {ticker} - 2w ago: {prev_rsi:.2f}, 1w ago: {latest_rsi:.2f}, Trend: {trend}")
            return (prev_rsi, latest_rsi, trend)
            
        except Exception as e:
            logger.error(f"주간 RSI 계산 오류 ({ticker}): {e}")
            return None
