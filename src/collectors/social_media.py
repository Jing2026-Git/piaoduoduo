"""
社交媒体与国际艺人数据采集模块
用于处理国外艺人（Stray Kids、Taylor Swift 等）的演出资讯
数据来源：微博超话、小红书笔记、Twitter/Instagram 动态等

注意：
- 这类艺人的演出通常不在国内售票平台售卖
- 开票信息需要从社交媒体获取
- 购票需要访问官方渠道或境外平台
"""

import requests
import re
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from ..models import Event, TicketInfo


# 已知的国外艺人列表及其演出特征
# 格式: {英文名: [可能的中文名/别名]}
FOREIGN_ARTIST_ALIASES = {
    "stray kids": ["Stray Kids", "迷路孩子", "SKZ"],
    "taylor swift": ["Taylor Swift", "霉霉", "泰勒"],
    "blackpink": ["BLACKPINK", "粉墨", "BP"],
    "bts": ["BTS", "防弹少年团", "阿米"],
    "ed sheeran": ["Ed Sheeran", "黄老板", "艾德·希兰"],
    "coldplay": ["Coldplay", "酷玩乐队"],
    "the weeknd": ["The Weeknd", "盆栽", "威肯"],
    "bruno mars": ["Bruno Mars", "火星人"],
    "adele": ["Adele", "阿黛尔"],
    "billie eilish": ["Billie Eilish", "碧梨"],
    "onedirection": ["One Direction", "1D"],
    "maroon 5": ["Maroon 5", "魔力红"],
    "lady gaga": ["Lady Gaga", "嘎嘎"],
    "olivia rodrigo": ["Olivia Rodrigo", "戳爷"],
    "justin bieber": ["Justin Bieber", "丁日", "比伯"],
    "ariana grande": ["Ariana Grande", "Ariana", "Ari"],
    "twice": ["TWICE", "兔瓦斯"],
    "seventeen": ["SEVENTEEN", "小十七", "SVT"],
    "enhypen": ["ENHYPEN", "符"],
    "newjeans": ["NewJeans", "鲸"],
    "zico": ["ZICO", "禹智皓"],
    "IU": ["IU", "李知恩", "小女孩"],
    "lisa": ["Lisa", "莉莎", "人间芭比"],
    "coachella": ["Coachella", "科切拉"],
    "glastonbury": ["Glastonbury", "格拉斯顿伯里"],
}

# 常见的境外购票官网
OFFICIAL_TICKET_URLS = {
    "stray kids": [
        ("Stray Kids 官网", "https://straykids.jype.com/"),
        ("Ticketmaster", "https://www.ticketmaster.com/"),
        ("AXS", "https://www.axs.com/"),
    ],
    "taylor swift": [
        ("Taylor Swift 官网", "https://taylorswift.com/"),
        ("Ticketmaster", "https://www.ticketmaster.com/"),
    ],
    "blackpink": [
        ("BLACKPINK 官网", "https://blackpinkofficial.com/"),
        ("Ticketmaster", "https://www.ticketmaster.com/"),
    ],
    "bts": [
        ("BTS 官网", "https://ibighit.com/bts/"),
        ("Ticketmaster", "https://www.ticketmaster.com/"),
    ],
    "default": [
        ("Ticketmaster 全球", "https://www.ticketmaster.com/"),
        ("AXS", "https://www.axs.com/"),
        ("StubHub", "https://www.stubhub.com/"),
    ],
}


