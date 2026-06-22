"""
数据采集模块 - 支持从各大卖票平台采集演出信息与票价数据

平台支持：
- damai: 大麦网 (damai.cn) — 国内主流售票平台 (人民币 CNY)
- maoyan: 猫眼演出 (show.maoyan.com) — 国内娱乐售票平台 (人民币 CNY)
- piaoxingqiu: 票星球 (piaoxingqiu.com) — 新兴售票平台 (人民币 CNY)
- ticketmaster: Ticketmaster (ticketmaster.com) — 国际票务平台 (多币种)
- social_media: 社交媒体/国际艺人 — 微博、小红书及境外购票渠道
"""

from .damai import DamaiCollector
from .maoyan import MaoyanCollector
from .piaoxingqiu import PiaoxingqiuCollector
from .ticketmaster import TicketmasterCollector
from .social_media import SocialMediaCollector

__all__ = [
    "DamaiCollector",
    "MaoyanCollector",
    "PiaoxingqiuCollector",
    "TicketmasterCollector",
    "SocialMediaCollector",
]
