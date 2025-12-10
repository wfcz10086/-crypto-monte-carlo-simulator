// 加密货币蒙特卡洛模拟器 - 前端交互

// 全局变量
let pricePathChart = null;
let priceDistChart = null;
let profitDistChart = null;
let confidenceChart = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成，初始化...');

    // 加载市场数据
    loadMarketData();

    // 绑定表单提交事件
    document.getElementById('singleSimForm').addEventListener('submit', handleSingleSimulation);
    document.getElementById('portfolioSimForm').addEventListener('submit', handlePortfolioSimulation);

    // 监听资金分配变化
    const allocInputs = ['alloc_btc', 'alloc_eth', 'alloc_ltc', 'alloc_etc'];
    allocInputs.forEach(id => {
        document.getElementById(id).addEventListener('input', updateTotalAllocation);
    });
});

// 切换标签页
function switchTab(tabName) {
    // 隐藏所有标签内容
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // 移除所有按钮的激活状态
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // 显示选中的标签
    if (tabName === 'single') {
        document.getElementById('singleAssetTab').classList.add('active');
        event.target.classList.add('active');
    } else if (tabName === 'portfolio') {
        document.getElementById('portfolioTab').classList.add('active');
        event.target.classList.add('active');
    }
}

// 更新总投资金额
function updateTotalAllocation() {
    const btc = parseFloat(document.getElementById('alloc_btc').value) || 0;
    const eth = parseFloat(document.getElementById('alloc_eth').value) || 0;
    const ltc = parseFloat(document.getElementById('alloc_ltc').value) || 0;
    const etc = parseFloat(document.getElementById('alloc_etc').value) || 0;

    const total = btc + eth + ltc + etc;
    document.getElementById('totalAllocation').textContent = total.toLocaleString();
}

// 加载市场数据
async function loadMarketData() {
    try {
        const response = await axios.get('/api/market_data');
        const data = response.data;

        if (data.success) {
            // 更新价格卡片
            updateMarketCards(data.prices, data.market_summary);

            // 更新恐惧贪婪指数
            updateFearGreedIndex(data.fear_greed_index);
        } else {
            console.error('加载市场数据失败:', data.error);
        }
    } catch (error) {
        console.error('请求市场数据失败:', error);
        // 如果API请求失败，使用模拟数据
        useMockMarketData();
    }
}

// 使用模拟数据（API不可用时）
function useMockMarketData() {
    const mockPrices = {
        'BTC': 43250.50,
        'ETH': 2280.75,
        'LTC': 72.30,
        'ETC': 20.15
    };

    const mockSummary = {
        'BTC': { price_change_pct_24h: 2.5 },
        'ETH': { price_change_pct_24h: -1.2 },
        'LTC': { price_change_pct_24h: 0.8 },
        'ETC': { price_change_pct_24h: -0.5 }
    };

    updateMarketCards(mockPrices, mockSummary);

    const mockFearGreed = {
        value: 26,
        classification: 'Fear',
        sentiment: { score: 26, recommendation: 'consider_buying' }
    };

    updateFearGreedIndex(mockFearGreed);
}

// 更新市场卡片
function updateMarketCards(prices, summary) {
    const coins = ['BTC', 'ETH', 'LTC', 'ETC'];
    const cards = document.querySelectorAll('.market-card');

    cards.forEach((card, index) => {
        const coin = coins[index];
        const price = prices[coin];
        const coinSummary = summary[coin];

        card.classList.remove('loading');

        const priceElement = card.querySelector('.card-price');
        const changeElement = card.querySelector('.card-change');

        priceElement.textContent = `$${price.toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        })}`;

        if (coinSummary) {
            const change = coinSummary.price_change_pct_24h;
            changeElement.textContent = `${change > 0 ? '+' : ''}${change.toFixed(2)}% (24h)`;
            changeElement.className = `card-change ${change > 0 ? 'positive' : 'negative'}`;
        }
    });
}

// 更新恐惧贪婪指数
function updateFearGreedIndex(fngData) {
    const value = fngData.value;
    const classification = fngData.classification;

    document.getElementById('fngValue').textContent = value;
    document.getElementById('fngLabel').textContent = classification;

    // 更新指示器位置
    const gaugeBar = document.getElementById('gaugeBar');
    gaugeBar.style.left = `${value}%`;
}

