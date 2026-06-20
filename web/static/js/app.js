/* 票多多 - 前端交互脚本 */

// 全局图表实例存储
const charts = {};

// 初始化 ECharts 图表
function initChart(containerId, option) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.warn(`Chart container #${containerId} not found`);
        return;
    }

    // 清除旧的图表实例
    if (charts[containerId]) {
        charts[containerId].dispose();
    }

    // 创建新图表
    const chart = echarts.init(container);
    chart.setOption(option);
    charts[containerId] = chart;

    // 响应式调整
    window.addEventListener('resize', () => {
        chart.resize();
    });

    return chart;
}

// 格式化价格
function formatPrice(price) {
    return '¥' + parseInt(price).toLocaleString();
}

// 格式化日期
function formatDate(dateStr) {
    if (!dateStr) return '';
    return dateStr.split('T')[0];
}

// 搜索表单提交处理
document.addEventListener('DOMContentLoaded', function() {
    console.log('🎫 票多多 页面加载完成');

    // 初始化页面上的图表
    initPageCharts();

    // 设置搜索表单 AJAX 提交
    setupAjaxSearch();

    // 设置导出功能
    setupExportButtons();
});

// 初始化页面图表（如果有数据）
function initPageCharts() {
    // 检查是否有图表数据容器
    const chartContainers = document.querySelectorAll('[data-chart-data]');
    chartContainers.forEach(container => {
        try {
            const chartData = JSON.parse(container.getAttribute('data-chart-data'));
            const chartType = container.getAttribute('data-chart-type');
            const chartId = container.getAttribute('id');
            initChart(chartId, chartData);
        } catch (e) {
            console.error('图表初始化失败:', e);
        }
    });
}

// 设置 AJAX 搜索
function setupAjaxSearch() {
    const searchForm = document.getElementById('searchForm');
    if (!searchForm) return;

    searchForm.addEventListener('submit', function(e) {
        // 对于简单的搜索，我们保持默认的表单提交行为
        // 这里可以扩展为 AJAX 搜索，添加加载动画
        const submitBtn = searchForm.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="loading-spinner" style="width:20px;height:20px;border-width:2px;"></span>';
        }
    });
}

// 设置导出按钮
function setupExportButtons() {
    const exportButtons = document.querySelectorAll('[data-export]');
    exportButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const format = this.getAttribute('data-export');
            const keyword = this.getAttribute('data-keyword') || '';
            const url = `/export/${format}?keyword=${encodeURIComponent(keyword)}`;
            window.location.href = url;
        });
    });
}

// 票价排序工具
function sortEvents(events, sortBy = 'price', ascending = true) {
    return [...events].sort((a, b) => {
        let valA, valB;

        switch (sortBy) {
            case 'price':
                valA = a.min_price || 0;
                valB = b.min_price || 0;
                break;
            case 'date':
                valA = new Date(a.date_str || 0).getTime();
                valB = new Date(b.date_str || 0).getTime();
                break;
            case 'city':
                valA = a.city || '';
                valB = b.city || '';
                return ascending ? valA.localeCompare(valB) : valB.localeCompare(valA);
            default:
                valA = a.title || '';
                valB = b.title || '';
                return ascending ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }

        return ascending ? valA - valB : valB - valA;
    });
}

// 票价对比分析
function analyzePrices(events) {
    if (!events || events.length === 0) {
        return { error: '无数据' };
    }

    // 按平台分组统计
    const platformStats = {};
    let allPrices = [];

    events.forEach(event => {
        if (event.tickets) {
            event.tickets.forEach(ticket => {
                const platform = ticket.platform || '未知';
                if (!platformStats[platform]) {
                    platformStats[platform] = {
                        count: 0,
                        prices: [],
                        avgPrice: 0,
                        minPrice: Infinity,
                        maxPrice: -Infinity
                    };
                }

                platformStats[platform].count++;
                platformStats[platform].prices.push(ticket.price);
                allPrices.push(ticket.price);
            });
        }
    });

    // 计算各平台统计
    Object.keys(platformStats).forEach(platform => {
        const stats = platformStats[platform];
        stats.avgPrice = stats.prices.reduce((a, b) => a + b, 0) / stats.prices.length;
        stats.minPrice = Math.min(...stats.prices);
        stats.maxPrice = Math.max(...stats.prices);
    });

    // 总体统计
    const overall = {
        avgPrice: allPrices.reduce((a, b) => a + b, 0) / allPrices.length,
        minPrice: Math.min(...allPrices),
        maxPrice: Math.max(...allPrices),
        totalTickets: allPrices.length
    };

    return {
        platforms: platformStats,
        overall: overall
    };
}

// 生成推荐文字
function generateRecommendation(event) {
    if (!event.tickets || event.tickets.length === 0) {
        return '暂无票价信息';
    }

    const available = event.tickets.filter(t => !t.ticket_status || !t.ticket_status.includes('售罄'));
    if (available.length === 0) {
        return '⚠️ 所有票档均已售罄';
    }

    const minPrice = Math.min(...available.map(t => t.price));
    const platforms = [...new Set(available.map(t => t.platform))];

    return `💰 最低 ¥${minPrice}，${platforms.join(' / ')} 可购`;
}

// 平滑滚动
function smoothScrollTo(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
    }
}

// 复制到剪贴板
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showToast('已复制到剪贴板');
    }).catch(err => {
        console.error('复制失败:', err);
        showToast('复制失败');
    });
}

// 显示提示信息
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed-top mx-auto mt-3 alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'}`;
    toast.style.width = 'fit-content';
    toast.style.zIndex = '9999';
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// 页面加载后自动初始化图表（当页面内嵌 chartData 变量时）
window.addEventListener('load', function() {
    // 检查是否有内联的图表数据
    if (typeof window.chartData !== 'undefined') {
        Object.keys(window.chartData).forEach(chartId => {
            initChart(chartId, window.chartData[chartId]);
        });
    }
});
