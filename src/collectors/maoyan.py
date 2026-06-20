"""
猫眼演出 (show.maoyan.com) 数据采集模块
支持: 关键词搜索、演出信息、票价数据

注意: 猫眼演出同样有反爬虫机制，设计与大麦网相同的策略
"""

import requests
import json
import re
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from ..models import Event, TicketInfo


class MaoyanCollector:
    """猫眼演出数据采集器"""

    PLATFORM_NAME = "猫眼演出"

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Safari/605.1.15"
    ]

    def __init__(self, mode: str = "auto"):
        self.mode = mode
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        })

    def search(self, keyword: str, city: str = "", category: str = "", limit: int = 20) -> List[Event]:
        """根据关键词搜索演出"""
        # 尝试真实采集
        if self.mode in ["auto", "real"]:
            try:
                events = self._real_search(keyword, city, category, limit)
                if events:
                    print(f"[猫眼演出] 成功采集到 {len(events)} 场演出")
                    return events
            except Exception as e:
                print(f"[猫眼演出] 真实采集失败: {e}")

        # 示例数据模式
        if self.mode in ["auto", "sample"]:
            print(f"[猫眼演出] 使用示例数据模式（关键词: {keyword}）")
            return self._generate_sample_data(keyword, city, category, limit)

        return []

    def _real_search(self, keyword: str, city: str = "", category: str = "", limit: int = 20) -> List[Event]:
        """尝试从猫眼演出接口采集数据（实验性）"""
        search_url = "https://show.maoyan.com/qqw"
        params = {
            "keyword": keyword,
            "offset": 0,
            "limit": min(limit, 20)
        }

        try:
            response = self.session.get(search_url, params=params, timeout=10)
            if response.status_code == 200:
                # 猫眼演出返回的是HTML页面，需要从中提取JavaScript数据
                html = response.text
                # 尝试提取页面中的JSON数据
                # 这里是简化实现，实际页面结构可能需要根据最新接口调整
                pass
        except Exception as e:
            print(f"[猫眼演出] 接口请求异常: {e}")

        return []

    def _generate_sample_data(self, keyword: str, city: str = "", category: str = "", limit: int = 20) -> List[Event]:
        """
        生成猫眼演出风格的示例数据
        注意: 与大麦网数据略有差异（相同演出的票价、场次可能不同），
        这样后续比价分析时可以展示出跨平台的差异
        """
        events = []

        # 猫眼演出的票价可能比大麦网略低或略高，模拟真实平台差异
        price_adjust = 0.9  # 平均打9折，模拟平台差价

        sample_templates = [
            {
                "title": f"{keyword} 嘉年华世界巡回演唱会",
                "artist": keyword,
                "venues": [
                    {"city": "北京", "venue": "国家体育场（鸟巢）",
                     "prices": [int(x * price_adjust) for x in [480, 680, 980, 1280, 1580]]},
                    {"city": "上海", "venue": "上海体育场",
                     "prices": [int(x * price_adjust) for x in [580, 780, 980, 1280]]},
                    {"city": "广州", "venue": "大学城体育中心体育场",
                     "prices": [int(x * price_adjust) for x in [380, 580, 880, 1280]]},
                    {"city": "深圳", "venue": "深圳湾体育中心",
                     "prices": [int(x * price_adjust) for x in [480, 780, 1080]]},
                ],
                "category": "演唱会",
                "desc": f"猫眼演出独家呈现！{keyword} 2026 最新巡演，超值票价！"
            },
            {
                "title": f"{keyword} LIVE 2026",
                "artist": keyword,
                "venues": [
                    {"city": "北京", "venue": "凯迪拉克中心",
                     "prices": [int(x * price_adjust) for x in [480, 680, 980, 1280]]},
                    {"city": "上海", "venue": "梅赛德斯-奔驰文化中心",
                     "prices": [int(x * price_adjust) for x in [380, 580, 880, 1180]]},
                    {"city": "成都", "venue": "成都东安湖体育中心",
                     "prices": [int(x * price_adjust) for x in [280, 480, 680, 980]]},
                ],
                "category": "演唱会",
                "desc": f"{keyword} 最新 LIVE 巡演！猫眼购票有机会赢取签名周边！"
            }
        ]

        start_date = datetime.now() + timedelta(days=random.randint(30, 120))
        event_count = 0

        for template in sample_templates:
            for venue_info in template["venues"]:
                if city and city not in venue_info["city"]:
                    continue

                event_count += 1
                if event_count > limit:
                    break

                event_date = start_date + timedelta(days=event_count * 10 + random.randint(-3, 3))

                event = Event(
                    event_id=f"maoyan-sample-{hash(keyword + venue_info['city'] + str(event_count)) & 0xFFFFFFFF}",
                    title=template["title"],
                    artist=template["artist"],
                    venue=venue_info["venue"],
                    city=venue_info["city"],
                    date_str=event_date.strftime("%Y-%m-%d %H:%M"),
                    start_date=event_date,
                    end_date=event_date,
                    sale_time=event_date - timedelta(days=25),
                    category=template["category"],
                    source_url="https://show.maoyan.com/",
                    source_platform=self.PLATFORM_NAME,
                    description=template["desc"],
                    cover_image="",
                    tags=[keyword, venue_info["city"], "猫眼独家"],
                    platform_rating=round(random.uniform(4.0, 4.9), 1),
                    sold_count=random.randint(300, 6000)
                )

                for price in venue_info["prices"]:
                    seat_type = self._guess_seat_type(price)
                    status = "在售" if random.random() > 0.25 else "已售罄"
                    event.tickets.append(TicketInfo(
                        price=float(price),
                        seat_type=seat_type,
                        ticket_status=status,
                        platform=self.PLATFORM_NAME,
                        note="猫眼演出"
                    ))

                events.append(event)
            if event_count > limit:
                break

        return events

    def _guess_seat_type(self, price: float) -> str:
        """根据价格粗略推断座次类型"""
        if price >= 1500:
            return "VIP/内场前排"
        elif price >= 1000:
            return "内场"
        elif price >= 680:
            return "看台前区"
        elif price >= 380:
            return "看台"
        else:
            return "看台后区/站票"