// 处理单一资产模拟
async function handleSingleSimulation(event) {
    event.preventDefault();

    const symbol = document.getElementById('symbol').value;
    const investment = parseFloat(document.getElementById('investment').value);
    const days = parseInt(document.getElementById('days').value);
    const numSims = parseInt(document.getElementById('numSims').value);

    // 显示加载指示器
    showLoading();
    hideResults();

    try {
        const response = await axios.post('/api/simulate', {
            symbol,
            investment,
            days,
            num_simulations: numSims
        });

        const data = response.data;

        if (data.success) {
            // 显示结果
            displayResults(data, 'single');
        } else {
            alert('模拟失败: ' + data.error);
        }
    } catch (error) {
        console.error('模拟请求失败:', error);
        alert('模拟请求失败，请检查后端服务是否运行');
    } finally {
        hideLoading();
    }
}

// 处理投资组合模拟
async function handlePortfolioSimulation(event) {
    event.preventDefault();

    const allocations = {
        'BTC': parseFloat(document.getElementById('alloc_btc').value) || 0,
        'ETH': parseFloat(document.getElementById('alloc_eth').value) || 0,
        'LTC': parseFloat(document.getElementById('alloc_ltc').value) || 0,
        'ETC': parseFloat(document.getElementById('alloc_etc').value) || 0
    };

    // 过滤掉0分配
    Object.keys(allocations).forEach(key => {
        if (allocations[key] === 0) {
            delete allocations[key];
        }
    });

    const days = parseInt(document.getElementById('portfolioDays').value);
    const numSims = parseInt(document.getElementById('portfolioSims').value);

    // 显示加载指示器
    showLoading();
    hideResults();

    try {
        const response = await axios.post('/api/simulate_portfolio', {
            allocations,
            days,
            num_simulations: numSims
        });

        const data = response.data;

        if (data.success) {
            // 显示结果
            displayResults(data, 'portfolio');
        } else {
            alert('组合模拟失败: ' + data.error);
        }
    } catch (error) {
        console.error('组合模拟请求失败:', error);
        alert('组合模拟请求失败，请检查后端服务是否运行');
    } finally {
        hideLoading();
    }
}

// 显示加载指示器
function showLoading() {
    document.getElementById('loadingIndicator').style.display = 'block';
}

// 隐藏加载指示器
function hideLoading() {
    document.getElementById('loadingIndicator').style.display = 'none';
}

// 隐藏结果区域
function hideResults() {
    document.getElementById('resultsSection').style.display = 'none';
}

