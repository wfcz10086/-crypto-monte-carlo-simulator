"""
恐惧与贪婪指数分析模块
用于分析市场情绪并预测趋势
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np


class FearGreedAnalyzer:
    """恐惧与贪婪指数分析器"""

    # 情绪分类
    CLASSIFICATIONS = {
        'Extreme Fear': (0, 25),
        'Fear': (25, 45),
        'Neutral': (45, 55),
        'Greed': (55, 75),
        'Extreme Greed': (75, 100)
    }

    def __init__(self):
        """初始化分析器"""
        self.data = []
        self.current_index = None
        self.current_classification = None

    def load_data_from_dict(self, data_dict: Dict) -> None:
        """
        从字典加载数据

        Args:
            data_dict: 包含 'data' 键的字典，数据格式为 CSV 字符串
        """
        if 'data' in data_dict:
            # 解析 CSV 数据
            lines = data_dict['data']
            if isinstance(lines, str):
                lines = lines.strip().split('\n')

            # 跳过标题行
            records = []
            for line in lines[1:]:  # 跳过 "fng_value,fng_classification,date"
                parts = line.strip().split(',')
                if len(parts) == 3:
                    try:
                        date_str, value_str, classification = parts
                        # 解析日期 (格式: DD-MM-YYYY)
                        date = datetime.strptime(date_str, '%d-%m-%Y')
                        value = int(value_str)

                        records.append({
                            'date': date,
                            'value': value,
                            'classification': classification
                        })
                    except Exception as e:
                        print(f"解析行失败: {line}, 错误: {e}")

            # 转换为 DataFrame
            self.data = pd.DataFrame(records)
            self.data = self.data.sort_values('date', ascending=False)

            # 设置当前值
            if len(self.data) > 0:
                latest = self.data.iloc[0]
                self.current_index = latest['value']
                self.current_classification = latest['classification']

    def load_data_from_list(self, data_list: List[Dict]) -> None:
        """
        从列表加载数据

        Args:
            data_list: 数据列表，每个元素包含 date, value, classification
        """
        self.data = pd.DataFrame(data_list)
        self.data['date'] = pd.to_datetime(self.data['date'])
        self.data = self.data.sort_values('date', ascending=False)

        if len(self.data) > 0:
            latest = self.data.iloc[0]
            self.current_index = latest['value']
            self.current_classification = latest['classification']

    def get_current_index(self) -> Tuple[int, str]:
        """
        获取当前恐惧贪婪指数

        Returns:
            (指数值, 分类)
        """
        return self.current_index, self.current_classification

    def get_trend(self, days: int = 7) -> Dict:
        """
        分析最近趋势

        Args:
            days: 分析天数

        Returns:
            趋势分析结果
        """
        if len(self.data) < 2:
            return {'trend': 'insufficient_data'}

        # 获取最近N天的数据
        recent_data = self.data.head(min(days, len(self.data)))

        # 计算趋势
        values = recent_data['value'].values
        dates = recent_data['date'].values

        # 线性回归计算趋势
        if len(values) > 1:
            x = np.arange(len(values))
            z = np.polyfit(x, values, 1)
            trend_slope = z[0]

            # 判断趋势方向
            if trend_slope > 2:
                trend_direction = 'increasing'
                trend_strength = 'strong' if abs(trend_slope) > 5 else 'moderate'
            elif trend_slope < -2:
                trend_direction = 'decreasing'
                trend_strength = 'strong' if abs(trend_slope) > 5 else 'moderate'
            else:
                trend_direction = 'stable'
                trend_strength = 'weak'

            # 计算波动性
            volatility = np.std(values)

            return {
                'trend_direction': trend_direction,
                'trend_strength': trend_strength,
                'trend_slope': trend_slope,
                'volatility': volatility,
                'current_value': values[0],
                'avg_value': np.mean(values),
                'min_value': np.min(values),
                'max_value': np.max(values),
                'change': values[0] - values[-1],
                'change_pct': (values[0] - values[-1]) / values[-1] * 100 if values[-1] != 0 else 0
            }
        else:
            return {'trend': 'insufficient_data'}

    def predict_next_period(self, days_ahead: int = 30) -> Dict:
        """
        预测未来趋势

        Args:
            days_ahead: 预测天数

        Returns:
            预测结果
        """
        if len(self.data) < 7:
            return {'prediction': 'insufficient_data'}

        # 使用最近30天的数据进行预测
        recent_data = self.data.head(min(30, len(self.data)))
        values = recent_data['value'].values

        # 简单移动平均预测
        sma_7 = np.mean(values[:7]) if len(values) >= 7 else np.mean(values)
        sma_14 = np.mean(values[:14]) if len(values) >= 14 else sma_7

        # 趋势预测
        trend = self.get_trend(14)
        trend_slope = trend.get('trend_slope', 0)

        # 预测值（考虑均值回归）
        current_value = values[0]
        long_term_mean = np.mean(values)

        # 使用加权预测
        # 短期趋势 40%，长期均值回归 40%，当前值惯性 20%
        predicted_value = (
            0.4 * (current_value + trend_slope * days_ahead / 7) +
            0.4 * long_term_mean +
            0.2 * current_value
        )

        # 限制在 0-100 范围内
        predicted_value = max(0, min(100, predicted_value))

        # 预测分类
        predicted_classification = self._classify_value(predicted_value)

        # 置信度评估
        volatility = np.std(values)
        confidence = max(0, min(100, 100 - volatility * 2))

        return {
            'predicted_value': predicted_value,
            'predicted_classification': predicted_classification,
            'confidence': confidence,
            'current_value': current_value,
            'trend_direction': trend.get('trend_direction', 'unknown'),
            'days_ahead': days_ahead,
            'factors': {
                'short_term_trend': current_value + trend_slope * days_ahead / 7,
                'long_term_mean': long_term_mean,
                'volatility': volatility
            }
        }

    def _classify_value(self, value: float) -> str:
        """
        根据数值分类情绪

        Args:
            value: 指数值

        Returns:
            分类名称
        """
        for classification, (min_val, max_val) in self.CLASSIFICATIONS.items():
            if min_val <= value < max_val:
                return classification
        return 'Extreme Greed'  # 默认最高档

    def get_market_sentiment_score(self) -> Dict:
        """
        获取市场情绪评分（用于蒙特卡洛模拟）

        Returns:
            情绪评分和建议
        """
        if self.current_index is None:
            return {'score': 50, 'sentiment': 'neutral', 'recommendation': 'hold'}

        # 分析趋势
        trend = self.get_trend(7)

        # 综合评分
        score = self.current_index

        # 根据趋势调整
        if trend.get('trend_direction') == 'increasing':
            adjustment = 5 if trend.get('trend_strength') == 'strong' else 2
            score += adjustment
        elif trend.get('trend_direction') == 'decreasing':
            adjustment = 5 if trend.get('trend_strength') == 'strong' else 2
            score -= adjustment

        # 限制范围
        score = max(0, min(100, score))

        # 生成建议
        if score < 20:
            sentiment = 'extreme_fear'
            recommendation = 'consider_buying'  # 极度恐惧，可能是买入机会
            risk_level = 'high'
        elif score < 40:
            sentiment = 'fear'
            recommendation = 'accumulate'  # 恐惧，可以分批建仓
            risk_level = 'moderate_high'
        elif score < 60:
            sentiment = 'neutral'
            recommendation = 'hold'  # 中性，观望
            risk_level = 'moderate'
        elif score < 80:
            sentiment = 'greed'
            recommendation = 'take_profit'  # 贪婪，考虑获利
            risk_level = 'moderate_low'
        else:
            sentiment = 'extreme_greed'
            recommendation = 'sell'  # 极度贪婪，考虑减仓
            risk_level = 'low'

        return {
            'score': score,
            'raw_index': self.current_index,
            'sentiment': sentiment,
            'classification': self.current_classification,
            'recommendation': recommendation,
            'risk_level': risk_level,
            'trend': trend
        }

    def get_statistics(self) -> Dict:
        """获取历史统计信息"""
        if len(self.data) == 0:
            return {}

        values = self.data['value'].values

        return {
            'count': len(self.data),
            'mean': np.mean(values),
            'median': np.median(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values),
            'current': self.current_index,
            'date_range': {
                'start': self.data['date'].min().strftime('%Y-%m-%d'),
                'end': self.data['date'].max().strftime('%Y-%m-%d')
            },
            'classification_distribution': self.data['classification'].value_counts().to_dict()
        }


# 测试代码
if __name__ == '__main__':
    # 示例数据（用户提供的格式）
    sample_data = {
        "name": "Fear and Greed Index",
        "data": """fng_value,fng_classification,date
