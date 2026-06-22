"""
数据模型 - 定义演出活动、票价等核心数据结构
方案 C：混合策略 - 资讯聚合 + 用户关注 + 半自动票价 + 开票提醒
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime


@dataclass
class TicketInfo:
    """票档信息（支持用户手动编辑）"""
    price: float          # 票价（元）
    seat_type: str        # 座次类型（如：看台、内场、VIP等）
    ticket_status: str    # 售票状态（在售/已售罄/即将开抢/暂停销售/未开售）
    platform: str         # 平台名称
    ticket_id: str = ""   # 平台内部票ID
    note: str = ""        # 备注信息（如：抢购技巧、平台评价）
    is_user_edited: bool = False  # 是否由用户手动编辑过

    def to_dict(self) -> Dict:
        return {
            "price": self.price,
            "seat_type": self.seat_type,
            "ticket_status": self.ticket_status,
            "platform": self.platform,
            "ticket_id": self.ticket_id,
            "note": self.note,
            "is_user_edited": self.is_user_edited
        }


@dataclass
class Event:
    """演出活动信息"""
    event_id: str                      # 活动唯一ID（由系统生成）
    title: str                         # 活动标题
    artist: str = ""                   # 艺人/明星
    venue: str = ""                    # 场馆
    city: str = ""                     # 城市
    date_str: str = ""                 # 演出日期（原始字符串）
    start_date: Optional[datetime] = None   # 开始时间
    end_date: Optional[datetime] = None     # 结束时间
    sale_time: Optional[datetime] = None     # 开票时间
    category: str = ""                 # 类型（演唱会/音乐会/音乐剧/话剧/漫展等）
    source_url: str = ""               # 原始链接
    source_platform: str = ""          # 来源平台
    tickets: List[TicketInfo] = field(default_factory=list)   # 各票档信息
    description: str = ""              # 活动简介
    cover_image: str = ""              # 封面图URL
    tags: List[str] = field(default_factory=list)
    platform_rating: float = 0.0       # 平台评分
    sold_count: int = 0                # 已售数量
    crawl_time: datetime = field(default_factory=datetime.now)  # 采集时间
    # 方案 C 新增字段
    is_watching: bool = False          # 用户是否关注
    user_notes: str = ""               # 用户备注（如：我想抢看台、预算¥800）
    purchase_priority: int = 0         # 购买优先级（0-10，用户手动设置）

    def min_price(self) -> float:
        """获取最低票价"""
        if not self.tickets:
            return 0.0
        return min(t.price for t in self.tickets)

    def max_price(self) -> float:
        """获取最高票价"""
        if not self.tickets:
            return 0.0
        return max(t.price for t in self.tickets)

    def days_to_sale(self) -> int:
        """距离开票还有多少天（负数表示已开票）"""
        if self.sale_time:
            delta = self.sale_time - datetime.now()
            return delta.days
        return 999

    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "artist": self.artist,
            "venue": self.venue,
            "city": self.city,
            "date_str": self.date_str,
            "start_date": self.start_date.isoformat() if self.start_date else "",
            "end_date": self.end_date.isoformat() if self.end_date else "",
            "sale_time": self.sale_time.isoformat() if self.sale_time else "",
            "category": self.category,
            "source_url": self.source_url,
            "source_platform": self.source_platform,
            "description": self.description,
            "cover_image": self.cover_image,
            "tags": self.tags,
            "platform_rating": self.platform_rating,
            "sold_count": self.sold_count,
            "tickets": [t.to_dict() for t in self.tickets],
            "min_price": self.min_price(),
            "max_price": self.max_price(),
            "crawl_time": self.crawl_time.isoformat(),
            "is_watching": self.is_watching,
            "user_notes": self.user_notes,
            "purchase_priority": self.purchase_priority,
            "days_to_sale": self.days_to_sale()
        }


@dataclass
class PriceHistory:
    """票价历史记录 - 用于价格趋势分析"""
    event_id: str
    title: str
    platform: str
    seat_type: str
    price: float
    ticket_status: str
    record_time: datetime

    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "platform": self.platform,
            "seat_type": self.seat_type,
            "price": self.price,
            "ticket_status": self.ticket_status,
            "record_time": self.record_time.isoformat()
        }


@dataclass
class WatchItem:
    """关注列表中的演出（方案 C 核心功能）"""
    event_id: str           # 演出ID
    title: str             # 演出标题
    artist: str            # 艺人
    city: str              # 城市
    venue: str            # 场馆
    date_str: str          # 演出日期
    sale_time: str        # 开票时间
    min_price: float      # 最低票价
    user_notes: str       # 用户备注
    priority: int         # 优先级
    add_time: datetime    # 加入关注时间
    is_reminded: bool = False  # 是否已提醒

    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "title": self.title,
            "artist": self.artist,
            "city": self.city,
            "venue": self.venue,
            "date_str": self.date_str,
            "sale_time": self.sale_time,
            "min_price": self.min_price,
            "user_notes": self.user_notes,
            "priority": self.priority,
            "add_time": self.add_time.isoformat(),
            "is_reminded": self.is_reminded
        }


@dataclass
class ComparisonResult:
    """比价结果 - 同一场演出不同平台的票价比对"""
    event_title: str                    # 演出标题
    artist: str                         # 艺人
    city: str                           # 城市
    venue: str                          # 场馆
    date_str: str                       # 日期
    events: List[Event] = field(default_factory=list)  # 各平台采集到的此演出信息
    min_price: float = 0.0              # 跨平台最低价
    min_price_platform: str = ""        # 最低价平台
    max_price: float = 0.0              # 跨平台最高价
    price_range: str = ""               # 价格范围描述
    recommendation: str = ""            # 性价比推荐
    platforms_with_data: List[str] = field(default_factory=list)  # 有数据的平台

    def to_dict(self) -> Dict:
        return {
            "event_title": self.event_title,
            "artist": self.artist,
            "city": self.city,
            "venue": self.venue,
            "date_str": self.date_str,
            "min_price": self.min_price,
            "min_price_platform": self.min_price_platform,
            "max_price": self.max_price,
            "price_range": self.price_range,
            "recommendation": self.recommendation,
            "platforms_with_data": self.platforms_with_data,
            "events": [e.to_dict() for e in self.events]
        }