// 显示结果
function displayResults(data, type) {
    const resultsSection = document.getElementById('resultsSection');
    resultsSection.style.display = 'block';

    if (type === 'single') {
        displaySingleAssetResults(data);
    } else {
        displayPortfolioResults(data);
    }

    // 滚动到结果区域
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// 显示单一资产结果
function displaySingleAssetResults(data) {
    const { simulation, stats, portfolio_metrics, sample_paths, daily_stats, price_distribution } = data;

    // 显示关键指标
    displayKeyMetrics(portfolio_metrics, simulation);

    // 绘制图表
    drawPricePathChart(sample_paths, simulation.symbol, simulation.current_price);
    drawPriceDistributionChart(price_distribution, simulation.symbol);
    drawProfitDistributionChart(portfolio_metrics, simulation.investment);
    drawConfidenceChart(daily_stats, simulation.symbol);

    // 显示详细统计
    displayDetailedStats(stats, portfolio_metrics);
}

// 显示投资组合结果
function displayPortfolioResults(data) {
    const { simulation, portfolio_stats, asset_stats, sample_paths, daily_stats } = data;

    // 显示关键指标
    displayPortfolioKeyMetrics(portfolio_stats, simulation);

    // 绘制图表
    drawPortfolioPaths(sample_paths, portfolio_stats.total_investment);
    drawPortfolioDistribution(sample_paths, portfolio_stats);
    drawAssetAllocation(asset_stats);
    drawPortfolioConfidence(daily_stats);

    // 显示详细统计
    displayPortfolioDetailedStats(portfolio_stats, asset_stats);
}

// 显示关键指标
function displayKeyMetrics(metrics, simulation) {
    const metricsHtml = `
        <div class="metric-card">
            <h4>初始投资</h4>
            <div class="value">$${metrics.initial_investment.toLocaleString()}</div>
        </div>
        <div class="metric-card">
            <h4>预期价值</h4>
            <div class="value">$${metrics.expected_value.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
            <div class="subtext">${simulation.days}天后</div>
        </div>
        <div class="metric-card">
            <h4>预期收益</h4>
            <div class="value ${metrics.expected_profit >= 0 ? 'positive' : 'negative'}">
                $${metrics.expected_profit.toLocaleString(undefined, {maximumFractionDigits: 0})}
            </div>
            <div class="subtext">${metrics.expected_return_pct >= 0 ? '+' : ''}${metrics.expected_return_pct.toFixed(2)}%</div>
        </div>
        <div class="metric-card">
            <h4>盈利概率</h4>
            <div class="value">${(metrics.probability_loss !== undefined ? (1 - metrics.probability_loss) * 100 : 0).toFixed(1)}%</div>
        </div>
        <div class="metric-card">
            <h4>最佳情况</h4>
            <div class="value positive">$${metrics.best_case.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
        </div>
        <div class="metric-card">
            <h4>最坏情况</h4>
            <div class="value negative">$${metrics.worst_case.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
        </div>
    `;

    document.getElementById('keyMetrics').innerHTML = metricsHtml;
}

// 显示投资组合关键指标
function displayPortfolioKeyMetrics(stats, simulation) {
    const expectedProfit = stats.expected_value - stats.total_investment;
    const expectedReturnPct = (expectedProfit / stats.total_investment) * 100;

    const metricsHtml = `
        <div class="metric-card">
            <h4>总投资</h4>
            <div class="value">$${stats.total_investment.toLocaleString()}</div>
        </div>
        <div class="metric-card">
            <h4>预期价值</h4>
            <div class="value">$${stats.expected_value.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
            <div class="subtext">${simulation.days}天后</div>
        </div>
        <div class="metric-card">
            <h4>预期收益</h4>
            <div class="value ${expectedProfit >= 0 ? 'positive' : 'negative'}">
                $${expectedProfit.toLocaleString(undefined, {maximumFractionDigits: 0})}
            </div>
            <div class="subtext">${expectedReturnPct >= 0 ? '+' : ''}${expectedReturnPct.toFixed(2)}%</div>
        </div>
        <div class="metric-card">
            <h4>盈利概率</h4>
            <div class="value">${(stats.probability_profit * 100).toFixed(1)}%</div>
        </div>
        <div class="metric-card">
            <h4>最佳情况</h4>
            <div class="value positive">$${stats.best_case.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
        </div>
        <div class="metric-card">
            <h4>最坏情况</h4>
            <div class="value negative">$${stats.worst_case.toLocaleString(undefined, {maximumFractionDigits: 0})}</div>
        </div>
    `;

    document.getElementById('keyMetrics').innerHTML = metricsHtml;
}

// 绘制价格路径图
function drawPricePathChart(paths, symbol, currentPrice) {
    const ctx = document.getElementById('pricePathChart').getContext('2d');

    if (pricePathChart) {
        pricePathChart.destroy();
    }

    // 准备数据
    const days = paths[0].length;
    const labels = Array.from({length: days}, (_, i) => i);

    const datasets = paths.slice(0, 50).map((path, i) => ({
        label: `路径 ${i + 1}`,
        data: path,
        borderColor: `rgba(102, 126, 234, ${0.1 + (i / paths.length) * 0.3})`,
        borderWidth: 1,
        fill: false,
        pointRadius: 0,
        tension: 0.1
    }));

    // 添加当前价格线
    datasets.push({
        label: '当前价格',
        data: Array(days).fill(currentPrice),
        borderColor: 'red',
        borderWidth: 2,
        borderDash: [5, 5],
        fill: false,
        pointRadius: 0
    });

    pricePathChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: false
                },
                title: {
                    display: true,
                    text: `${symbol} 价格模拟路径 (50条样本)`
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '天数'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '价格 (USD)'
                    }
                }
            }
        }
    });
}

// 绘制价格分布图
function drawPriceDistributionChart(distribution, symbol) {
    const ctx = document.getElementById('priceDistChart').getContext('2d');

    if (priceDistChart) {
        priceDistChart.destroy();
    }

    const bins = distribution.bins;
    const counts = distribution.counts;

    // 创建标签（区间中点）
    const labels = bins.slice(0, -1).map((bin, i) => {
        const mid = (bin + bins[i + 1]) / 2;
        return mid.toFixed(0);
    });

    priceDistChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '模拟次数',
                data: counts,
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                title: {
                    display: true,
                    text: `${symbol} 最终价格分布`
                },
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '价格 (USD)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '频次'
                    }
                }
            }
        }
    });
}

