import pandas as pd
from dataclasses import dataclass
from Leverage_Point import get_price_data, calculate_sma, calculate_rsi, calculate_bollinger_bands

@dataclass
class UsdSignalResult:
    ticker: str              # 종목명 (KRW=X)
    latest_date: str         # 최신 거래일
    close: float             # 현재 환율
    daily_return_pct: float  # 전일 대비 등락률
    sma200: float            # 200일 이동평균선 (120일선에서 교체됨)
    bb_lower: float          # 볼린저 밴드 하단
    rsi14: float             # RSI 값
    below_sma200: bool       # 200일선 아래 여부
    below_bb_lower: bool     # 볼린저 밴드 하단 이탈 여부
    rsi35_or_less: bool      # RSI 35 이하 여부
    signal_msg: str          # 조건 충족 메시지
    action_text: str         # 실제 행동 문구


# 환율 조건 계산하는 함수
def get_usd_conditions(df: pd.DataFrame) -> tuple[dict, pd.Series, str]:
    latest = df.iloc[-1]
    latest_date = df.index[-1].date().isoformat()

    conditions = {
        "below_sma200"   : bool(latest["close"] < latest["sma200"]),
        "below_bb_lower" : bool(latest["close"] <= latest["bb_lower"]),
        "rsi35_or_less"  : bool(latest["rsi14"] <= 35),
    }
    return conditions, latest, latest_date


# 환율 신호 로직
def get_usd_signal(conditions: dict) -> tuple[str, str]:
    if conditions["rsi35_or_less"] and conditions["below_bb_lower"] and conditions["below_sma200"]:
        return "RSI 35 이하 & BB 하단 이탈 & 200일선 아래", "적극 환전 구간"
    
    elif conditions["rsi35_or_less"] and conditions["below_bb_lower"]:
        return "RSI 35 이하 & BB 하단 이탈", "소극 환전 구간"
    
    else:
        return "관망", "대기"


# 매매 신호를 계산하는 함수
def get_usd_signal_data(ticker: str = "KRW=X", period: str = "1y") -> UsdSignalResult:
    years = int(period.replace("y", ""))
    fetch_period = f"{years + 1}y"

    data = get_price_data(ticker, fetch_period)
    close = data["Close"].squeeze()
    returns = close.pct_change(fill_method=None)

    sma5, sma20, sma60, sma120, sma200 = calculate_sma(close)
    rsi14 = calculate_rsi(close)
    std20, bb_upper, bb_lower = calculate_bollinger_bands(close)

    df = pd.DataFrame({
        "close"   : close,
        "return"  : returns,
        "sma200"  : sma200,
        "rsi14"   : rsi14,
        "bb_lower": bb_lower
    })
    df = df.dropna()
    df = df.tail(252 * years)

    if len(df) < 2:
        raise ValueError(f"{ticker} 계산 가능한 데이터가 부족합니다.")

    conditions, latest, latest_date = get_usd_conditions(df)
    signal_msg, action_text = get_usd_signal(conditions)

    return UsdSignalResult(
        ticker           = ticker.upper(),
        latest_date      = latest_date,
        close            = float(latest["close"]),
        daily_return_pct = float(latest["return"] * 100),
        sma200           = float(latest["sma200"]),
        bb_lower         = float(latest["bb_lower"]),
        rsi14            = float(latest["rsi14"]),
        below_sma200     = conditions["below_sma200"],
        below_bb_lower   = conditions["below_bb_lower"],
        rsi35_or_less    = conditions["rsi35_or_less"],
        signal_msg       = signal_msg,
        action_text      = action_text
    )


# 텔레그램 메시지 전송하는 함수
def build_usd_message(ticker: str = "KRW=X", period: str = "1y") -> str:
    try:
        result = get_usd_signal_data(ticker, period)
    except Exception as e:
        return f"⚠️ 환율 데이터 조회 실패: {e}"

    lines = [
        f"{result.latest_date}\n",
        f"[USD/KRW 환율]",
        f"• 현재가(등락률) : {result.close:,.2f}원 ({result.daily_return_pct:+.2f}%)",
        f"• 200일선 : {result.sma200:,.2f}원",
        f"• 볼린저하단 : {result.bb_lower:,.2f}원",
        f"• RSI : {result.rsi14:.1f}",
        "----------------------------------------------------",
        f">> {result.signal_msg}",
        f">> {result.action_text}",
    ]
    return "\n".join(lines)