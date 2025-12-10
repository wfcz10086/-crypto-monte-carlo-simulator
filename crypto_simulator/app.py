"""
加密货币蒙特卡洛模拟器 - Flask Web 应用
"""

from flask import Flask, render_template, request, jsonify
import json
import numpy as np
from datetime import datetime
import traceback

from binance_data import CryptoMarketData
from monte_carlo_engine import MonteCarloSimulator, MultiAssetSimulator
from fear_greed_index import FearGreedAnalyzer

app = Flask(__name__)

# 全局变量
market_data = None
fear_greed_analyzer = None


def initialize_data():
    """初始化数据"""
    global market_data, fear_greed_analyzer

    try:
        # 初始化市场数据
        print("正在初始化市场数据...")
        market_data = CryptoMarketData()

        # 初始化恐惧贪婪指数分析器
        print("正在初始化恐惧贪婪指数...")
        fear_greed_analyzer = FearGreedAnalyzer()

        # 加载示例数据（用户提供的）
        sample_fear_greed_data = {
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
            "metadata": {"error": None}
        }

        fear_greed_analyzer.load_data_from_dict(sample_fear_greed_data)

        print("数据初始化完成！")

    except Exception as e:
        print(f"数据初始化失败: {e}")
        traceback.print_exc()


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/market_data', methods=['GET'])
def get_market_data():
    """获取市场数据"""
    try:
        # 获取当前价格
        prices = market_data.get_all_prices()

        # 获取市场概况
        summary = market_data.get_market_summary()

        # 获取恐惧贪婪指数
        fng_value, fng_class = fear_greed_analyzer.get_current_index()
        fng_sentiment = fear_greed_analyzer.get_market_sentiment_score()

        return jsonify({
            'success': True,
            'prices': prices,
            'market_summary': summary,
            'fear_greed_index': {
                'value': fng_value,
                'classification': fng_class,
                'sentiment': fng_sentiment
            },
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/simulate', methods=['POST'])
def simulate():
    """执行蒙特卡洛模拟"""
    try:
        # 获取请求参数
        data = request.get_json()

        symbol = data.get('symbol', 'BTC')
        investment = float(data.get('investment', 10000))
        days = int(data.get('days', 90))
        num_simulations = int(data.get('num_simulations', 1000))

        print(f"开始模拟: {symbol}, 投资: ${investment}, 天数: {days}, 模拟次数: {num_simulations}")

        # 获取当前价格
        prices = market_data.get_all_prices()
        current_price = prices.get(symbol, 0)

        if current_price == 0:
            return jsonify({
                'success': False,
                'error': f'无法获取 {symbol} 的价格'
            }), 400

        # 获取历史数据
        historical_data = market_data.get_historical_data(symbol, days_back=180)

        if len(historical_data) == 0:
            return jsonify({
                'success': False,
                'error': f'无法获取 {symbol} 的历史数据'
            }), 400

        # 创建模拟器
        simulator = MonteCarloSimulator(
            symbol=symbol,
            current_price=current_price,
            historical_data=historical_data
        )

        # 获取恐惧贪婪指数
        fng_value, _ = fear_greed_analyzer.get_current_index()

        # 执行模拟
        price_paths, stats = simulator.simulate_price_path(
            days=days,
            fear_greed_index=fng_value,
            num_simulations=num_simulations
        )

        # 计算投资组合指标
        final_prices = price_paths[:, -1]
        portfolio_metrics = simulator.calculate_portfolio_metrics(
            investment_amount=investment,
            final_prices=final_prices
        )

        # 准备返回数据
        # 只返回部分路径用于可视化（避免数据量过大）
        sample_paths = price_paths[:min(100, num_simulations), :].tolist()

        # 计算每日统计（用于扇形图）
        daily_stats = []
        for day in range(days + 1):
            day_prices = price_paths[:, day]
            daily_stats.append({
                'day': day,
                'mean': float(np.mean(day_prices)),
                'median': float(np.median(day_prices)),
                'p5': float(np.percentile(day_prices, 5)),
                'p25': float(np.percentile(day_prices, 25)),
                'p75': float(np.percentile(day_prices, 75)),
                'p95': float(np.percentile(day_prices, 95))
            })

        # 价格分布（直方图数据）
        hist, bin_edges = np.histogram(final_prices, bins=50)
        price_distribution = {
            'bins': bin_edges.tolist(),
            'counts': hist.tolist()
        }

        return jsonify({
            'success': True,
            'simulation': {
                'symbol': symbol,
                'current_price': current_price,
                'investment': investment,
                'days': days,
                'num_simulations': num_simulations,
                'fear_greed_index': fng_value
            },
            'stats': {k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                     for k, v in stats.items()},
            'portfolio_metrics': {k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                                 for k, v in portfolio_metrics.items()},
            'sample_paths': sample_paths,
            'daily_stats': daily_stats,
            'price_distribution': price_distribution,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/simulate_portfolio', methods=['POST'])
def simulate_portfolio():
    """模拟投资组合"""
    try:
        # 获取请求参数
        data = request.get_json()

        allocations = data.get('allocations', {})  # {BTC: 5000, ETH: 3000, ...}
        days = int(data.get('days', 90))
        num_simulations = int(data.get('num_simulations', 1000))

        print(f"开始组合模拟: {allocations}, 天数: {days}, 模拟次数: {num_simulations}")

        # 获取所有价格和历史数据
        prices = market_data.get_all_prices()

        # 创建各个资产的模拟器
        simulators = {}
        for symbol in allocations.keys():
            if symbol in prices:
                current_price = prices[symbol]
                historical_data = market_data.get_historical_data(symbol, days_back=180)

                if len(historical_data) > 0:
                    simulators[symbol] = MonteCarloSimulator(
                        symbol=symbol,
                        current_price=current_price,
                        historical_data=historical_data
                    )

        if len(simulators) == 0:
            return jsonify({
                'success': False,
                'error': '无法创建任何资产的模拟器'
            }), 400

        # 创建多资产模拟器
        multi_simulator = MultiAssetSimulator(simulators)

        # 获取恐惧贪婪指数
        fng_value, _ = fear_greed_analyzer.get_current_index()

        # 执行组合模拟
        results = multi_simulator.simulate_portfolio(
            allocations=allocations,
            fear_greed_index=fng_value,
            days=days,
            num_simulations=num_simulations
        )

        # 准备返回数据
        portfolio_values = results['portfolio_values']
        portfolio_stats = results['portfolio_stats']
        asset_results = results['asset_results']

        # 只返回部分路径用于可视化
        sample_portfolio_paths = portfolio_values[:min(100, num_simulations), :].tolist()

        # 计算每日组合统计
        daily_portfolio_stats = []
        for day in range(days + 1):
            day_values = portfolio_values[:, day]
            daily_portfolio_stats.append({
                'day': day,
                'mean': float(np.mean(day_values)),
                'median': float(np.median(day_values)),
                'p5': float(np.percentile(day_values, 5)),
                'p25': float(np.percentile(day_values, 25)),
                'p75': float(np.percentile(day_values, 75)),
                'p95': float(np.percentile(day_values, 95))
            })

        # 各资产统计
        asset_stats = {}
        for symbol, asset_result in asset_results.items():
            asset_stats[symbol] = {
                'stats': {k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                         for k, v in asset_result['stats'].items()},
                'allocation': float(asset_result['allocation']),
                'weight': float(asset_result['weight'])
            }

        return jsonify({
            'success': True,
            'simulation': {
                'allocations': allocations,
                'days': days,
                'num_simulations': num_simulations,
                'fear_greed_index': fng_value
            },
            'portfolio_stats': {k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                               for k, v in portfolio_stats.items()},
            'asset_stats': asset_stats,
            'sample_paths': sample_portfolio_paths,
            'daily_stats': daily_portfolio_stats,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@app.route('/api/fear_greed_analysis', methods=['GET'])
def fear_greed_analysis():
    """获取恐惧贪婪指数详细分析"""
    try:
        # 当前指数
        current_value, current_class = fear_greed_analyzer.get_current_index()

        # 趋势分析
        trend_7d = fear_greed_analyzer.get_trend(7)
        trend_30d = fear_greed_analyzer.get_trend(30)

        # 预测
        prediction = fear_greed_analyzer.predict_next_period(30)

        # 市场情绪
        sentiment = fear_greed_analyzer.get_market_sentiment_score()

        # 统计信息
        statistics = fear_greed_analyzer.get_statistics()

        return jsonify({
            'success': True,
            'current': {
                'value': current_value,
                'classification': current_class
            },
            'trends': {
                '7_days': trend_7d,
                '30_days': trend_30d
            },
            'prediction': prediction,
            'sentiment': sentiment,
            'statistics': statistics,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


if __name__ == '__main__':
    # 初始化数据
    initialize_data()

    # 启动服务器
    print("\n" + "="*50)
    print("加密货币蒙特卡洛模拟器")
    print("="*50)
    print("\n服务器启动中...")
    print("访问地址: http://localhost:5000")
    print("\nCtrl+C 退出\n")

    app.run(host='0.0.0.0', port=5000, debug=True)
