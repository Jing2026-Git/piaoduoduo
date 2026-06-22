"""
票星球 (piaoxingqiu.com) 数据采集模块
支持: 关键词搜索、演出信息、票价数据
"""

import requests
import re
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote

from ..models import Event, TicketInfo


class PiaoxingqiuCollector:
    """票星球数据采集器"""

    PLATFORM_NAME = "票星球"

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
    ]

    def __init__(self, mode: str = "auto"):
        self.mode = mode
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://www.piaoxingqiu.com/'
        })

    def search(self, keyword: str, city: str = "", category: str = "", limit: int = 20) -> List[Event]:
        """根据关键词搜索演出"""
        if self.mode in ["auto", "real"]:
            try:
                events = self._real_search(keyword, city, category, limit)
                if events:
                    print(f"[票星球] 成功采集到 {len(events)} 场演出")
                    return events
            except Exception as e:
                print(f"[票星球] 真实采集失败: {e}")

        if self.mode in ["auto", "sample"]:
            print(f"[票星球] 使用示例数据模式（关键词: {keyword}）")
            return self._generate_sample_data(keyword, city, category, limit)

        return []

    def _real_search(self, keyword: str, city: str = "", category: str = "", limit: int = 20) -> List[Event]:
        """尝试从票星球接口采集数据"""
        # 票星球搜索接口
        search_url = "https://www.piaoxingqiu.com/search"

        params = {
            "keyword": keyword,
            "pageNo": 1,
            "pageSize": min(limit, 30)
        }

        if city:
            params["city"] = city

        try:
            response = self.session.get(search_url, params=params, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    return self._parse_search_result(data)
                except Exception:
                    # 返回 HTML 页面，降级到示例数据
                    pass
        except Exception as e:
            print(f"[票星球] 接口请求异常: {e}")

        return []

    def _parse_search_result(self, data: Dict) -> List[Event]:
        """解析搜索结果"""
        events = []
        items = data.get("data", {}).get("list", []) or data.get("list", [])

        for item in items:
            try:
                event = Event(
                    event_id=f"piaoxingqiu-{item.get('id', str(random.randint(10000, 99999)))}",
                    title=item.get("name", item.get("title", "")),
                    artist=item.get("artist", item.get("performer", "")),
                    venue=item.get("venue", item.get("address", "")),
                    city=item.get("city", ""),
                    date_str=item.get("showTime", item.get("show_time", "")),
                    category=item.get("category", "演唱会"),
                    source_url=item.get("url", f"https://www.piaoxingqiu.com/detail/{item.get('id', '')}"),
                    source_platform=self.PLATFORM_NAME,
                    description=item.get("description", item.get("summary", "")),
                    cover_image=item.get("poster", item.get("cover", "")),
                    platform_rating=float(item.get("rating", 0)) if item.get("rating") else 0.0,
                    sold_count=int(item.get("soldCount", item.get("sold_count", 0)))
                )

                show_time = item.get("showTime", "")
                try:
                    if "~" in show_time:
                        parts = show_time.split("~")
                        event.start_date = datetime.strptime(parts[0].strip(), "%Y-%m-%d %H:%M")
                        event.end_date = datetime.strptime(parts[1].strip(), "%Y-%m-%d %H:%M")
                    elif show_time:
                        event.start_date = datetime.strptime(show_time, "%Y-%m-%d %H:%M")
                except Exception:
                    pass

                price_str = item.get("price", "")
                event.tickets = self._parse_prices(price_str, event.title)

                events.append(event)
            except Exception as e:
                print(f"[票星球] 解析演出失败: {e}")
                continue

        return events

    def _parse_prices(self, price_str: str, title: str) -> List[TicketInfo]:
        """解析票价字符串"""
        tickets = []
        if not price_str:
            return tickets

        prices = re.findall(r'(\d+(?:\.\d+)?)', str(price_str))
        for p in prices:
            price = float(p)
            if price > 0:
                seat_type = self._guess_seat_type(price)
                tickets.append(TicketInfo(
                    price=price,
                    seat_type=seat_type,
                    ticket_status="在售",
                    platform=self.PLATFORM_NAME
                ))

        return sorted(tickets, key=lambda t: t.price)

    def _guess_seat_type(self, price: float) -> str:
        """根据价格推断座次类型"""
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

    def _generate_sample_data(self, keyword: str, city: str = "", category: str = "", limit: int = 20) -> List[Event]:
        """生成示例数据 - 票星球风格"""
        events = []

        sample_templates = [
            {
                "title": f"{keyword} 巡回演唱会",
                "artist": keyword,
                "venues": [
                    {"city": "北京", "venue": "凯迪拉克中心", "prices": [380, 580, 880, 1280]},
                    {"city": "上海", "venue": "梅赛德斯-奔驰文化中心", "prices": [480, 680, 980, 1380]},
                    {"city": "广州", "venue": "广州体育馆", "prices": [380, 580, 880, 1180]},
                    {"city": "深圳", "venue": "深圳湾体育中心", "prices": [480, 780, 1080, 1380]},
                ],
                "category": "演唱会",
                "desc": f"{keyword} 巡回演唱会，票星球官方售票！"
            },
            {
                "title": f"{keyword} 粉丝见面会",
                "artist": keyword,
                "venues": [
                    {"city": "上海", "venue": "上海静安体育中心", "prices": [580, 880, 1280]},
                    {"city": "北京", "venue": "北京工人体育馆", "prices": [480, 780, 1080]},
                ],
                "category": "演唱会",
                "desc": f"近距离接触 {keyword}，票星球专属票源！"
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

                event_date = start_date + timedelta(days=event_count * 7 + random.randint(-5, 5))

                event = Event(
                    event_id=f"piaoxingqiu-sample-{hash(keyword + venue_info['city']) & 0xFFFFFFFF}",
                    title=template["title"],
                    artist=template["artist"],
                    venue=venue_info["venue"],
                    city=venue_info["city"],
                    date_str=event_date.strftime("%Y-%m-%d %H:%M"),
                    start_date=event_date,
                    end_date=event_date,
                    sale_time=event_date - timedelta(days=28),
                    category=template["category"],
                    source_url="https://www.piaoxingqiu.com/",
                    source_platform=self.PLATFORM_NAME,
                    description=template["desc"],
                    cover_image="",
                    tags=[keyword, venue_info["city"], "票星球"],
                    platform_rating=round(random.uniform(4.3, 5.0), 1),
                    sold_count=random.randint(400, 7000)
                )

                for price in venue_info["prices"]:
                    seat_type = self._guess_seat_type(price)
                    status = "在售" if random.random() > 0.25 else "已售罄"
                    event.tickets.append(TicketInfo(
                        price=float(price),
                        seat_type=seat_type,
                        ticket_status=status,
                        platform=self.PLATFORM_NAME
                    ))

                events.append(event)
            if event_count > limit:
                break

        return events
