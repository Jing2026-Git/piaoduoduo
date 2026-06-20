"""
票多多 - 演唱会票价智能比价与资讯追踪工具
主入口类: 整合数据采集、清洗、比价、可视化等所有功能
"""

from typing import List, Optional, Dict
from datetime import datetime

from .collectors.damai import DamaiCollector
from .collectors.maoyan import MaoyanCollector
from .cleaner import DataCleaner
from .comparator import PriceComparator
from .visualizer import Visualizer
from .database import Database
from .models import Event, ComparisonResult


class PiaoDuoDuo:
    """票多多 - 主应用类"""

    def __init__(self, db_path: str = None, mode: str = "auto"):
        """
        初始化票多多

        Args:
            db_path: 数据库路径，默认在 data/piaoduoduo.db
            mode: 采集模式 - auto/real/sample
        """
        # 初始化数据库
        self.db = Database(db_path)

        # 初始化采集器
        self.damai = DamaiCollector(mode=mode)
        self.maoyan = MaoyanCollector(mode=mode)

        # 初始化处理模块
        self.cleaner = DataCleaner()
        self.comparator = PriceComparator()
        self.visualizer = Visualizer()

        # 缓存
        self._events_cache = []
        self._last_search_keyword = ""

    # ---------- 核心功能: 搜索与采集 ----------

    def search(self, keyword: str, city: str = "", limit: int = 30) -> List[Event]:
        """
        根据关键词搜索演出 - 整合所有平台的数据

        Args:
            keyword: 关键词（明星/乐队/演出名称等）
            city: 可选的城市过滤
            limit: 每个平台返回结果数量上限

        Returns:
            合并清洗后的演出信息列表
        """
        print(f"[票多多] 正在搜索关键词: '{keyword}'{' (城市: ' + city + ')' if city else ''}")

        # 从各平台采集
        all_events = []

        # 大麦网
        try:
            damai_events = self.damai.search(keyword, city=city, limit=limit)
            print(f"  - 大麦网: 采集到 {len(damai_events)} 场演出")
            all_events.extend(damai_events)
        except Exception as e:
            print(f"  - 大麦网: 采集失败 ({e})")

        # 猫眼演出
        try:
            maoyan_events = self.maoyan.search(keyword, city=city, limit=limit)
            print(f"  - 猫眼演出: 采集到 {len(maoyan_events)} 场演出")
            all_events.extend(maoyan_events)
        except Exception as e:
            print(f"  - 猫眼演出: 采集失败 ({e})")

        # 清洗数据（统一格式、过滤无效数据）
        cleaned = self.cleaner.clean(all_events)
        print(f"  - 清洗后: {len(cleaned)} 场有效演出")

        # 去重合并（识别同一场演出的不同平台数据）
        deduped = self.cleaner.dedupe(cleaned)
        print(f"  - 去重后: {len(deduped)} 场演出")

        # 缓存
        self._events_cache = deduped
        self._last_search_keyword = keyword

        # 保存到数据库（记录价格历史）
        self.db.save_events(deduped)

        return deduped

    # ---------- 核心功能: 票价对比分析 ----------

    def compare_prices(self, events: List[Event] = None) -> List[ComparisonResult]:
        """
        对演出进行票价对比分析

        Args:
            events: 演出列表，如不提供则使用上次搜索结果

        Returns:
            比价结果列表
        """
        if events is None:
            events = self._events_cache

        if not events:
            print("[票多多] 没有可分析的演出数据，请先执行搜索")
            return []

        results = self.comparator.compare(events)
        print(f"[票多多] 完成 {len(results)} 场演出票价对比分析")
        return results

    # ---------- 核心功能: 数据可视化 ----------

    def visualize(self, events: List[Event] = None) -> Dict:
        """
        生成可视化数据（用于前端展示）

        返回多种图表配置数据供网页使用
        """
        if events is None:
            events = self._events_cache

        if not events:
            return {}

        data = {
            'summary': self.visualizer.make_summary(events),
            'price_bar_chart': self.visualizer.make_price_bar_chart(events),
            'platform_pie_chart': self.visualizer.make_platform_pie_chart(events),
            'price_scatter_chart': self.visualizer.make_price_scatter_chart(events),
            'price_range_chart': self.visualizer.make_price_range_chart(events),
            'city_distribution_chart': self.visualizer.make_city_distribution_chart(events),
        }
        return data

    # ---------- 核心功能: 导出数据 ----------

    def export_csv(self, results: List[ComparisonResult], output_file: str) -> str:
        """导出比价结果为CSV文件"""
        csv_content = self.comparator.to_csv(results)
        with open(output_file, 'w', encoding='utf-8-sig') as f:
            f.write(csv_content)
        print(f"[票多多] CSV文件已导出: {output_file}")
        return output_file

    def export_json(self, results: List[ComparisonResult], output_file: str) -> str:
        """导出比价结果为JSON文件"""
        json_content = self.comparator.to_json(results)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(json_content)
        print(f"[票多多] JSON文件已导出: {output_file}")
        return output_file

    # ---------- 核心功能: 票价趋势 ----------

    def get_price_trend(self, keyword: str = "", event_id: str = "") -> Dict:
        """
        获取票价趋势（基于数据库历史记录）

        Args:
            keyword: 按关键词查询
            event_id: 按特定演出ID查询
        """
        history = []
        if event_id:
            history = self.db.get_price_history(event_id=event_id)
        elif keyword:
            history = self.db.get_price_history(title=keyword)

        if not history:
            return {'trend': {}, 'message': '暂无历史数据，多次运行后会记录价格变化趋势'}

        trend = self.comparator.analyze_price_trend(history)
        # 生成折线图数据
        line_chart = self.visualizer.make_trend_line_chart(history)
        return {
            'trend': trend,
            'line_chart': line_chart
        }

    # ---------- 核心功能: 开票提醒（半自动抢票助手） ----------

    def check_ticket_availability(self, keyword: str = "") -> Dict:
        """
        检查开票状态 - 用于开票提醒
        提示: 全自动抢票功能请谨慎使用，此功能仅用于监控和提醒

        返回: 各演出的在售票情况
        """
        events = self._events_cache or self.search(keyword, limit=20)

        if not events:
            return {'available': [], 'sold_out': [], 'upcoming': []}

        available = []
        sold_out = []

        for event in events:
            has_available = any(
                "售罄" not in t.ticket_status for t in event.tickets
            )
            if has_available:
                available.append({
                    'title': event.title,
                    'city': event.city,
                    'date': event.date_str,
                    'min_price': min(t.price for t in event.tickets if "售罄" not in t.ticket_status) if event.tickets else 0,
                    'platforms': list(set(t.platform for t in event.tickets))
                })
            else:
                sold_out.append({
                    'title': event.title,
                    'city': event.city,
                    'date': event.date_str
                })

        return {
            'available': available,
            'sold_out': sold_out,
            'available_count': len(available),
            'sold_out_count': len(sold_out),
            'alert_message': f"检测到 {len(available)} 场演出有票在售" if available else "暂无可购票演出，建议关注下次开票"
        }

    # ---------- 数据管理 ----------

    def get_stats(self) -> Dict:
        """获取数据库统计信息"""
        return self.db.get_stats()

    def get_cached_events(self) -> List[Event]:
        """获取缓存的演出数据"""
        return self._events_cache

    def clear_cache(self):
        """清空缓存"""
        self._events_cache = []
        self._last_search_keyword = ""

    def get_from_db(self, keyword: str = "", city: str = "", platform: str = "", limit: int = 100) -> List[Event]:
        """从数据库中查询历史数据"""
        return self.db.get_events(keyword=keyword, city=city, platform=platform, limit=limit)

    # ---------- 完整工作流 ----------

    def run_full_workflow(self, keyword: str, city: str = "", limit: int = 30) -> Dict:
        """
        执行完整工作流: 搜索 -> 清洗 -> 去重 -> 比价 -> 导出
        返回完整结果供网页或命令行展示
        """
        # 1. 搜索采集
        events = self.search(keyword, city=city, limit=limit)

        if not events:
            return {
                'success': False,
                'message': '没有找到相关演出数据',
                'keyword': keyword,
                'events': [],
                'comparison': [],
                'visualization': {}
            }

        # 2. 票价对比
        comparison = self.compare_prices(events)

        # 3. 生成可视化数据
        visualization = self.visualize(events)

        # 4. 开票状态检查
        availability = self.check_ticket_availability(keyword)

        return {
            'success': True,
            'keyword': keyword,
            'search_time': datetime.now().isoformat(),
            'events': [e.to_dict() for e in events],
            'comparison': [r.to_dict() for r in comparison],
            'visualization': visualization,
            'availability': availability,
            'summary': visualization.get('summary', {}),
            'stats': self.get_stats()
        }

    # ---------- 示例数据初始化 ----------

    def load_sample_data(self, keyword: str = "周杰伦") -> Dict:
        """
        加载示例数据 - 用于演示和快速体验
        """
        print(f"[票多多] 加载示例数据，关键词: {keyword}")

        # 强制使用 sample 模式
        self.damai.mode = "sample"
        self.maoyan.mode = "sample"

        result = self.run_full_workflow(keyword, limit=15)
        print(f"[票多多] 示例数据加载完成，共 {len(result['events'])} 场演出")
        return result