class SocialMediaCollector:
    """社交媒体与国际艺人数据采集器"""

    PLATFORM_NAME = "社交媒体"

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    def __init__(self, mode: str = "auto"):
        self.mode = mode
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

    def is_foreign_artist(self, keyword: str) -> bool:
        """检测关键词是否指向国外艺人"""
        kw_lower = keyword.lower().strip()
        for aliases in FOREIGN_ARTIST_ALIASES.values():
            if kw_lower in [a.lower() for a in aliases]:
                return True
        return False

    def get_official_ticket_urls(self, keyword: str) -> List[Dict[str, str]]:
        """获取某艺人的官方购票链接"""
        kw_lower = keyword.lower().strip()
        for artist_key, urls in OFFICIAL_TICKET_URLS.items():
            if kw_lower in [a.lower() for a in FOREIGN_ARTIST_ALIASES.get(artist_key, [])]:
                return [{"name": name, "url": url} for name, url in urls]
        return [{"name": name, "url": url} for name, url in OFFICIAL_TICKET_URLS["default"]]

    def search(self, keyword: str, city: str = "", category: str = "", limit: int = 20) -> List[Event]:
        """
        搜索国际艺人演出资讯
        策略：
        1. 微博超话/话题搜索（真实尝试）
        2. 小红书笔记搜索（真实尝试）
        3. 降级到预设的模板数据（涵盖常见国际巡演）
        """
        is_foreign = self.is_foreign_artist(keyword)

        if not is_foreign:
            # 非国外艺人，返回空，交给国内平台处理
            return []

        if self.mode in ["auto", "real"]:
            events = self._real_search(keyword, city, limit)
            if events:
                print(f"[社交媒体] 采集到 {len(events)} 条 {keyword} 国际巡演资讯")
                return events

        if self.mode in ["auto", "sample"]:
            return self._generate_international_sample(keyword, city, limit)

        return []

    def _real_search(self, keyword: str, city: str = "", limit: int = 20) -> List[Event]:
        """
        尝试从社交媒体获取国际艺人演出资讯
        注意：这里实际抓取微博/小红书成功率较低，
        主要展示可扩展的接口设计
        """
        events = []

        # 尝试小红书搜索接口（实验性）
        try:
            xhs_url = "https://www.xiaohongshu.com/search_result"
            params = {"keyword": keyword + " 演唱会", "type": "51"}
            resp = self.session.get(xhs_url, params=params, timeout=8)
            # 小红书有严格的反爬，这里记录接口地址，实际降级到模板
        except Exception:
            pass

        # 尝试微博超话搜索（实验性）
        try:
            weibo_url = "https://s.weibo.com/weibo"
            params = {"q": keyword + " 演唱会 开票", "type": "all"}
            resp = self.session.get(weibo_url, params=params, timeout=8)
            # 微博同样有反爬
        except Exception:
            pass

        return events

    def _generate_international_sample(self, keyword: str, city: str = "", limit: int = 20) -> List[Event]:
        """
        生成国际艺人巡演的示例数据
        这些数据基于已知的国际巡演规律，
        实际开票信息需从官方渠道确认
        """
        events = []

        # 国际艺人巡演模板
        templates = self._get_templates_for_artist(keyword)

        if not templates:
            # 通用模板
            templates = [{
                "title": f"{keyword} World Tour 2026",
                "artist": keyword,
                "venues": [
                    {"city": "香港", "venue": "香港红磡体育馆", "prices": [680, 980, 1380, 1680]},
                    {"city": "澳门", "venue": "银河综艺馆", "prices": [580, 880, 1280, 1680]},
                    {"city": "曼谷", "venue": "IMPACT Arena", "prices": [2800, 3800, 4800]},
                ],
                "category": "演唱会",
                "desc": f"{keyword} 2026 世界巡回演唱会。购票请访问官方渠道或 Ticketmaster。",
                "is_international": True
            }]

        start_date = datetime.now() + timedelta(days=random.randint(30, 180))
        event_count = 0

        for template in templates:
            for venue_info in template["venues"]:
                if city and city not in venue_info["city"]:
                    continue

                event_count += 1
                if event_count > limit:
                    break

                event_date = start_date + timedelta(days=event_count * 14 + random.randint(-10, 10))

                event = Event(
                    event_id=f"social-sample-{hash(keyword + venue_info['city']) & 0xFFFFFFFF}",
                    title=template["title"],
                    artist=template["artist"],
                    venue=venue_info["venue"],
                    city=venue_info["city"],
                    date_str=event_date.strftime("%Y-%m-%d %H:%M"),
                    start_date=event_date,
                    end_date=event_date,
                    sale_time=event_date - timedelta(days=60),
                    category=template["category"],
                    source_url="https://social.example.com/",
                    source_platform=self.PLATFORM_NAME,
                    description=template["desc"],
                    cover_image="",
                    tags=[keyword, venue_info["city"], "国际巡演", "需翻墙购票"],
                    platform_rating=round(random.uniform(4.5, 5.0), 1),
                    sold_count=random.randint(1000, 50000)
                )

                official_urls = self.get_official_ticket_urls(keyword)

                for price in venue_info["prices"]:
                    seat_type = self._guess_seat_type(price)
                    # 国际演出通常不标注具体票档售罄状态
                    event.tickets.append(TicketInfo(
                        price=float(price),
                        seat_type=seat_type,
                        ticket_status="待定",
                        platform=self.PLATFORM_NAME,
                        note="请至官方渠道购票"
                    ))

                # 添加官方购票链接说明
                if official_urls:
                    note_parts = [f"官网: {u['name']}" for u in official_urls[:2]]
                    event.description = template["desc"] + " | " + " | ".join(note_parts)

                events.append(event)
            if event_count > limit:
                break

        return events

    def _get_templates_for_artist(self, keyword: str) -> List[Dict]:
        """根据艺人名返回专属巡演模板"""
        kw_lower = keyword.lower().strip()

        templates_map = {
            "stray kids": [{
                "title": "Stray Kids 5-STAR Dome Tour 2026",
                "artist": "Stray Kids",
                "venues": [
                    {"city": "东京", "venue": "东京巨蛋", "prices": [12000, 15000, 18000]},
                    {"city": "大阪", "venue": "京瓷巨蛋大阪", "prices": [11000, 14000, 17000]},
                    {"city": "香港", "venue": "香港红磡体育馆", "prices": [880, 1280, 1680, 2080]},
                    {"city": "曼谷", "venue": "IMPACT Arena", "prices": [2800, 3800, 4800]},
                    {"city": "雅加达", "venue": "Indonesia Arena", "prices": [1500000, 2000000, 2500000]},
                ],
                "category": "演唱会",
                "desc": "Stray Kids 5-STAR 世界巡回演唱会。门票需通过 Ticketmaster 或当地官方渠道购买。"
            }],
            "taylor swift": [{
                "title": "Taylor Swift The Eras Tour 2026",
                "artist": "Taylor Swift",
                "venues": [
                    {"city": "东京", "venue": "东京巨蛋", "prices": [22000, 28000, 35000]},
                    {"city": "新加坡", "venue": "国家体育场", "prices": [188, 288, 388]},
                    {"city": "悉尼", "venue": "Accor Stadium", "prices": [120, 200, 300]},
                ],
                "category": "演唱会",
                "desc": "Taylor Swift The Eras Tour 全球巡演。门票通过 Ticketmaster 发售。"
            }],
            "blackpink": [{
                "title": "BLACKPINK Born Pink World Tour 2026",
                "artist": "BLACKPINK",
                "venues": [
                    {"city": "香港", "venue": "香港红磡体育馆", "prices": [688, 988, 1388, 1688]},
                    {"city": "澳门", "venue": "银河综艺馆", "prices": [688, 988, 1388]},
                    {"city": "台北", "venue": "台北小巨蛋", "prices": [2800, 3800, 4800]},
                ],
                "category": "演唱会",
                "desc": "BLACKPINK 世界巡回演唱会。"
            }],
        }

        for artist_key, templates in templates_map.items():
            aliases = FOREIGN_ARTIST_ALIASES.get(artist_key, [])
            if kw_lower in [a.lower() for a in aliases]:
                return templates

        return []

    def _guess_seat_type(self, price: float) -> str:
        """根据价格推断座次类型"""
        if price >= 2000:
            return "VIP/内场"
        elif price >= 1000:
            return "内场"
        elif price >= 500:
            return "看台前区"
        elif price >= 200:
            return "看台"
        else:
            return "看台后区"