10-12-2025,26,Fear
09-12-2025,22,Extreme Fear
08-12-2025,20,Extreme Fear
07-12-2025,20,Extreme Fear
06-12-2025,23,Extreme Fear
05-12-2025,28,Fear
04-12-2025,26,Fear
03-12-2025,28,Fear
02-12-2025,23,Extreme Fear
01-12-2025,24,Extreme Fear""",
        "metadata": {
            "error": None
        }
    }

    # 创建分析器
    analyzer = FearGreedAnalyzer()
    analyzer.load_data_from_dict(sample_data)

    # 获取当前指数
    current_value, current_class = analyzer.get_current_index()
    print(f"\n当前恐惧贪婪指数: {current_value} ({current_class})")

    # 分析趋势
    print("\n===== 7日趋势分析 =====")
    trend = analyzer.get_trend(7)
    for key, value in trend.items():
        print(f"{key}: {value}")

    # 预测未来
    print("\n===== 30日预测 =====")
    prediction = analyzer.predict_next_period(30)
    for key, value in prediction.items():
        print(f"{key}: {value}")

    # 市场情绪评分
    print("\n===== 市场情绪评分 =====")
    sentiment = analyzer.get_market_sentiment_score()
    for key, value in sentiment.items():
        print(f"{key}: {value}")

    # 统计信息
    print("\n===== 历史统计 =====")
    stats = analyzer.get_statistics()
    for key, value in stats.items():
        print(f"{key}: {value}")
