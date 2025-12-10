"""
Binance API 数据获取模块
用于获取实时价格和历史数据
"""

from binance.client import Client
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time


class BinanceDataFetcher:
    """Binance 数据获取器"""

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        初始化 Binance 客户端

        Args:
            api_key: Binance API Key (可选，获取公开数据不需要)
            api_secret: Binance API Secret (可选)
        """
        if api_key and api_secret:
            self.client = Client(api_key, api_secret)
        else:
            # 不需要 API key 也可以获取公开市场数据
            self.client = Client()

    def get_current_price(self, symbol: str) -> float:
        """
        获取当前价格

        Args:
            symbol: 交易对符号，例如 'BTCUSDT'

        Returns:
            当前价格
        """
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            print(f"获取 {symbol} 价格失败: {e}")
            return 0.0

    def get_all_current_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        批量获取当前价格

        Args:
            symbols: 交易对列表

        Returns:
            价格字典 {symbol: price}
        """
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.get_current_price(symbol)
            time.sleep(0.1)  # 避免请求过快
        return prices

    def get_historical_klines(
        self,
        symbol: str,
        interval: str = '1d',
        days_back: int = 180
    ) -> pd.DataFrame:
        """
        获取历史K线数据

        Args:
            symbol: 交易对符号
            interval: K线间隔 ('1m', '5m', '1h', '1d' 等)
            days_back: 向前获取多少天的数据

        Returns:
            包含历史数据的 DataFrame
        """
        try:
            # 计算开始时间
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days_back)

            # 转换为毫秒时间戳
            start_str = start_time.strftime('%Y-%m-%d')
            end_str = end_time.strftime('%Y-%m-%d')

            # 获取 K线数据
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=interval,
                start_str=start_str,
                end_str=end_str
            )

            # 转换为 DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            # 数据类型转换
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['date'] = df['timestamp']

            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)

            # 只保留需要的列
            df = df[['date', 'open', 'high', 'low', 'close', 'volume']]

            return df

        except Exception as e:
            print(f"获取 {symbol} 历史数据失败: {e}")
            return pd.DataFrame()

    def get_market_summary(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        获取市场概况

        Args:
            symbols: 交易对列表

        Returns:
            市场概况字典
        """
        summary = {}

        for symbol in symbols:
            try:
                # 获取24小时统计
                ticker_24h = self.client.get_ticker(symbol=symbol)

                summary[symbol] = {
                    'current_price': float(ticker_24h['lastPrice']),
                    'price_change_24h': float(ticker_24h['priceChange']),
                    'price_change_pct_24h': float(ticker_24h['priceChangePercent']),
                    'high_24h': float(ticker_24h['highPrice']),
                    'low_24h': float(ticker_24h['lowPrice']),
                    'volume_24h': float(ticker_24h['volume']),
                    'quote_volume_24h': float(ticker_24h['quoteVolume']),
                    'trades_24h': int(ticker_24h['count'])
                }

                time.sleep(0.1)  # 避免请求过快

            except Exception as e:
                print(f"获取 {symbol} 市场概况失败: {e}")
                summary[symbol] = None

        return summary

    def calculate_volatility(self, symbol: str, days: int = 30) -> float:
        """
        计算历史波动率

        Args:
            symbol: 交易对符号
            days: 计算天数

        Returns:
            年化波动率
        """
        try:
            df = self.get_historical_klines(symbol, interval='1d', days_back=days)

            if len(df) > 1:
                # 计算日收益率
                returns = df['close'].pct_change().dropna()

                # 年化波动率
                volatility = returns.std() * (365 ** 0.5)
                return volatility
            else:
                return 0.0

        except Exception as e:
            print(f"计算 {symbol} 波动率失败: {e}")
            return 0.0


class CryptoMarketData:
    """加密货币市场数据管理器"""

    # 支持的币种及其 Binance 交易对
    SUPPORTED_COINS = {
        'BTC': 'BTCUSDT',
        'ETH': 'ETHUSDT',
        'LTC': 'LTCUSDT',
        'ETC': 'ETCUSDT'
    }

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """初始化市场数据管理器"""
        self.fetcher = BinanceDataFetcher(api_key, api_secret)
        self.cache = {}
        self.last_update = None

    def get_all_prices(self) -> Dict[str, float]:
        """获取所有支持币种的当前价格"""
        symbols = list(self.SUPPORTED_COINS.values())
        prices_raw = self.fetcher.get_all_current_prices(symbols)

        # 转换为友好的币种名称
        prices = {}
        for coin, symbol in self.SUPPORTED_COINS.items():
            if symbol in prices_raw:
                prices[coin] = prices_raw[symbol]

        return prices

    def get_historical_data(self, coin: str, days_back: int = 180) -> pd.DataFrame:
        """
        获取指定币种的历史数据

        Args:
            coin: 币种符号 (BTC, ETH, LTC, ETC)
            days_back: 向前获取天数

        Returns:
            历史数据 DataFrame
        """
        if coin not in self.SUPPORTED_COINS:
            raise ValueError(f"不支持的币种: {coin}")

        symbol = self.SUPPORTED_COINS[coin]
        return self.fetcher.get_historical_klines(symbol, interval='1d', days_back=days_back)

    def get_all_historical_data(self, days_back: int = 180) -> Dict[str, pd.DataFrame]:
        """获取所有币种的历史数据"""
        data = {}
        for coin in self.SUPPORTED_COINS.keys():
            print(f"正在获取 {coin} 的历史数据...")
            data[coin] = self.get_historical_data(coin, days_back)
            time.sleep(0.2)  # 避免请求过快

        return data

    def get_market_summary(self) -> Dict[str, Dict]:
        """获取所有币种的市场概况"""
        symbols = list(self.SUPPORTED_COINS.values())
        summary_raw = self.fetcher.get_market_summary(symbols)

        # 转换为友好的币种名称
        summary = {}
        for coin, symbol in self.SUPPORTED_COINS.items():
            if symbol in summary_raw and summary_raw[symbol]:
                summary[coin] = summary_raw[symbol]

        return summary

    def refresh_cache(self, days_back: int = 180):
        """刷新缓存数据"""
        print("正在刷新市场数据缓存...")

        self.cache = {
            'prices': self.get_all_prices(),
            'historical_data': self.get_all_historical_data(days_back),
            'market_summary': self.get_market_summary()
        }

        self.last_update = datetime.now()
        print(f"缓存刷新完成，时间: {self.last_update}")

    def get_cached_data(self, max_age_minutes: int = 5) -> Optional[Dict]:
        """
        获取缓存数据（如果过期则自动刷新）

        Args:
            max_age_minutes: 缓存最大有效时间（分钟）

        Returns:
            缓存的市场数据
        """
        if not self.cache or not self.last_update:
            self.refresh_cache()
        else:
            age = (datetime.now() - self.last_update).total_seconds() / 60
            if age > max_age_minutes:
                self.refresh_cache()

        return self.cache


# 测试代码
if __name__ == '__main__':
    # 创建市场数据管理器
    market_data = CryptoMarketData()

    # 获取当前价格
    print("\n===== 当前价格 =====")
    prices = market_data.get_all_prices()
    for coin, price in prices.items():
        print(f"{coin}: ${price:,.2f}")

    # 获取市场概况
    print("\n===== 24小时市场概况 =====")
    summary = market_data.get_market_summary()
    for coin, data in summary.items():
        if data:
            print(f"\n{coin}:")
            print(f"  当前价格: ${data['current_price']:,.2f}")
            print(f"  24h涨跌: {data['price_change_pct_24h']:.2f}%")
            print(f"  24h最高: ${data['high_24h']:,.2f}")
            print(f"  24h最低: ${data['low_24h']:,.2f}")
            print(f"  24h成交量: {data['volume_24h']:,.2f}")

    # 获取历史数据示例
    print("\n===== 获取BTC历史数据 =====")
    btc_history = market_data.get_historical_data('BTC', days_back=30)
    print(f"获取到 {len(btc_history)} 条历史数据")
    print(btc_history.tail())
