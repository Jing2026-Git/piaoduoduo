"""
数据可视化模块 - 为网页生成图表数据
输出格式适配 ECharts (前端图表库使用的格式
"""

from typing import List, Dict
from collections import defaultdict
from datetime import datetime


class Visualizer:
    """数据可视化生成器"""

    def __init__(self):
        self.colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272']

    def make_price_bar_chart(self, events: List) -> Dict:
        """
        生成票价柱状图数据 - 各演出最低价对比
        """
        # 按演出分组，取每个演出的最低票价
        event_prices = []

        # 取前8个演出
        for event in events[:8]:
            if event.tickets:
                available = [t for t in event.tickets if "售罄" not in t.ticket_status]
                tickets_to_use = available if available else event.tickets
                if tickets_to_use:
                    min_price = min(t.price for t in tickets_to_use)
                    event_prices.append({
                        'title': event.title[:15] + ('...' if len(event.title) > 15 else ''),
                        'price': int(min_price),
                        'city': event.city,
                        'venue': event.venue
                    })

        # 按价格排序
        event_prices.sort(key=lambda x: x['price'])

        # 生成 ECharts 配置
        chart = {
            'title': {'text': '演出最低票价对比', 'left': 'center'},
            'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
            'grid': {'left': '3%', 'right': '4%', 'bottom': '15%', 'containLabel': True},
            'xAxis': {
                'type': 'category',
                'data': [e['title'] for e in event_prices],
                'axisLabel': {'interval': 0, 'rotate': 30}
            },
            'yAxis': {'type': 'value', 'name': '票价 (¥'},
            'series': [{
                'name': '最低票价',
                'type': 'bar',
                'data': [e['price'] for e in event_prices],
                'itemStyle': {'color': '#5470c6'},
                'label': {
                    'show': True,
                    'position': 'top',
                    'formatter': '¥{c}'
                }
            }]
        }
        return chart

    def make_platform_pie_chart(self, events: List) -> Dict:
        """
        生成各平台票价比饼图 - 各平台均价对比
        """
        platform_prices = defaultdict(list)

        for event in events:
            for ticket in event.tickets:
                if ticket.platform:
                    platform_prices[ticket.platform].append(ticket.price)

        # 计算每个平台的平均价格
        pie_data = []
        for platform, prices in platform_prices.items():
            if prices:
                pie_data.append({
                    'name': platform,
                    'value': int(sum(prices) / len(prices))
                })

        # 生成 ECharts 配置
        chart = {
            'title': {'text': '各平台平均票价对比', 'left': 'center'},
            'tooltip': {'trigger': 'item', 'formatter': '{b}: ¥{c} ({d}%)'},
            'legend': {'orient': 'vertical', 'left': 'left'},
            'series': [{
                'name': '均价',
                'type': 'pie',
                'radius': ['40%', '70%'],
                'data': pie_data,
                'emphasis': {
                    'itemStyle': {
                        'shadowBlur': 10,
                        'shadowOffsetX': 0,
                        'shadowColor': 'rgba(0, 0, 0, 0.5)'
                    }
                }
            }]
        }
        return chart

    def make_price_scatter_chart(self, events: List) -> Dict:
        """
        生成票价散点图 - 展示所有票档的价格分布
        """
        scatter_data = []

        for idx, event in enumerate(events[:10]):
            for ticket in event.tickets:
                scatter_data.append({
                    'name': event.title[:12] + '...',
                    'value': [idx, int(ticket.price)],
                    'platform': ticket.platform
                })

        chart = {
            'title': {'text': '票价分布', 'left': 'center'},
            'tooltip': {
                'trigger': 'item',
                'formatter': '{@[2]}<br/>票价: ¥{@[1]}'
            },
            'xAxis': {
                'type': 'category',
                'data': [e.title[:8] for e in events[:10]],
                'axisLabel': {'rotate': 30}
            },
            'yAxis': {'type': 'value', 'name': '票价 (¥)'},
            'series': [{
                'type': 'scatter',
                'symbolSize': 15,
                'data': scatter_data,
                'itemStyle': {'color': '#ee6666'}
            }]
        }
        return chart

    def make_price_range_chart(self, events: List) -> Dict:
        """
        生成票价范围图 - 展示每个演出的票价范围(最低价-最高价
        """
        range_data = []
        categories = []

        for idx, event in enumerate(events[:8]):
            if event.tickets:
                prices = [t.price for t in event.tickets]
                categories.append(event.title[:15])
                range_data.append([min(prices), max(prices)])

        chart = {
            'title': {'text': '各演出票价范围', 'left': 'center'},
            'tooltip': {'trigger': 'axis', 'formatter': '{b}<br/>最低价: ¥{c}'},
            'xAxis': {
                'type': 'category',
                'data': categories,
                'axisLabel': {'rotate': 30}
            },
            'yAxis': {'type': 'value', 'name': '票价 (¥)'},
            'series': [{
                'type': 'bar',
                'data': range_data,
                'itemStyle': {'color': '#91cc75'}
            }]
        }
        return chart

    def make_city_distribution_chart(self, events: List) -> Dict:
        """
        生成城市分布图 - 各城市演出数量
        """
        city_count = defaultdict(int)
        for event in events:
            if event.city:
                city_count[event.city] += 1

        city_data = sorted(city_count.items(), key=lambda x: x[1], reverse=True)[:10]

        chart = {
            'title': {'text': '各城市演出场次分布', 'left': 'center'},
            'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}},
            'grid': {'left': '3%', 'right': '4%', 'bottom': '3%', 'containLabel': True},
            'xAxis': {
                'type': 'value', 'name': '场次'},
            'yAxis': {
                'type': 'category',
                'data': [c[0] for c in city_data]
            },
            'series': [{
                'name': '场次',
                'type': 'bar',
                'data': [c[1] for c in city_data],
                'itemStyle': {'color': '#73c0de'},
                'label': {'show': True, 'position': 'right'}
            }]
        }
        return chart

    def make_trend_line_chart(self, price_history: List) -> Dict:
        """
        生成价格趋势折线图 - 展示价格随时间变化
        """
        from collections import defaultdict as dd

        # 按平台和座次分组
        platform_data = dd(list)
        for record in price_history:
            key = f"{record.platform} - {record.seat_type}"
            platform_data[key].append({
                'time': record.record_time.strftime('%Y-%m-%d') if hasattr(record, 'record_time') else '',
                'price': record.price
            })

        # 生成 ECharts 配置
        series = []
        all_times = set()

        for key, records in platform_data.items():
            times = [r['time'] for r in records]
            prices = [r['price'] for r in records]
            all_times.update(times)
            series.append({
                'name': key,
                'type': 'line',
                'smooth': True,
                'data': list(zip(times, prices))
            })

        chart = {
            'title': {'text': '票价变化趋势', 'left': 'center'},
            'tooltip': {'trigger': 'axis'},
            'legend': {'data': [s['name'] for s in series]},
            'xAxis': {
                'type': 'category',
                'data': sorted(all_times)
            },
            'yAxis': {'type': 'value', 'name': '票价 (¥)'},
            'series': series
        }
        return chart

    def make_summary(self, events: List) -> Dict:
        """生成汇总统计"""
        total_events = len(events)
        total_tickets = sum(len(e.tickets) for e in events)
        cities = set(e.city for e in events if e.city)
        platforms = set()
        all_prices = []
        for e in events:
            for t in e.tickets:
                platforms.add(t.platform)
                all_prices.append(t.price)

        avg_price = sum(all_prices) / len(all_prices) if all_prices else 0
        min_price = min(all_prices) if all_prices else 0
        max_price = max(all_prices) if all_prices else 0

        return {
            'total_events': total_events,
            'total_tickets': total_tickets,
            'city_count': len(cities),
            'platform_count': len(platforms),
            'avg_price': int(avg_price),
            'min_price': int(min_price),
            'max_price': int(max_price),
            'cities': sorted(list(cities)),
            'platforms': sorted(list(platforms))
        }
