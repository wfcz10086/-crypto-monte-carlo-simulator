"""
加密货币蒙特卡洛模拟引擎
考虑多个因素：历史波动率、恐惧贪婪指数、市场事件、降息等
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import pandas as pd


class MonteCarloSimulator:
    """蒙特卡洛模拟器 - 加密货币价格预测"""

    def __init__(self, symbol: str, current_price: float, historical_data: pd.DataFrame):
        """
        初始化模拟器

        Args:
            symbol: 币种符号 (BTC, ETH, LTC, ETC)
            current_price: 当前价格
            historical_data: 历史价格数据 (包含 'close', 'date' 列)
        """
        self.symbol = symbol
        self.current_price = current_price
        self.historical_data = historical_data

        # 计算历史统计数据
        self.calculate_historical_stats()

    def calculate_historical_stats(self):
        """计算历史波动率和趋势"""
        if len(self.historical_data) > 1:
            # 计算日收益率
            returns = self.historical_data['close'].pct_change().dropna()

            # 年化波动率
            self.volatility = returns.std() * np.sqrt(365)

            # 平均日收益率（年化）
            self.drift = returns.mean() * 365

            # 计算最近趋势
            recent_returns = returns.tail(30).mean() * 365
            self.recent_trend = recent_returns
        else:
            # 默认值（如果没有历史数据）
            self.volatility = 0.8  # 加密货币高波动率
            self.drift = 0.0
            self.recent_trend = 0.0

    def apply_fear_greed_adjustment(self, fear_greed_index: float) -> float:
        """
        根据恐惧贪婪指数调整漂移率

        Args:
            fear_greed_index: 恐惧贪婪指数 (0-100)

        Returns:
            调整后的漂移率
        """
        # 极度恐惧 (0-25): 负面影响，但可能触底反弹
        # 恐惧 (25-45): 轻微负面影响
        # 中性 (45-55): 无影响
        # 贪婪 (55-75): 正面影响
        # 极度贪婪 (75-100): 正面但可能过热

        if fear_greed_index < 25:  # 极度恐惧
            # 极度恐惧时，短期下跌但可能反弹
            adjustment = -0.15 + (25 - fear_greed_index) * 0.003  # 触底反弹因子
        elif fear_greed_index < 45:  # 恐惧
            adjustment = -0.05 - (45 - fear_greed_index) * 0.005
        elif fear_greed_index < 55:  # 中性
            adjustment = 0.0
        elif fear_greed_index < 75:  # 贪婪
            adjustment = (fear_greed_index - 55) * 0.004
        else:  # 极度贪婪
            # 极度贪婪时，可能回调
            adjustment = 0.08 - (fear_greed_index - 75) * 0.002

        return adjustment

    def apply_market_events(self, simulation_days: int) -> np.ndarray:
        """
        应用市场事件影响（如大瀑布、降息等）

        Args:
            simulation_days: 模拟天数

        Returns:
            每日事件影响因子数组
        """
        event_impacts = np.ones(simulation_days)

        # 10.11 大瀑布影响（190亿美金合约清算）
        # 假设当前是12月，距离大瀑布约2个月
        # 影响逐渐减弱，但市场仍在恢复期
        waterfall_recovery_days = min(60, simulation_days)
        for i in range(waterfall_recovery_days):
            # 恢复曲线：开始时负面影响大，逐渐恢复
            recovery_factor = 1 - 0.15 * np.exp(-i / 20)  # 指数恢复
            event_impacts[i] *= recovery_factor

        # 12月降息影响（通常在月中某日）
        # 假设降息在第15-20天发生
        if simulation_days >= 15:
            rate_cut_day = 17  # 假设第17天降息

            # 降息前的预期影响（提前反应）
            for i in range(max(0, rate_cut_day - 7), rate_cut_day):
                event_impacts[i] *= 1.02  # 轻微正面影响

            # 降息后的影响（更强的正面影响）
            for i in range(rate_cut_day, min(rate_cut_day + 30, simulation_days)):
                days_after = i - rate_cut_day
                # 降息后短期利好，然后逐渐消化
                boost = 1.08 * np.exp(-days_after / 15)
                event_impacts[i] *= boost

        # 季节性因素（年底通常波动大）
        for i in range(simulation_days):
            # 12月到1月，波动性增加
            if i < 60:  # 前两个月
                seasonal_factor = 1.0 + 0.05 * np.sin(i * np.pi / 60)
                event_impacts[i] *= seasonal_factor

        return event_impacts

    def simulate_price_path(
        self,
        days: int,
        fear_greed_index: float,
        num_simulations: int = 1000,
        include_jumps: bool = True
    ) -> Tuple[np.ndarray, Dict]:
        """
        执行蒙特卡洛模拟

        Args:
            days: 模拟天数
            fear_greed_index: 当前恐惧贪婪指数
            num_simulations: 模拟路径数量
            include_jumps: 是否包含跳跃扩散（极端事件）

        Returns:
            (价格路径矩阵, 统计信息字典)
        """
        dt = 1  # 时间步长（天）

        # 调整漂移率
        base_drift = self.drift
        fear_greed_adjustment = self.apply_fear_greed_adjustment(fear_greed_index)
        adjusted_drift = base_drift + fear_greed_adjustment

        # 获取市场事件影响
        event_impacts = self.apply_market_events(days)

        # 初始化价格矩阵
        prices = np.zeros((num_simulations, days + 1))
        prices[:, 0] = self.current_price

        # 跳跃扩散参数（模拟极端事件）
        jump_intensity = 0.05  # 平均每20天一次跳跃
        jump_mean = -0.02  # 跳跃平均幅度（略微负面）
        jump_std = 0.08  # 跳跃标准差

        # 执行模拟
        for i in range(num_simulations):
            for t in range(1, days + 1):
                # 几何布朗运动（GBM）
                random_shock = np.random.normal(0, 1)
                drift_component = adjusted_drift * dt
                diffusion_component = self.volatility * np.sqrt(dt) * random_shock

                # 应用市场事件影响
                event_factor = event_impacts[t - 1]

                # 计算价格变化
                price_change = drift_component + diffusion_component

                # 添加跳跃扩散（模拟突发事件）
                if include_jumps and np.random.random() < jump_intensity * dt:
                    jump_size = np.random.normal(jump_mean, jump_std)
                    price_change += jump_size

                # 更新价格（使用指数形式避免负价格）
                prices[i, t] = prices[i, t - 1] * np.exp(price_change) * event_factor

        # 计算统计信息
        final_prices = prices[:, -1]
        stats = {
            'mean': np.mean(final_prices),
            'median': np.median(final_prices),
            'std': np.std(final_prices),
            'min': np.min(final_prices),
            'max': np.max(final_prices),
            'percentile_5': np.percentile(final_prices, 5),
            'percentile_25': np.percentile(final_prices, 25),
            'percentile_75': np.percentile(final_prices, 75),
            'percentile_95': np.percentile(final_prices, 95),
            'probability_profit': np.sum(final_prices > self.current_price) / num_simulations,
            'expected_return': (np.mean(final_prices) - self.current_price) / self.current_price,
            'risk_adjusted_return': (np.mean(final_prices) - self.current_price) / np.std(final_prices) if np.std(final_prices) > 0 else 0
        }

        return prices, stats

    def calculate_portfolio_metrics(
        self,
        investment_amount: float,
        final_prices: np.ndarray
    ) -> Dict:
        """
        计算投资组合指标

        Args:
            investment_amount: 投资金额
            final_prices: 最终价格数组

        Returns:
            投资组合指标字典
        """
        # 计算持仓数量
        quantity = investment_amount / self.current_price

        # 计算最终价值
        final_values = quantity * final_prices

        # 计算收益
        profits = final_values - investment_amount

        metrics = {
            'initial_investment': investment_amount,
            'quantity': quantity,
            'expected_value': np.mean(final_values),
            'expected_profit': np.mean(profits),
            'expected_return_pct': np.mean(profits) / investment_amount * 100,
            'median_profit': np.median(profits),
            'best_case': np.max(profits),
            'worst_case': np.min(profits),
            'value_at_risk_95': np.percentile(profits, 5),  # 95% VaR
            'probability_loss': np.sum(profits < 0) / len(profits),
            'sharpe_ratio': np.mean(profits) / np.std(profits) if np.std(profits) > 0 else 0
        }

        return metrics


class MultiAssetSimulator:
    """多资产组合模拟器"""

    def __init__(self, assets: Dict[str, MonteCarloSimulator]):
        """
        初始化多资产模拟器

        Args:
            assets: 资产模拟器字典 {symbol: simulator}
        """
        self.assets = assets

    def simulate_portfolio(
        self,
        allocations: Dict[str, float],
        fear_greed_index: float,
        days: int = 90,
        num_simulations: int = 1000
    ) -> Dict:
        """
        模拟投资组合

        Args:
            allocations: 资金分配 {symbol: amount}
            fear_greed_index: 恐惧贪婪指数
            days: 模拟天数
            num_simulations: 模拟次数

        Returns:
            组合模拟结果
        """
        total_investment = sum(allocations.values())
        portfolio_values = np.zeros((num_simulations, days + 1))
        portfolio_values[:, 0] = total_investment

        # 为每个资产执行模拟
        asset_results = {}
        for symbol, allocation in allocations.items():
            if symbol in self.assets:
                simulator = self.assets[symbol]
                prices, stats = simulator.simulate_price_path(
                    days=days,
                    fear_greed_index=fear_greed_index,
                    num_simulations=num_simulations
                )

                # 计算该资产的价值变化
                quantity = allocation / simulator.current_price
                asset_values = prices * quantity

                asset_results[symbol] = {
                    'prices': prices,
                    'values': asset_values,
                    'stats': stats,
                    'allocation': allocation,
                    'weight': allocation / total_investment
                }

                # 累加到组合价值
                portfolio_values += asset_values

        # 计算组合统计
        final_values = portfolio_values[:, -1]
        profits = final_values - total_investment

        portfolio_stats = {
            'total_investment': total_investment,
            'expected_value': np.mean(final_values),
            'expected_profit': np.mean(profits),
            'expected_return_pct': np.mean(profits) / total_investment * 100,
            'median_value': np.median(final_values),
            'std_dev': np.std(final_values),
            'best_case': np.max(final_values),
            'worst_case': np.min(final_values),
            'probability_profit': np.sum(final_values > total_investment) / num_simulations,
            'value_at_risk_95': np.percentile(profits, 5),
            'sharpe_ratio': np.mean(profits) / np.std(profits) if np.std(profits) > 0 else 0
        }

        return {
            'portfolio_values': portfolio_values,
            'portfolio_stats': portfolio_stats,
            'asset_results': asset_results
        }
