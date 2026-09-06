from __future__ import annotations

"""
Quantitative Analysis & ML Forecasting Tools
Provides functions for technical indicators, risk metrics, and ML-based price forecasting.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from loguru import logger

# ============================================
# FIX: Import serialization helper
# ============================================
from ..utils.serialization import convert_to_serializable

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None  # type: ignore[assignment]
    PANDAS_AVAILABLE = False
    logger.warning("pandas is not available. Using pure-Python numeric fallbacks.")

try:
    from sklearn.preprocessing import MinMaxScaler
    from sklearn.metrics import mean_squared_error, mean_absolute_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("Scikit-learn not available. Some features will be limited.")

try:
    import statsmodels.api as sm
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False
    logger.warning("Statsmodels not available. ARIMA models will not work.")

try:
    from models.lstm_model import LSTMModel
    from models.arima_model import ARIMAModel
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    logger.warning("ML models not available. Using fallback forecasting.")


def _prepare_prices_dataframe(prices: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(prices or []).copy()
    if df.empty:
        return df

    for column in ["open", "high", "low", "close", "adj_close", "volume"]:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("date")

    df = df.ffill().bfill()
    return df


def _last_mean(values: List[float], window: int) -> Optional[float]:
    if not values:
        return None
    window_values = values[-window:] if len(values) >= window else values
    return float(sum(window_values) / len(window_values))


def _last_std(values: List[float], window: int) -> Optional[float]:
    if not values:
        return None
    window_values = values[-window:] if len(values) >= window else values
    if len(window_values) < 2:
        return 0.0
    return float(np.std(window_values, ddof=1))


def _ema_series(values: List[float], span: int) -> List[float]:
    if not values:
        return []
    alpha = 2 / (span + 1)
    ema_values = [float(values[0])]
    for value in values[1:]:
        ema_values.append(alpha * float(value) + (1 - alpha) * ema_values[-1])
    return ema_values


def _rsi_value(closes: List[float], period: int = 14) -> Optional[float]:
    if len(closes) < 2:
        return None
    deltas = np.diff(np.array(closes, dtype=float))
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    if len(gains) < period:
        period = len(gains)
    avg_gain = gains[-period:].mean() if period > 0 else 0.0
    avg_loss = losses[-period:].mean() if period > 0 else 0.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))


def _true_range_values(highs: List[float], lows: List[float], closes: List[float]) -> List[float]:
    tr_values: List[float] = []
    previous_close = None
    for high, low, close in zip(highs, lows, closes):
        candidates = [high - low]
        if previous_close is not None:
            candidates.extend([abs(high - previous_close), abs(low - previous_close)])
        tr_values.append(float(max(candidates)))
        previous_close = close
    return tr_values


def calculate_technical_indicators(prices: List[Dict]) -> Dict[str, Any]:
    """
    Calculates technical indicators from historical price data.
    
    Args:
        prices: List of dictionaries with 'close', 'high', 'low', 'volume' keys
    
    Returns:
        Dictionary containing technical indicators
    """
    try:
        logger.info("Calculating technical indicators")
        
        if not prices or len(prices) < 20:
            logger.warning("Insufficient data for technical indicators")
            return {}
        
        indicators = {}

        if PANDAS_AVAILABLE:
            # Convert to DataFrame
            df = _prepare_prices_dataframe(prices)
            if df.empty or "close" not in df.columns:
                return {}
            if "high" not in df.columns:
                df["high"] = df["close"]
            if "low" not in df.columns:
                df["low"] = df["close"]
            if "volume" not in df.columns:
                df["volume"] = 0.0

            close_values = df["close"].tolist()
            high_values = df["high"].tolist()
            low_values = df["low"].tolist()
            volume_values = df["volume"].tolist()
        else:
            rows = [row for row in prices if row.get("close") is not None]
            if len(rows) < 20:
                return {}
            close_values = [float(row["close"]) for row in rows]
            high_values = [float(row.get("high", row["close"])) for row in rows]
            low_values = [float(row.get("low", row["close"])) for row in rows]
            volume_values = [float(row.get("volume", 0) or 0) for row in rows]

        indicators['SMA_20'] = _last_mean(close_values, 20)
        indicators['SMA_50'] = _last_mean(close_values, 50) if len(close_values) >= 50 else None
        indicators['SMA_200'] = _last_mean(close_values, 200) if len(close_values) >= 200 else None

        ema_12_series = _ema_series(close_values, 12)
        ema_26_series = _ema_series(close_values, 26)
        indicators['EMA_12'] = ema_12_series[-1]
        indicators['EMA_26'] = ema_26_series[-1]

        macd_series = [ema12 - ema26 for ema12, ema26 in zip(ema_12_series[-len(ema_26_series):], ema_26_series)] if len(ema_12_series) >= len(ema_26_series) else []
        if not macd_series:
            macd_series = [ema_12_series[-1] - ema_26_series[-1]]
        macd_signal_series = _ema_series(macd_series, 9)
        indicators['MACD'] = macd_series[-1]
        indicators['MACD_signal'] = macd_signal_series[-1]
        indicators['MACD_histogram'] = indicators['MACD'] - indicators['MACD_signal']

        indicators['RSI'] = _rsi_value(close_values, 14)

        sma_20 = _last_mean(close_values, 20)
        std_20 = _last_std(close_values, 20) or 0.0
        indicators['Bollinger_Bands'] = {
            'upper': sma_20 + 2 * std_20 if sma_20 is not None else None,
            'middle': sma_20,
            'lower': sma_20 - 2 * std_20 if sma_20 is not None else None
        }

        true_range_values = _true_range_values(high_values, low_values, close_values)
        indicators['ATR'] = _last_mean(true_range_values, 14)

        indicators['Volume_SMA'] = _last_mean(volume_values, 20)
        indicators['Volume_Ratio'] = volume_values[-1] / indicators['Volume_SMA'] if indicators['Volume_SMA'] and indicators['Volume_SMA'] > 0 else 1

        stochastic_k_series: List[float] = []
        for index, close_price in enumerate(close_values):
            window = min(14, index + 1)
            window_lows = low_values[index - window + 1:index + 1]
            window_highs = high_values[index - window + 1:index + 1]
            low_14 = min(window_lows)
            high_14 = max(window_highs)
            if high_14 != low_14:
                stochastic_k_series.append(((close_price - low_14) / (high_14 - low_14)) * 100)
            else:
                stochastic_k_series.append(0.0)
        indicators['Stochastic_K'] = stochastic_k_series[-1]
        indicators['Stochastic_D'] = _last_mean(stochastic_k_series, 3) or stochastic_k_series[-1]
        
        logger.info("Technical indicators calculated successfully")
        
        # ============================================
        # FIX: Convert NumPy types before returning
        # ============================================
        return convert_to_serializable(indicators)
        
    except Exception as e:
        logger.error(f"Error calculating technical indicators: {str(e)}")
        return {}


def calculate_risk_metrics(prices: List[Dict], benchmark_returns: Optional[List[float]] = None) -> Dict[str, Any]:
    """
    Calculates risk metrics from historical price data.
    
    Args:
        prices: List of dictionaries with 'close' key
        benchmark_returns: Optional benchmark returns for beta calculation
    
    Returns:
        Dictionary containing risk metrics
    """
    try:
        logger.info("Calculating risk metrics")
        
        if not prices or len(prices) < 30:
            logger.warning("Insufficient data for risk metrics")
            return {}
        
        rows = [row for row in prices if row.get("close") is not None]
        if len(rows) < 30:
            return {}

        close_values = [float(row["close"]) for row in rows]
        returns = np.diff(np.array(close_values, dtype=float)) / np.array(close_values[:-1], dtype=float)
        if len(returns) == 0:
            return {}
        returns_series = pd.Series(returns) if PANDAS_AVAILABLE else None
        
        risk_metrics = {}
        
        # Volatility (standard deviation of returns)
        risk_metrics['volatility'] = float(np.std(returns, ddof=1) * np.sqrt(252))  # Annualized
        
        # Sharpe Ratio (assuming risk-free rate of 2%)
        risk_free_rate = 0.02
        excess_returns = float(np.mean(returns) * 252 - risk_free_rate)
        risk_metrics['Sharpe_ratio'] = float(excess_returns / risk_metrics['volatility']) if risk_metrics['volatility'] > 0 else 0
        
        # Sortino Ratio
        downside_returns = returns[returns < 0]
        downside_deviation = float(np.std(downside_returns, ddof=1) * np.sqrt(252)) if len(downside_returns) > 1 else 0
        risk_metrics['Sortino_ratio'] = float(excess_returns / downside_deviation) if downside_deviation > 0 else 0
        
        # Maximum Drawdown
        cumulative_returns = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        risk_metrics['max_drawdown'] = float(np.min(drawdown))
        
        # Value at Risk (VaR) at 95% confidence
        risk_metrics['VaR_95'] = float(np.quantile(returns, 0.05))
        risk_metrics['VaR_99'] = float(np.quantile(returns, 0.01))
        
        # Conditional VaR (Expected Shortfall)
        tail_returns = returns[returns <= risk_metrics['VaR_95']]
        cvar = float(np.mean(tail_returns)) if len(tail_returns) else None
        risk_metrics['CVaR_95'] = cvar
        
        # Beta (if benchmark provided)
        if benchmark_returns:
            benchmark_series = np.array([float(value) for value in benchmark_returns if value is not None], dtype=float)
            if len(benchmark_series) == len(close_values):
                benchmark_series = np.diff(benchmark_series) / benchmark_series[:-1]
            if len(benchmark_series) == len(returns) and len(benchmark_series) > 1:
                covariance = np.cov(returns, benchmark_series)[0][1]
                benchmark_variance = np.var(benchmark_series, ddof=1)
                risk_metrics['beta'] = float(covariance / benchmark_variance) if benchmark_variance > 0 else 1.0
        
        # Skewness and Kurtosis
        if PANDAS_AVAILABLE and returns_series is not None:
            risk_metrics['skewness'] = float(returns_series.skew())
            risk_metrics['kurtosis'] = float(returns_series.kurtosis())
        else:
            centered = returns - np.mean(returns)
            std_dev = np.std(returns, ddof=1)
            if std_dev > 0:
                risk_metrics['skewness'] = float(np.mean((centered / std_dev) ** 3))
                risk_metrics['kurtosis'] = float(np.mean((centered / std_dev) ** 4) - 3)
            else:
                risk_metrics['skewness'] = 0.0
                risk_metrics['kurtosis'] = 0.0
        
        logger.info("Risk metrics calculated successfully")
        
        # ============================================
        # FIX: Convert NumPy types before returning
        # ============================================
        return convert_to_serializable(risk_metrics)
        
    except Exception as e:
        logger.error(f"Error calculating risk metrics: {str(e)}")
        return {}


def forecast_price_lstm(prices: List[Dict], forecast_days: int = 30) -> Dict[str, Any]:
    """
    Forecasts prices using LSTM model.
    
    Args:
        prices: List of dictionaries with 'close' key
        forecast_days: Number of days to forecast
    
    Returns:
        Dictionary containing forecast results
    """
    try:
        logger.info(f"Forecasting prices using LSTM for {forecast_days} days")
        
        if not prices or len(prices) < 60:
            logger.warning("Insufficient data for LSTM forecasting")
            return fallback_forecast(prices, forecast_days)
        
        if not MODELS_AVAILABLE or not SKLEARN_AVAILABLE:
            logger.warning("ML models not available, using fallback forecast")
            return fallback_forecast(prices, forecast_days)
        
        # Prepare data
        close_prices = [float(p['close']) for p in prices if p.get('close')]
        
        if len(close_prices) < 60:
            return fallback_forecast(prices, forecast_days)
        
        # Scale data
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(np.array(close_prices).reshape(-1, 1))
        
        # Create sequences
        sequence_length = 60
        X, y = [], []
        for i in range(sequence_length, len(scaled_data)):
            X.append(scaled_data[i-sequence_length:i, 0])
            y.append(scaled_data[i, 0])
        
        X, y = np.array(X), np.array(y)
        X = X.reshape(X.shape[0], X.shape[1], 1)
        
        # Train LSTM model
        try:
            model = LSTMModel(input_shape=(X.shape[1], 1))
            model.train(X, y)
            
            # Make predictions
            last_sequence = scaled_data[-sequence_length:].reshape(1, sequence_length, 1)
            predictions = []
            
            for _ in range(forecast_days):
                pred = model.predict(last_sequence)
                predictions.append(pred[0, 0])
                last_sequence = np.roll(last_sequence, -1, axis=1)
                last_sequence[0, -1, 0] = pred[0, 0]
            
            # Inverse transform predictions
            predictions = scaler.inverse_transform(np.array(predictions).reshape(-1, 1)).flatten()
            
            current_price = close_prices[-1]
            forecast_7d = predictions[6] if len(predictions) > 6 else predictions[-1]
            forecast_30d = predictions[-1] if len(predictions) >= forecast_days else predictions[-1]
            
            logger.info(f"LSTM forecast completed: 7d={forecast_7d:.2f}, 30d={forecast_30d:.2f}")
            
            result = {
                'model': 'LSTM',
                'forecast_7d': forecast_7d,
                'forecast_30d': forecast_30d,
                'all_forecasts': predictions.tolist(),
                'current_price': current_price,
                'confidence': 0.75  # Placeholder confidence
            }
            
            # ============================================
            # FIX: Convert NumPy types before returning
            # ============================================
            return convert_to_serializable(result)
            
        except Exception as e:
            logger.error(f"LSTM model error: {str(e)}")
            return fallback_forecast(prices, forecast_days)
        
    except Exception as e:
        logger.error(f"Error in LSTM forecasting: {str(e)}")
        return fallback_forecast(prices, forecast_days)


def forecast_price_arima(prices: List[Dict], forecast_days: int = 30) -> Dict[str, Any]:
    """
    Forecasts prices using ARIMA model.
    
    Args:
        prices: List of dictionaries with 'close' key
        forecast_days: Number of days to forecast
    
    Returns:
        Dictionary containing forecast results
    """
    try:
        logger.info(f"Forecasting prices using ARIMA for {forecast_days} days")
        
        if not prices or len(prices) < 30:
            logger.warning("Insufficient data for ARIMA forecasting")
            return fallback_forecast(prices, forecast_days)
        
        if not STATSMODELS_AVAILABLE:
            logger.warning("Statsmodels not available, using fallback forecast")
            return fallback_forecast(prices, forecast_days)
        
        # Prepare data
        close_prices = [float(p['close']) for p in prices if p.get('close')]
        
        if len(close_prices) < 30:
            return fallback_forecast(prices, forecast_days)
        
        # Fit ARIMA model
        try:
            model = sm.tsa.ARIMA(close_prices, order=(5, 1, 0))
            model_fit = model.fit()
            
            # Make predictions
            forecast = model_fit.forecast(steps=forecast_days)
            
            current_price = close_prices[-1]
            forecast_7d = forecast[6] if len(forecast) > 6 else forecast[-1]
            forecast_30d = forecast[-1] if len(forecast) >= forecast_days else forecast[-1]
            
            logger.info(f"ARIMA forecast completed: 7d={forecast_7d:.2f}, 30d={forecast_30d:.2f}")
            
            result = {
                'model': 'ARIMA',
                'forecast_7d': forecast_7d,
                'forecast_30d': forecast_30d,
                'all_forecasts': forecast.tolist(),
                'current_price': current_price,
                'confidence': 0.70  # Placeholder confidence
            }
            
            # ============================================
            # FIX: Convert NumPy types before returning
            # ============================================
            return convert_to_serializable(result)
            
        except Exception as e:
            logger.error(f"ARIMA model error: {str(e)}")
            return fallback_forecast(prices, forecast_days)
        
    except Exception as e:
        logger.error(f"Error in ARIMA forecasting: {str(e)}")
        return fallback_forecast(prices, forecast_days)


def fallback_forecast(prices: List[Dict], forecast_days: int = 30) -> Dict[str, Any]:
    """
    Fallback forecasting using simple moving average and trend.
    
    Args:
        prices: List of dictionaries with 'close' key
        forecast_days: Number of days to forecast
    
    Returns:
        Dictionary containing forecast results
    """
    try:
        logger.info("Using fallback forecasting method")
        
        if not prices:
            result = {
                'model': 'Fallback',
                'forecast_7d': None,
                'forecast_30d': None,
                'confidence': 0.3
            }
            return convert_to_serializable(result)
        
        close_prices = [float(p['close']) for p in prices if p.get('close')]
        
        if len(close_prices) < 2:
            result = {
                'model': 'Fallback',
                'forecast_7d': close_prices[-1] if close_prices else None,
                'forecast_30d': close_prices[-1] if close_prices else None,
                'confidence': 0.3
            }
            return convert_to_serializable(result)
        
        # Calculate trend
        recent_prices = close_prices[-20:] if len(close_prices) >= 20 else close_prices
        trend = (recent_prices[-1] - recent_prices[0]) / len(recent_prices)
        
        current_price = close_prices[-1]
        
        # Simple linear extrapolation
        forecast_7d = current_price + (trend * 7)
        forecast_30d = current_price + (trend * 30)
        
        # Ensure forecasts are positive
        forecast_7d = max(forecast_7d, current_price * 0.9)
        forecast_30d = max(forecast_30d, current_price * 0.8)
        
        logger.info(f"Fallback forecast: 7d={forecast_7d:.2f}, 30d={forecast_30d:.2f}")
        
        result = {
            'model': 'Fallback',
            'forecast_7d': forecast_7d,
            'forecast_30d': forecast_30d,
            'current_price': current_price,
            'confidence': 0.4
        }
        
        # ============================================
        # FIX: Convert NumPy types before returning
        # ============================================
        return convert_to_serializable(result)
        
    except Exception as e:
        logger.error(f"Error in fallback forecasting: {str(e)}")
        result = {
            'model': 'Fallback',
            'forecast_7d': None,
            'forecast_30d': None,
            'confidence': 0.0
        }
        return convert_to_serializable(result)


def perform_fundamental_analysis(company_info: Dict, financial_statements: Dict) -> Dict[str, Any]:
    """
    Performs fundamental analysis using company info and financial statements.
    
    Args:
        company_info: Dictionary with company information
        financial_statements: Dictionary with financial statements
    
    Returns:
        Dictionary containing fundamental analysis results
    """
    try:
        logger.info("Performing fundamental analysis")
        
        analysis = {}
        
        # P/E Analysis
        pe_ratio = company_info.get('pe_ratio')
        if pe_ratio:
            analysis['pe_analysis'] = {'current_pe': pe_ratio}
            if pe_ratio < 15:
                analysis['pe_analysis']['valuation'] = 'Undervalued'
            elif pe_ratio > 30:
                analysis['pe_analysis']['valuation'] = 'Overvalued'
            else:
                analysis['pe_analysis']['valuation'] = 'Fairly Valued'
        
        # PEG Analysis
        peg_ratio = company_info.get('peg_ratio')
        if peg_ratio:
            analysis['peg_analysis'] = {'current_peg': peg_ratio}
            analysis['peg_analysis']['interpretation'] = 'Good value' if peg_ratio < 1 else 'Overvalued' if peg_ratio > 2 else 'Fair value'
        
        # Profitability Analysis
        income_stmt = financial_statements.get('income_statement', {})
        if income_stmt:
            revenue = income_stmt.get('total_revenue', 0)
            net_income = income_stmt.get('net_income', 0)
            
            if revenue > 0:
                analysis['profitability'] = {
                    'net_margin': net_income / revenue if revenue > 0 else 0,
                    'revenue': revenue,
                    'net_income': net_income
                }
                
                if analysis['profitability']['net_margin'] > 0.20:
                    analysis['profitability']['rating'] = 'Excellent'
                elif analysis['profitability']['net_margin'] > 0.10:
                    analysis['profitability']['rating'] = 'Good'
                else:
                    analysis['profitability']['rating'] = 'Poor'
        
        # Balance Sheet Health
        balance_sheet = financial_statements.get('balance_sheet', {})
        if balance_sheet:
            total_assets = balance_sheet.get('total_assets', 0)
            total_liabilities = balance_sheet.get('total_liabilities', 0)
            shareholders_equity = balance_sheet.get('shareholders_equity', 0)
            
            if total_assets > 0:
                debt_to_equity = total_liabilities / shareholders_equity if shareholders_equity > 0 else 0
                analysis['balance_sheet'] = {
                    'debt_to_equity': debt_to_equity,
                    'total_assets': total_assets,
                    'total_liabilities': total_liabilities
                }
                
                if debt_to_equity < 0.5:
                    analysis['balance_sheet']['health'] = 'Strong'
                elif debt_to_equity < 1.0:
                    analysis['balance_sheet']['health'] = 'Moderate'
                else:
                    analysis['balance_sheet']['health'] = 'Weak'
        
        # DCF Valuation (simplified)
        if income_stmt and (cash_flow := financial_statements.get('cash_flow', {})):
            free_cash_flow = cash_flow.get('free_cash_flow', 0)
            if free_cash_flow > 0:
                # Simplified DCF: FCF * growth_rate / discount_rate
                growth_rate = 0.05  # Assume 5% growth
                discount_rate = 0.10  # 10% discount rate
                intrinsic_value = free_cash_flow * (1 + growth_rate) / (discount_rate - growth_rate)
                
                analysis['dcf_analysis'] = {
                    'intrinsic_value': intrinsic_value,
                    'free_cash_flow': free_cash_flow,
                    'assumed_growth': growth_rate,
                    'discount_rate': discount_rate
                }
        
        logger.info("Fundamental analysis completed")
        
        # ============================================
        # FIX: Convert NumPy types before returning
        # ============================================
        return convert_to_serializable(analysis)
        
    except Exception as e:
        logger.error(f"Error in fundamental analysis: {str(e)}")
        return {}


def calculate_position_size(
    current_price: float,
    account_value: float,
    risk_per_trade: float = 0.02,
    stop_loss_pct: float = 0.05
) -> Dict[str, Any]:
    """
    Calculates recommended position size based on risk parameters.
    
    Args:
        current_price: Current stock price
        account_value: Total account/portfolio value
        risk_per_trade: Risk percentage per trade (default 2%)
        stop_loss_pct: Stop loss percentage (default 5%)
    
    Returns:
        Dictionary containing position sizing recommendations
    """
    try:
        logger.info("Calculating position size")
        
        # Calculate dollar amount to risk
        risk_amount = account_value * risk_per_trade
        
        # Calculate stop loss amount per share
        stop_loss_amount = current_price * stop_loss_pct
        
        # Calculate number of shares
        if stop_loss_amount > 0:
            shares = int(risk_amount / stop_loss_amount)
        else:
            shares = 0
        
        # Calculate position value
        position_value = shares * current_price
        
        # Calculate position as percentage of portfolio
        position_pct = position_value / account_value if account_value > 0 else 0
        
        result = {
            'shares': shares,
            'position_value': position_value,
            'position_percentage': position_pct,
            'risk_amount': risk_amount,
            'stop_loss_price': current_price * (1 - stop_loss_pct),
            'risk_per_trade': risk_per_trade,
            'stop_loss_percentage': stop_loss_pct
        }
        
        logger.info(f"Position size calculated: {shares} shares ({position_pct:.2%} of portfolio)")
        
        # ============================================
        # FIX: Convert NumPy types before returning
        # ============================================
        return convert_to_serializable(result)
        
    except Exception as e:
        logger.error(f"Error calculating position size: {str(e)}")
        return {}


def perform_complete_quant_analysis(
    historical_prices: List[Dict],
    company_info: Dict,
    financial_statements: Dict,
    forecast_days: int = 30
) -> Dict[str, Any]:
    """
    Performs complete quantitative analysis including technical indicators, 
    risk metrics, forecasting, and fundamental analysis.
    
    Args:
        historical_prices: List of historical price dictionaries
        company_info: Company information dictionary
        financial_statements: Financial statements dictionary
        forecast_days: Number of days to forecast
    
    Returns:
        Dictionary containing all quantitative analysis results
    """
    logger.info("Performing complete quantitative analysis")
    
    results = {
        'technical_indicators': None,
        'risk_metrics': None,
        'price_forecast': None,
        'fundamental_analysis': None,
        'position_sizing': None
    }
    
    # Technical indicators
    results['technical_indicators'] = calculate_technical_indicators(historical_prices)
    
    # Risk metrics
    results['risk_metrics'] = calculate_risk_metrics(historical_prices)
    
    # Price forecasting (try LSTM first, fallback to ARIMA)
    lstm_forecast = forecast_price_lstm(historical_prices, forecast_days)
    if lstm_forecast.get('confidence', 0) > 0.5:
        results['price_forecast'] = lstm_forecast
    else:
        results['price_forecast'] = forecast_price_arima(historical_prices, forecast_days)
    
    # Fundamental analysis
    results['fundamental_analysis'] = perform_fundamental_analysis(company_info, financial_statements)
    
    # Position sizing (placeholder values)
    if company_info.get('current_price'):
        results['position_sizing'] = calculate_position_size(
            company_info['current_price'],
            account_value=100000,  # Placeholder account value
            risk_per_trade=0.02,
            stop_loss_pct=0.05
        )
    
    logger.info("Complete quantitative analysis finished")
    
    # ============================================
    # FIX: Convert NumPy types before returning
    # ============================================
    return convert_to_serializable(results)