// 绘制收益分布图
function drawProfitDistributionChart(metrics, investment) {
    const ctx = document.getElementById('profitDistChart').getContext('2d');

    if (profitDistChart) {
        profitDistChart.destroy();
    }

    // 创建收益区间
    const worstCase = metrics.worst_case;
    const bestCase = metrics.best_case;
    const range = bestCase - worstCase;
    const numBins = 30;
    const binSize = range / numBins;

    const labels = [];
    const data = [];

    // 简化：使用正态分布近似
    const mean = metrics.expected_profit;
    const std = (bestCase - worstCase) / 6;  // 假设6个标准差范围

    for (let i = 0; i < numBins; i++) {
        const binStart = worstCase + i * binSize;
        const binMid = binStart + binSize / 2;
        labels.push(binMid.toFixed(0));

        // 正态分布密度
        const density = Math.exp(-0.5 * Math.pow((binMid - mean) / std, 2)) / (std * Math.sqrt(2 * Math.PI));
        data.push(density * 1000);  // 缩放以便可视化
    }

    profitDistChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '概率密度',
                data: data,
                backgroundColor: labels.map(l => parseFloat(l) >= 0 ? 'rgba(34, 197, 94, 0.6)' : 'rgba(239, 68, 68, 0.6)'),
                borderColor: labels.map(l => parseFloat(l) >= 0 ? 'rgba(34, 197, 94, 1)' : 'rgba(239, 68, 68, 1)'),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                title: {
                    display: true,
                    text: '投资收益分布'
                },
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '收益 (USD)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '概率密度'
                    }
                }
            }
        }
    });
}

// 绘制置信区间图
function drawConfidenceChart(dailyStats, symbol) {
    const ctx = document.getElementById('confidenceChart').getContext('2d');

    if (confidenceChart) {
        confidenceChart.destroy();
    }

    const days = dailyStats.map(s => s.day);
    const mean = dailyStats.map(s => s.mean);
    const p5 = dailyStats.map(s => s.p5);
    const p25 = dailyStats.map(s => s.p25);
    const p75 = dailyStats.map(s => s.p75);
    const p95 = dailyStats.map(s => s.p95);

    confidenceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: days,
            datasets: [
                {
                    label: '95% 置信区间上限',
                    data: p95,
                    borderColor: 'rgba(102, 126, 234, 0.3)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: '+1',
                    borderWidth: 1,
                    pointRadius: 0
                },
                {
                    label: '75% 置信区间上限',
                    data: p75,
                    borderColor: 'rgba(102, 126, 234, 0.5)',
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    fill: '+1',
                    borderWidth: 1,
                    pointRadius: 0
                },
                {
                    label: '平均值',
                    data: mean,
                    borderColor: 'rgba(102, 126, 234, 1)',
                    borderWidth: 2,
                    fill: false,
                    pointRadius: 0
                },
                {
                    label: '25% 置信区间下限',
                    data: p25,
                    borderColor: 'rgba(102, 126, 234, 0.5)',
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    fill: '-1',
                    borderWidth: 1,
                    pointRadius: 0
                },
                {
                    label: '5% 置信区间下限',
                    data: p5,
                    borderColor: 'rgba(102, 126, 234, 0.3)',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: false,
                    borderWidth: 1,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                title: {
                    display: true,
                    text: `${symbol} 价格置信区间`
                },
                legend: {
                    display: true,
                    position: 'bottom'
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '天数'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '价格 (USD)'
                    }
                }
            }
        }
    });
}

// 绘制投资组合路径
function drawPortfolioPaths(paths, initialValue) {
    drawPricePathChart(paths, '投资组合', initialValue);
}

// 绘制投资组合分布
function drawPortfolioDistribution(paths, stats) {
    const ctx = document.getElementById('priceDistChart').getContext('2d');

    if (priceDistChart) {
        priceDistChart.destroy();
    }

    // 获取最终值
    const finalValues = paths.map(path => path[path[0].length - 1]);

    // 创建直方图
    const min = Math.min(...finalValues);
    const max = Math.max(...finalValues);
    const numBins = 30;
    const binSize = (max - min) / numBins;

    const bins = [];
    const counts = Array(numBins).fill(0);

    for (let i = 0; i <= numBins; i++) {
        bins.push(min + i * binSize);
    }

    finalValues.forEach(value => {
        const binIndex = Math.min(Math.floor((value - min) / binSize), numBins - 1);
        counts[binIndex]++;
    });

    const labels = bins.slice(0, -1).map((bin, i) => {
        const mid = (bin + bins[i + 1]) / 2;
        return mid.toFixed(0);
    });

    priceDistChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '模拟次数',
                data: counts,
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                title: {
                    display: true,
                    text: '投资组合最终价值分布'
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: '组合价值 (USD)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: '频次'
                    }
                }
            }
        }
    });
}

