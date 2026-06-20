"""
数据清洗与去重模块
功能: 合并来自不同平台的重复演出、标准化格式、清洗脏数据
"""

import re
from typing import List, Dict, Set, Tuple
from datetime import datetime
from collections import defaultdict

from .models import Event


class DataCleaner:
    """数据清洗器"""

    # 中文数字映射
    CN_NUM_MAP = {'零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
                  '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}

    def clean(self, events: List[Event]) -> List[Event]:
        """对原始数据进行清洗"""
        cleaned = []
        for event in events:
            # 1. 清洗标题：去除多余空格、HTML标签、特殊符号
            event.title = self._clean_text(event.title)

            # 2. 清洗艺人名称
            event.artist = self._clean_text(event.artist)

            # 3. 标准化场馆名称
            event.venue = self._normalize_venue(event.venue)

            # 4. 标准化城市名称
            event.city = self._normalize_city(event.city)

            # 5. 清洗票价信息
            event.tickets = self._clean_tickets(event.tickets)

            # 6. 过滤无效数据（没有标题或没有票价信息的）
            if event.title and event.tickets:
                cleaned.append(event)

        return cleaned

    def dedupe(self, events: List[Event]) -> List[Event]:
        """
        跨平台数据去重
        识别同一场演出（相同标题+相同城市+相近日期），合并为一个事件记录
        保留各平台的票价信息，供后续比价分析使用
        """
        if not events:
            return []

        # 按关键词分组（标题核心词 + 城市）
        groups = defaultdict(list)

        for event in events:
            # 生成去重key：标题核心词 + 城市 + 日期
            key_words = self._extract_core_words(event.title)
            city_norm = self._normalize_city(event.city)
            date_str = event.date_str[:10] if event.date_str else "unknown"

            # 使用多个可能的key来匹配
            keys = []
            for word in key_words[:2]:  # 取前2个核心词
                keys.append(f"{word}|{city_norm}|{date_str}")

            # 找到最合适的分组
            target_key = None
            for key in keys:
                if key in groups:
                    target_key = key
                    break

            if target_key is None:
                target_key = keys[0] if keys else f"{event.title}|{city_norm}|{date_str}"

            groups[target_key].append(event)

        # 处理每组：合并同一场演出的不同平台票价
        merged_events = []
        for key, group in groups.items():
            if len(group) == 1:
                merged_events.append(group[0])
                continue

            # 同一场演出的不同平台数据：合并
            # 以第一个事件为基础，合并其他平台的票价信息
            base_event = group[0]
            all_tickets = list(base_event.tickets)

            for other_event in group[1:]:
                # 标记这个事件来自哪个平台
                for ticket in other_event.tickets:
                    # 避免重复添加同平台同价位票
                    is_duplicate = False
                    for existing in all_tickets:
                        if (existing.platform == ticket.platform and
                                abs(existing.price - ticket.price) < 1.0 and
                                existing.seat_type == ticket.seat_type):
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        all_tickets.append(ticket)

            base_event.tickets = sorted(all_tickets, key=lambda t: t.price)
            merged_events.append(base_event)

        # 按日期排序
        merged_events.sort(key=lambda e: e.start_date or datetime.max)
        return merged_events

    def clean_and_dedupe(self, events: List[Event]) -> List[Event]:
        """清洗 + 去重"""
        cleaned = self.clean(events)
        deduped = self.dedupe(cleaned)
        return deduped

    # ---------- 辅助方法 ----------

    def _clean_text(self, text: str) -> str:
        """清洗文本：去除HTML标签、多余空格、特殊符号"""
        if not text:
            return ""

        # 去除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 去除多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        # 去除特殊符号开头
        text = text.strip('·•*【】[]()()')

        return text

    def _normalize_venue(self, venue: str) -> str:
        """标准化场馆名称"""
        if not venue:
            return ""

        # 去除常见的包装词
        venue = re.sub(r'（.*?\)', '', venue)
        venue = re.sub(r'\(.*?\)', '', venue)
        venue = venue.strip()

        # 场馆别名映射
        venue_map = {
            "国家体育场": "国家体育场（鸟巢）",
            "鸟巢": "国家体育场（鸟巢）",
            "上海体育场": "上海体育场",
            "上海大舞台": "上海大舞台",
            "工人体育场": "工人体育场",
        }

        for key, value in venue_map.items():
            if key in venue:
                return value

        return venue

    def _normalize_city(self, city: str) -> str:
        """标准化城市名称"""
        if not city:
            return ""

        # 去除"市"等后缀
        city = city.replace("市", "").replace("区", "").strip()

        # 常见别名
        city_map = {
            "京": "北京",
            "沪": "上海",
            "花城": "广州",
            "蓉城": "成都",
            "鹏城": "深圳",
        }

        return city_map.get(city, city)

    def _clean_tickets(self, tickets):
        """清洗票价信息"""
        if not tickets:
            return []

        cleaned = []
        seen = set()

        for ticket in tickets:
            # 过滤无效价格
            if ticket.price <= 0 or ticket.price > 100000:  # 合理范围
                continue

            # 去重（相同价格 + 相同座次 + 相同平台视为重复）
            key = (int(ticket.price), ticket.seat_type, ticket.platform)
            if key in seen:
                continue
            seen.add(key)

            cleaned.append(ticket)

        return cleaned

    def _extract_core_words(self, title: str) -> List[str]:
        """从标题中提取核心关键词（用于去重匹配）"""
        if not title:
            return []

        # 去除演出类型词
        noise_words = {"演唱会", "音乐会", "巡回", "世界", "嘉年华",
                       "LIVE", "live", "专场", "见面会", "粉丝",
                       "音乐节", "演出", "站", "2024", "2025", "2026",
                       "巡演", "全新", "舞台", "音乐"}

        # 分词（简单切分）
        words = re.findall(r'[\u4e00-\u9fa5a-zA-Z]+', title)
        core_words = []

        for w in words:
            if w not in noise_words and len(w) >= 2:
                core_words.append(w)

        return core_words if core_words else [title]

    # ---------- 统计信息 ----------

    def get_cleaning_stats(self, original: List[Event], cleaned: List[Event]) -> Dict:
        """获取清洗统计信息"""
        return {
            "original_count": len(original),
            "cleaned_count": len(cleaned),
            "removed_count": len(original) - len(cleaned),
            "duplicates_removed": sum(1 for e in original) - len(cleaned)
        }
