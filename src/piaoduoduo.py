"""
票多多 - 方案 C：混合策略
功能：演出资讯聚合 + 用户关注 + 半自动票价 + 开票提醒
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta

from .collectors.damai import DamaiCollector
from .collectors.maoyan import MaoyanCollector
from .collectors.piaoxingqiu import PiaoxingqiuCollector
from .collectors.ticketmaster import TicketmasterCollector
from .collectors.social_media import SocialMediaCollector
from .cleaner import DataCleaner
from .comparator import PriceComparator
from .visualizer import Visualizer
from .database import Database
from .models import Event, ComparisonResult, TicketInfo


class PiaoDuoDuo:
    """票多多 - 主应用类（方案 C）"""

    def __init__(self, db_path: str = None, mode: str = "auto"):
        self.db = Database(db_path)
        self.damai = DamaiCollector(mode=mode)
        self.maoyan = MaoyanCollector(mode=mode)
        self.piaoxingqiu = PiaoxingqiuCollector(mode=mode)
        self.ticketmaster = TicketmasterCollector(mode=mode)
        self.social_media = SocialMediaCollector(mode=mode)
        self.cleaner = DataCleaner()
        self.comparator = PriceComparator()
        self.visualizer = Visualizer()
        self._events_cache = []
        self._last_search_keyword = ""
        self._last_mode = mode
        self._is_foreign_search = False

    # ---------- 核心功能: 搜索与采集 ----------

    def search(self, keyword: str, city: str = "", limit: int = 30) -> List[Event]:
        print(f"[票多多] 正在搜索关键词: '{keyword}'{' (城市: ' + city + ')' if city else ''}")
        all_events = []
        mode_used = []

        # 判断是否为国际艺人
        is_foreign = self.social_media.is_foreign_artist(keyword)

        if is_foreign:
            # 国际艺人：走 Ticketmaster + 社交媒体，不调国内平台（他们不会在大陆开演唱会）
            print(f"  [检测] '{keyword}' 识别为国际艺人，通过 Ticketmaster + 社交媒体查询...")
            try:
                tm_events = self.ticketmaster.search(keyword, city=city, limit=limit)
                print(f"  - Ticketmaster: 采集到 {len(tm_events)} 场演出")
                all_events.extend(tm_events)
                mode_used.append("Ticketmaster")
            except Exception as e:
                print(f"  - Ticketmaster: 采集失败 ({e})")
            try:
                social_events = self.social_media.search(keyword, city=city, limit=limit)
                if social_events:
                    print(f"  - 社交媒体/国际: 采集到 {len(social_events)} 场演出")
                    all_events.extend(social_events)
                    mode_used.append("社交媒体")
            except Exception as e:
                print(f"  - 社交媒体: 采集失败 ({e})")
            print(f"  - [提示] '{keyword}' 不会在中国大陆开演唱会，购票需访问 Ticketmaster / AXS 等官方渠道")
        else:
            # 国内艺人/泛关键词：走国内三大平台
            platform_sources = [
                ("大麦网", self.damai),
                ("猫眼演出", self.maoyan),
                ("票星球", self.piaoxingqiu),
            ]

            for platform_name, collector in platform_sources:
                try:
                    events = collector.search(keyword, city=city, limit=limit)
                    print(f"  - {platform_name}: 采集到 {len(events)} 场演出")
                    all_events.extend(events)
                    mode_used.append(platform_name)
                except Exception as e:
                    print(f"  - {platform_name}: 采集失败 ({e})")

        # 如果没有任何数据，给出提示
        if not all_events:
            print(f"  [提示] 未找到 '{keyword}' 相关演出，请尝试其他关键词")

        cleaned = self.cleaner.clean(all_events)
        deduped = self.cleaner.dedupe(cleaned)
        print(f"  - 清洗后: {len(cleaned)} 场，去重后: {len(deduped)} 场")
        print(f"  - 数据来源: {', '.join(mode_used) if mode_used else '无'}")

        self._events_cache = deduped
        self._last_search_keyword = keyword
        self._is_foreign_search = is_foreign  # 标记是否为国际艺人搜索
        self.db.save_events(deduped)
        return deduped

    # ---------- 核心功能: 票价对比分析 ----------

    def compare_prices(self, events: List[Event] = None) -> List[ComparisonResult]:
        if events is None:
            events = self._events_cache
        if not events:
            return []
        return self.comparator.compare(events)

    # ---------- 核心功能: 数据可视化 ----------

    def visualize(self, events: List[Event] = None) -> Dict:
        if events is None:
            events = self._events_cache
        if not events:
            return {}
        return {
            'summary': self.visualizer.make_summary(events),
            'price_bar_chart': self.visualizer.make_price_bar_chart(events),
            'platform_pie_chart': self.visualizer.make_platform_pie_chart(events),
            'price_scatter_chart': self.visualizer.make_price_scatter_chart(events),
            'price_range_chart': self.visualizer.make_price_range_chart(events),
            'city_distribution_chart': self.visualizer.make_city_distribution_chart(events),
        }

    # ---------- 核心功能: 票价趋势 ----------

    def get_price_trend(self, keyword: str = "", event_id: str = "") -> Dict:
        history = []
        if event_id:
            history = self.db.get_price_history(event_id=event_id)
        elif keyword:
            history = self.db.get_price_history(title=keyword)
        if not history:
            return {'trend': {}, 'message': '暂无历史数据'}
        trend = self.comparator.analyze_price_trend(history)
        line_chart = self.visualizer.make_trend_line_chart(history)
        return {'trend': trend, 'line_chart': line_chart}

    def check_ticket_availability(self, keyword: str = "") -> Dict:
        events = self._events_cache or self.search(keyword, limit=20)
        if not events:
            return {'available': [], 'sold_out': [], 'upcoming': []}
        available, sold_out = [], []
        for event in events:
            has_available = any("售罄" not in t.ticket_status for t in event.tickets)
            data = {'title': event.title, 'city': event.city, 'date': event.date_str,
                    'min_price': min((t.price for t in event.tickets if "售罄" not in t.ticket_status), default=0),
                    'platforms': list(set(t.platform for t in event.tickets))}
            (available if has_available else sold_out).append(data)
        return {
            'available': available, 'sold_out': sold_out,
            'available_count': len(available), 'sold_out_count': len(sold_out),
            'alert_message': f"检测到 {len(available)} 场演出有票在售" if available else "暂无可购票演出，建议关注下次开票"
        }

    # ============== 方案 C：用户关注（核心功能） ==============

    def add_to_watchlist(self, event_id: str, user_notes: str = "", priority: int = 0) -> bool:
        """
        将一场演出加入关注列表
        如果 event_id 不在数据库，尝试从缓存中查找
        返回 True 表示成功
        """
        event = self.db.get_event_by_id(event_id)
        if not event:
            # 从缓存中查找
            for e in self._events_cache:
                if e.event_id == event_id:
                    event = e
                    break
        if not event:
            print(f"[票多多] 关注失败：未找到演出 ID {event_id}")
            return False

        self.db.add_to_watchlist(event, user_notes=user_notes, priority=priority)
        print(f"[票多多] 已关注：{event.title} ({event.city})")
        return True

    def remove_from_watchlist(self, event_id: str) -> bool:
        """取消关注"""
        self.db.remove_from_watchlist(event_id)
        print(f"[票多多] 已取消关注：{event_id}")
        return True

    def get_watchlist(self) -> List[Dict]:
        """获取关注列表（带票价信息和开票状态）"""
        items = self.db.get_watchlist()
        result = []
        for item in items:
            item_dict = item.to_dict()
            # 补充关注后的票价信息
            tickets = self.db.get_tickets(item.event_id)
            item_dict['tickets'] = [t.__dict__ for t in tickets]
            item_dict['ticket_count'] = len(tickets)
            # 判断用户是否编辑过票价
            user_edited = any(t.is_user_edited for t in tickets)
            item_dict['is_user_edited'] = user_edited
            # 计算离开票还有几天
            days_to_sale = None
            if item.sale_time:
                try:
                    sale_dt = datetime.fromisoformat(item.sale_time)
                    days_to_sale = (sale_dt - datetime.now()).days
                except Exception:
                    pass
            item_dict['days_to_sale'] = days_to_sale
            result.append(item_dict)
        return result

    def update_watch_notes(self, event_id: str, user_notes: str, priority: int = 0):
        """更新关注项目的备注和优先级"""
        self.db.update_watch_notes(event_id, user_notes, priority)

    # ============== 方案 C：半自动票价编辑 ==============

    def get_event_tickets(self, event_id: str) -> List[Dict]:
        """获取某场演出的当前票价配置"""
        tickets = self.db.get_tickets(event_id)
        result = []
        for t in tickets:
            result.append({
                'price': t.price,
                'seat_type': t.seat_type,
                'ticket_status': t.ticket_status,
                'platform': t.platform,
                'is_user_edited': t.is_user_edited
            })
        return result

    def update_event_tickets(self, event_id: str, tickets_data: List[Dict]) -> bool:
        """
        用户手动编辑票价
        tickets_data 格式:
        [
            {"price": 480, "seat_type": "看台", "ticket_status": "在售", "platform": "大麦网"},
            ...
        ]
        """
        if not tickets_data:
            return False
        # 验证格式
        valid_data = []
        for t in tickets_data:
            try:
                price = float(t.get('price', 0))
                if price <= 0:
                    continue
                valid_data.append({
                    'price': price,
                    'seat_type': str(t.get('seat_type', '')),
                    'ticket_status': str(t.get('ticket_status', '在售')),
                    'platform': str(t.get('platform', ''))
                })
            except Exception:
                continue
        if not valid_data:
            return False
        self.db.update_tickets(event_id, valid_data)
        print(f"[票多多] 已更新票价信息，共 {len(valid_data)} 个票档")
        return True

    # ============== 方案 C：开票提醒 ==============

    def get_upcoming_sales(self, days_ahead: int = 7) -> List[Dict]:
        """
        获取未来 N 天内即将开票的演出（用于提醒）
        """
        items = self.db.get_upcoming_sales(days_ahead=days_ahead)
        result = []
        for item in items:
            item_dict = item.to_dict()
            # 计算离开票天数和小时数
            if item.sale_time:
                try:
                    sale_dt = datetime.fromisoformat(item.sale_time)
                    delta = sale_dt - datetime.now()
                    total_hours = int(delta.total_seconds() / 3600)
                    days = delta.days
                    hours = int((delta.total_seconds() - days * 86400) / 3600)
                    item_dict['days_to_sale'] = days
                    item_dict['hours_to_sale'] = hours
                    item_dict['total_hours'] = total_hours
                except Exception:
                    item_dict['days_to_sale'] = None
                    item_dict['hours_to_sale'] = None
            result.append(item_dict)
        # 按紧急程度排序
        result.sort(key=lambda x: x.get('total_hours', 99999))
        return result

    def get_sale_calendar(self, days_ahead: int = 30) -> Dict:
        """
        获取未来 N 天的开票日历
        返回: {'2026-07-01': [{event1}, {event2}], ...}
        """
        raw_calendar = self.db.get_sale_calendar(days_ahead=days_ahead)
        result = {}
        for date_key, items in raw_calendar.items():
            result[date_key] = [item.to_dict() for item in items]
        # 生成未来 N 天的日期列表（用于前端展示）
        dates = []
        for i in range(days_ahead):
            d = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
            dates.append({
                'date': d,
                'weekday': ['周一','周二','周三','周四','周五','周六','周日'][datetime.strptime(d, '%Y-%m-%d').weekday()],
                'events': result.get(d, [])
            })
        return {'dates': dates, 'total_events': sum(len(v) for v in result.values())}

    # ---------- 数据管理 ----------

    def get_stats(self) -> Dict:
        stats = self.db.get_stats()
        # 补充计算：即将开票数量、关注中演出数
        watchlist = self.get_watchlist()
        upcoming = self.get_upcoming_sales(30)
        stats['upcoming_count_7'] = len(self.get_upcoming_sales(7))
        stats['upcoming_count_30'] = len(upcoming)
        stats['watchlist_total'] = len(watchlist)
        return stats

    def get_from_db(self, keyword: str = "", city: str = "", platform: str = "", limit: int = 100) -> List[Event]:
        return self.db.get_events(keyword=keyword, city=city, platform=platform, limit=limit)

    def get_event_detail(self, event_id: str) -> Optional[Dict]:
        """获取一场演出的完整详情（含关注状态）"""
        event = self.db.get_event_by_id(event_id)
        if not event:
            # 从缓存中查找
            for e in self._events_cache:
                if e.event_id == event_id:
                    event = e
                    break
        if not event:
            return None
        data = event.to_dict()
        data['is_watching'] = self.db.is_in_watchlist(event_id)
        # 补充用户编辑状态
        tickets = self.db.get_tickets(event_id)
        data['is_user_edited'] = any(t.is_user_edited for t in tickets)
        return data

    def clear_cache(self):
        self._events_cache = []
        self._last_search_keyword = ""

    # ---------- 完整工作流 ----------

    def run_full_workflow(self, keyword: str, city: str = "", limit: int = 30) -> Dict:
        events = self.search(keyword, city=city, limit=limit)

        # 判断数据来源
        platforms_found = set()
        for e in events:
            if e.source_platform:
                platforms_found.add(e.source_platform)
        data_source = list(platforms_found) if platforms_found else []
        is_foreign = self._is_foreign_search

        # 国际艺人时附上官方购票渠道
        official_links = []
        if is_foreign:
            official_links = self.social_media.get_official_ticket_urls(keyword)

        if not events:
            message = f"未找到 '{keyword}' 相关演出数据"
            if is_foreign:
                message = f"'{keyword}' 是国际艺人，未在其巡演区域发现相关演出。请查看下方官方购票渠道。"
            return {
                'success': False,
                'message': message,
                'keyword': keyword,
                'events': [],
                'comparison': [],
                'visualization': {},
                'data_source': data_source,
                'is_sample_data': False,
                'is_foreign_artist': is_foreign,
                'official_links': official_links
            }
        comparison = self.compare_prices(events)
        visualization = self.visualize(events)
        availability = self.check_ticket_availability(keyword)
        # 补充每个演出的关注状态
        events_with_watch = []
        for e in events:
            ed = e.to_dict()
            ed['is_watching'] = self.db.is_in_watchlist(e.event_id)
            events_with_watch.append(ed)
        return {
            'success': True,
            'keyword': keyword,
            'search_time': datetime.now().isoformat(),
            'events': events_with_watch,
            'comparison': [r.to_dict() for r in comparison],
            'visualization': visualization,
            'availability': availability,
            'summary': visualization.get('summary', {}),
            'stats': self.get_stats(),
            'data_source': data_source,
            'is_sample_data': False,
            'is_foreign_artist': is_foreign,
            'official_links': official_links
        }

    def load_sample_data(self, keyword: str = "周杰伦") -> Dict:
        print(f"[票多多] 加载示例数据，关键词: {keyword}")
        is_foreign = self.social_media.is_foreign_artist(keyword)
        if is_foreign:
            # 国际艺人：Ticketmaster 示例数据 + 关闭国内平台
            self.damai.mode = "real"
            self.maoyan.mode = "real"
            self.piaoxingqiu.mode = "real"
            self.ticketmaster.mode = "sample"
            self.social_media.mode = "real"
        else:
            self.damai.mode = "sample"
            self.maoyan.mode = "sample"
            self.piaoxingqiu.mode = "sample"
            self.ticketmaster.mode = "real"
            self.social_media.mode = "real"
        result = self.run_full_workflow(keyword, limit=15)
        result['is_sample_data'] = True
        result['message'] = "这是示例数据，用于功能演示。切换到「自动模式」或「真实采集」可获取真实数据。"
        print(f"[票多多] 示例数据加载完成，共 {len(result['events'])} 场演出")
        return result