// 绘制资产分配
function drawAssetAllocation(assetStats) {
    const ctx = document.getElementById('profitDistChart').getContext('2d');

    if (profitDistChart) {
        profitDistChart.destroy();
    }

    const labels = Object.keys(assetStats);
    const data = labels.map(symbol => assetStats[symbol].allocation);
    const colors = [
        'rgba(255, 99, 132, 0.6)',
        'rgba(54, 162, 235, 0.6)',
        'rgba(255, 206, 86, 0.6)',
        'rgba(75, 192, 192, 0.6)'
    ];

    profitDistChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: colors.map(c => c.replace('0.6', '1')),
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                title: {
                    display: true,
                    text: '资产分配'
                },
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// 绘制投资组合置信区间
function drawPortfolioConfidence(dailyStats) {
    drawConfidenceChart(dailyStats, '投资组合');
}

// 显示详细统计
function displayDetailedStats(stats, metrics) {
    const statsHtml = `
        <h3>详细统计数据</h3>
        <div class="stat-grid">
            <div class="stat-item">
                <span class="label">平均最终价格:</span>
                <span class="value">$${stats.mean.toLocaleString(undefined, {maximumFractionDigits: 2})}</span>
            </div>
            <div class="stat-item">
                <span class="label">中位数价格:</span>
                <span class="value">$${stats.median.toLocaleString(undefined, {maximumFractionDigits: 2})}</span>
            </div>
            <div class="stat-item">
                <span class="label">标准差:</span>
                <span class="value">$${stats.std.toLocaleString(undefined, {maximumFractionDigits: 2})}</span>
            </div>
            <div class="stat-item">
                <span class="label">5%分位数:</span>
                <span class="value">$${stats.percentile_5.toLocaleString(undefined, {maximumFractionDigits: 2})}</span>
            </div>
            <div class="stat-item">
                <span class="label">95%分位数:</span>
                <span class="value">$${stats.percentile_95.toLocaleString(undefined, {maximumFractionDigits: 2})}</span>
            </div>
            <div class="stat-item">
                <span class="label">风险调整后收益:</span>
                <span class="value">${metrics.sharpe_ratio.toFixed(4)}</span>
            </div>
        </div>
    `;

    document.getElementById('detailedStats').innerHTML = statsHtml;
}

// 显示投资组合详细统计
function displayPortfolioDetailedStats(portfolioStats, assetStats) {
    let statsHtml = `
        <h3>投资组合详细统计</h3>
        <div class="stat-grid">
            <div class="stat-item">
                <span class="label">预期收益率:</span>
                <span class="value">${portfolioStats.expected_return_pct.toFixed(2)}%</span>
            </div>
            <div class="stat-item">
                <span class="label">中位数价值:</span>
                <span class="value">$${portfolioStats.median_value.toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
            </div>
            <div class="stat-item">
                <span class="label">标准差:</span>
                <span class="value">$${portfolioStats.std_dev.toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
            </div>
            <div class="stat-item">
                <span class="label">VaR (95%):</span>
                <span class="value">$${portfolioStats.value_at_risk_95.toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
            </div>
            <div class="stat-item">
                <span class="label">夏普比率:</span>
                <span class="value">${portfolioStats.sharpe_ratio.toFixed(4)}</span>
            </div>
        </div>

        <h3 style="margin-top: 30px;">各资产表现</h3>
        <div class="stat-grid">
    `;

    for (const [symbol, assetData] of Object.entries(assetStats)) {
        const stats = assetData.stats;
        statsHtml += `
            <div class="stat-item">
                <span class="label">${symbol} 预期收益率:</span>
                <span class="value">${(stats.expected_return * 100).toFixed(2)}%</span>
            </div>
            <div class="stat-item">
                <span class="label">${symbol} 权重:</span>
                <span class="value">${(assetData.weight * 100).toFixed(1)}%</span>
            </div>
        `;
    }

    statsHtml += `</div>`;

    document.getElementById('detailedStats').innerHTML = statsHtml;
}

console.log('应用初始化完成');
