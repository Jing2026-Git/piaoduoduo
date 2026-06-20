"""
大麦网 (damai.cn) 数据采集模块
支持: 关键词搜索、演出信息、票价数据

注意: 由于卖票平台有反爬虫机制，本模块支持两种模式：
1. real 模式: 尝试真实请求大麦网接口（可能受反爬限制）
2. sample 模式: 返回结构完整的示例数据（用于演示和测试）
"""

import requests
import json
import re
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import quote

from ..models import Event, TicketInfo


class DamaiCollector:
    """大麦网数据采集器"""

    PLATFORM_NAME = "大麦网"

    # 常用的 User-Agent，模拟真实浏览器
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
    ]

    def __init__(self, mode: str = "auto"):
        """
        初始化采集器

        Args:
            mode: 采集模式
                - "auto": 自动尝试真实采集，失败则返回示例数据
                - "real": 仅尝试真实采集
                - "sample": 仅返回示例数据
        """
        self.mode = mode
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Origin': 'https://search.damai.cn',
            'Referer': 'https://search.damai.cn/search.html'
        })

    # ---------- 核心采集方法 ----------

    def search(self, keyword: str, city: str = "", category: str = "", limit: int = 20) -> List[Event]:
        """
        根据关键词搜索演出

        Args:
            keyword: 关键词，如"周杰伦"、"演唱会"、"BTS"
            city: 城市过滤，如"北京"、"上海"
            category: 类型过滤，如"演唱会"、"音乐剧"、"话剧歌剧"
            limit: 返回结果数量限制

        Returns:
            演出活动列表
        """
        # 尝试真实采集
        if self.mode in ["auto", "real"]:
            try:
                events = self._real_search(keyword, city, category, limit)
                if events:
                    print(f"[大麦网] 成功采集到 {len(events)} 场演出")
                    return events
            except Exception as e:
                print(f"[大麦网] 真实采集失败: {e}")

        # 自动模式或 sample 模式：返回示例数据
        if self.mode in ["auto", "sample"]:
            print(f"[大麦网] 使用示例数据模式（关键词: {keyword}）")
            return self._generate_sample_data(keyword, city, category, limit)

        return []

    def _real_search(self, keyword: str, city: str = "", category: str = "", limit: int = 20) -> List[Event]:
        """尝试从大麦网真实接口采集数据"""

        # 大麦网搜索接口（注意: 平台接口可能随时变化）
        search_url = f"https://search.damai.cn/searchajax.html"

        params = {
            "keyword": keyword,
            "cty": city,
            "ctl": category,
            "order": "1",
            "pageNo": "1",
            "pageSize": str(min(limit, 50))
        }

        try:
            response = self.session.get(search_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return self._parse_search_result(data)
            else:
                print(f"[大麦网] HTTP请求失败: {response.status_code}")
        except Exception as e:
            print(f"[大麦网] 接口请求异常: {e}")

        return []

    def _parse_search_result(self, data: Dict) -> List[Event]:
        """解析搜索结果"""
        events = []
        items = data.get("resultData", {}).get("result", [])

        for item in items:
            try:
                event = Event(
                    event_id=f"damai-{item.get('itemNo', str(random.randint(10000, 99999)))}",
                    title=item.get("titleNoFormat", item.get("name", "")),
                    artist=item.get("actors", ""),
                    venue=item.get("venueName", ""),
                    city=item.get("cityName", ""),
                    date_str=item.get("showTime", ""),
                    category=item.get("category", ""),
                    source_url=item.get("itemUrl", ""),
                    source_platform=self.PLATFORM_NAME,
                    description=item.get("summary", ""),
                    cover_image=item.get("verticalPic", item.get("horizontalPic", "")),
                    platform_rating=float(item.get("score", 0)) if item.get("score") else 0.0,
                    sold_count=int(item.get("sellCount", 0)) if item.get("sellCount") else 0
                )

                # 解析时间
                show_time = item.get("showTime", "")
                try:
                    if "~" in show_time:
                        parts = show_time.split("~")
                        event.start_date = datetime.strptime(parts[0].strip(), "%Y-%m-%d %H:%M")
                        event.end_date = datetime.strptime(parts[1].strip(), "%Y-%m-%d %H:%M")
                    elif show_time:
                        event.start_date = datetime.strptime(show_time, "%Y-%m-%d %H:%M")
                except:
                    pass

                # 解析票价
                price_str = item.get("price", "")
                event.tickets = self._parse_prices(price_str, event.title)

                events.append(event)
            except Exception as e:
                print(f"[大麦网] 解析单个演出失败: {e}")
                continue

        return events

    def _parse_prices(self, price_str: str, title: str) -> List[TicketInfo]:
        """解析票价字符串，如: '¥380,¥680,¥980,¥1280'"""
        tickets = []
        if not price_str:
            return tickets

        # 提取所有数字价格
        prices = re.findall(r'(\d+(?:\.\d+)?)', price_str)
        for p in prices:
            price = float(p)
            if price > 0:
                # 根据价格粗略判断座次类型
                seat_type = self._guess_seat_type(price)
                tickets.append(TicketInfo(
                    price=price,
                    seat_type=seat_type,
                    ticket_status="在售",
                    platform=self.PLATFORM_NAME
                ))

        return sorted(tickets, key=lambda t: t.price)

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

    # ---------- 示例数据生成 ----------

    def _generate_sample_data(self, keyword: str, city: str = "", category: str = "", limit: int = 20) -> List[Event]:
        """
        生成示例数据 - 保持真实的结构，用于演示和测试
        """
        events = []

        # 常见演出模板
        sample_templates = [
            {
                "title": f"{keyword} 嘉年华世界巡回演唱会",
                "artist": keyword,
                "venues": [
                    {"city": "北京", "venue": "国家体育场（鸟巢）", "prices": [480, 680, 980, 1280, 1680, 1980]},
                    {"city": "上海", "venue": "上海体育场", "prices": [480, 680, 980, 1280, 1580, 1880]},
                    {"city": "广州", "venue": "大学城体育中心体育场", "prices": [380, 580, 880, 1280, 1580]},
                    {"city": "成都", "venue": "成都东安湖体育中心", "prices": [380, 580, 880, 1180, 1580]},
                    {"city": "深圳", "venue": "深圳湾体育中心", "prices": [480, 780, 980, 1280, 1680]}
                ],
                "category": "演唱会",
                "desc": f"{keyword} 2026 最新世界巡回演唱会，全新舞台设计、震撼视听效果！"
            },
            {
                "title": f"{keyword} LIVE 2026",
                "artist": keyword,
                "venues": [
                    {"city": "北京", "venue": "凯迪拉克中心", "prices": [380, 580, 880, 1280]},
                    {"city": "上海", "venue": "梅赛德斯-奔驰文化中心", "prices": [480, 680, 980, 1380]},
                    {"city": "杭州", "venue": "黄龙体育中心", "prices": [280, 480, 680, 980]},
                    {"city": "南京", "venue": "南京青奥体育公园", "prices": [380, 580, 780, 1080]}
                ],
                "category": "演唱会",
                "desc": f"{keyword} 最新 LIVE 巡演，带来全新音乐体验！"
            },
            {
                "title": f"{keyword} 粉丝见面会",
                "artist": keyword,
                "venues": [
                    {"city": "上海", "venue": "上海静安体育中心", "prices": [580, 880, 1280]},
                    {"city": "北京", "venue": "北京工人体育馆", "prices": [480, 780, 1180]},
                    {"city": "广州", "venue": "广州体育馆", "prices": [580, 880, 1180]}
                ],
                "category": "演唱会",
                "desc": f"近距离接触 {keyword} 的机会！粉丝专属福利。"
            },
            {
                "title": f"{keyword} 音乐节专场",
                "artist": keyword,
                "venues": [
                    {"city": "上海", "venue": "上海世博公园", "prices": [288, 488, 688, 988]},
                    {"city": "成都", "venue": "成都露天音乐公园", "prices": [199, 388, 588, 888]}
                ],
                "category": "演唱会",
                "desc": f"{keyword} 领衔，超豪华阵容！"
            }
        ]

        # 如果关键词比较泛，加一些额外的演出
        generic_shows = [
            {
                "title": "华语流行音乐盛典 2026",
                "artist": "多位明星",
                "venues": [
                    {"city": "北京", "venue": "国家体育场", "prices": [380, 680, 980, 1280, 1680]}
                ],
                "category": "演唱会",
                "desc": "年度最盛大的华语音乐盛典，顶级阵容齐聚一堂！"
            },
            {
                "title": "古典音乐之夜 - 交响音乐会",
                "artist": "国家交响乐团",
                "venues": [
                    {"city": "北京", "venue": "国家大剧院", "prices": [180, 380, 580, 880]}
                ],
                "category": "音乐会",
                "desc": "经典曲目演奏，感受古典音乐的魅力。"
            }
        ]

        # 根据关键词决定是否加泛类演出
        if keyword in ["演唱会", "音乐", "音乐会"]:
            templates = sample_templates + generic_shows
        else:
            templates = sample_templates

        start_date = datetime.now() + timedelta(days=random.randint(30, 120))

        event_count = 0
        for template in templates:
            for venue_info in template["venues"]:
                # 城市过滤
                if city and city not in venue_info["city"]:
                    continue

                event_count += 1
                if event_count > limit:
                    break

                event_date = start_date + timedelta(days=event_count * 7 + random.randint(-5, 5))

                event = Event(
                    event_id=f"damai-sample-{hash(keyword + venue_info['city'] + str(event_count)) & 0xFFFFFFFF}",
                    title=template["title"],
                    artist=template["artist"],
                    venue=venue_info["venue"],
                    city=venue_info["city"],
                    date_str=event_date.strftime("%Y-%m-%d %H:%M"),
                    start_date=event_date,
                    end_date=event_date,
                    sale_time=event_date - timedelta(days=30),
                    category=template["category"],
                    source_url=f"https://www.damai.cn/",
                    source_platform=self.PLATFORM_NAME,
                    description=template["desc"],
                    cover_image="",
                    tags=[keyword, venue_info["city"], template["category"]],
                    platform_rating=round(random.uniform(4.2, 5.0), 1),
                    sold_count=random.randint(500, 8000)
                )

                # 生成票价信息
                for price in venue_info["prices"]:
                    seat_type = self._guess_seat_type(price)
                    # 随机设置一些票档为售罄
                    status = "在售" if random.random() > 0.3 else "已售罄"
                    event.tickets.append(TicketInfo(
                        price=float(price),
                        seat_type=seat_type,
                        ticket_status=status,
                        platform=self.PLATFORM_NAME,
                        note=""
                    ))

                events.append(event)
            if event_count > limit:
                break

        return events

    # ---------- 单场演出详情采集 ----------

    def get_event_detail(self, event_id: str) -> Optional[Event]:
        """获取单场演出的详细信息（票价、场次等）"""
        # 简单实现：如果是示例数据，重新生成一个更详细的版本
        if "sample" in event_id or self.mode == "sample":
            keyword = "示例演出"
            events = self._generate_sample_data(keyword, limit=1)
            return events[0] if events else None

        return None
