"""
比价分析模块
功能: 跨平台票价对比、性价比推荐、价格趋势分析
"""

from typing import List, Dict, Optional, Tuple
from collections import defaultdict
from datetime import datetime

from .models import Event, ComparisonResult


class PriceComparator:
    """票价比价分析器"""

    # 性价比评分权重
    PRICE_WEIGHT = 0.4
    SEAT_WEIGHT = 0.3
    AVAILABILITY_WEIGHT = 0.2
    RATING_WEIGHT = 0.1

    def compare(self, events: List[Event]) -> List[ComparisonResult]:
        """
        对演出列表进行比价分析
        按同一场演出（标题+城市+场馆）分组，对比各平台票价
        """
        # 按演出分组
        event_groups = self._group_events(events)

        results = []
        for group_key, group in event_groups.items():
            result = self._analyze_group(group)
            results.append(result)

        # 按性价比从高到低排序
        results.sort(key=lambda r: r.min_price if r.min_price > 0 else float('inf'))
        return results

    def get_min_price_platform(self, event: Event) -> Tuple[float, str, str]:
        """
        获取某场演出的最低票价及其平台和座次
        返回: (最低价格, 平台名称, 座次类型)
        """
        if not event.tickets:
            return (0.0, "", "")

        # 只考虑在售的票
        available_tickets = [t for t in event.tickets if "售罄" not in t.ticket_status]

        if not available_tickets:
            # 如果全部售罄，返回最低价格的信息
            min_ticket = min(event.tickets, key=lambda t: t.price)
            return (min_ticket.price, min_ticket.platform, min_ticket.seat_type)

        min_ticket = min(available_tickets, key=lambda t: t.price)
        return (min_ticket.price, min_ticket.platform, min_ticket.seat_type)

    def get_price_analysis(self, event: Event) -> Dict:
        """获取单场演出的票价详细分析"""
        if not event.tickets:
            return {}

        # 按平台分组
        platform_prices = defaultdict(list)
        for ticket in event.tickets:
            platform_prices[ticket.platform].append(ticket)

        # 分析各平台
        analysis = {
            "title": event.title,
            "city": event.city,
            "venue": event.venue,
            "date": event.date_str,
            "platforms": []
        }

        all_prices = []
        for platform, tickets in platform_prices.items():
            prices = [t.price for t in tickets]
            available = sum(1 for t in tickets if "售罄" not in t.ticket_status)
            platform_info = {
                "name": platform,
                "min_price": min(prices),
                "max_price": max(prices),
                "avg_price": sum(prices) / len(prices),
                "ticket_count": len(tickets),
                "available_count": available,
                "seat_types": list(set(t.seat_type for t in tickets))
            }
            analysis["platforms"].append(platform_info)
            all_prices.extend(prices)

        # 整体统计
        if all_prices:
            analysis["overall"] = {
                "min_price": min(all_prices),
                "max_price": max(all_prices),
                "avg_price": sum(all_prices) / len(all_prices),
                "total_tickets": len(all_prices),
                "price_range": self._format_price_range(min(all_prices), max(all_prices))
            }

        # 找最佳性价比
        if event.tickets:
            best = self._find_best_value_ticket(event)
            analysis["best_value"] = best

        return analysis

    def _group_events(self, events: List[Event]) -> Dict[str, List[Event]]:
        """按演出分组（标题核心词 + 城市）"""
        groups = defaultdict(list)
        for event in events:
            # 提取标题核心词
            title_core = event.title.split("演唱会")[0].split("LIVE")[0].strip()
            if not title_core:
                title_core = event.title[:10]

            key = f"{title_core}|{event.city}"
            groups[key].append(event)
        return groups

    def _analyze_group(self, group: List[Event]) -> ComparisonResult:
        """分析一组同一场演出"""
        # 合并所有票价
        all_tickets = []
        for event in group:
            all_tickets.extend(event.tickets)

        if not all_tickets:
            return ComparisonResult(
                event_title=group[0].title if group else "",
                artist=group[0].artist if group else "",
                city=group[0].city if group else "",
                venue=group[0].venue if group else "",
                date_str=group[0].date_str if group else "",
                events=group,
                min_price=0.0,
                max_price=0.0,
                platforms_with_data=[]
            )

        # 只看在售票
        available_tickets = [t for t in all_tickets if "售罄" not in t.ticket_status]

        # 最低价
        if available_tickets:
            min_ticket = min(available_tickets, key=lambda t: t.price)
            min_price = min_ticket.price
            min_platform = min_ticket.platform
        else:
            min_ticket = min(all_tickets, key=lambda t: t.price)
            min_price = min_ticket.price
            min_platform = min_ticket.platform

        max_price = max(t.price for t in all_tickets)

        # 有数据的平台
        platforms = list(set(t.platform for t in all_tickets))

        # 性价比推荐
        recommendation = self._generate_recommendation(group, all_tickets, min_price, max_price)

        result = ComparisonResult(
            event_title=group[0].title,
            artist=group[0].artist,
            city=group[0].city,
            venue=group[0].venue,
            date_str=group[0].date_str,
            events=group,
            min_price=min_price,
            min_price_platform=min_platform,
            max_price=max_price,
            price_range=self._format_price_range(min_price, max_price),
            recommendation=recommendation,
            platforms_with_data=platforms
        )
        return result

    def _generate_recommendation(self, events: List[Event],
                                 all_tickets,
                                 min_price: float,
                                 max_price: float) -> str:
        """生成性价比推荐文本"""
        if not all_tickets:
            return "暂无票价信息"

        # 找最低价在售票
        available = [t for t in all_tickets if "售罄" not in t.ticket_status]
        if not available:
            return "⚠️ 所有平台均已售罄，建议关注下次开票"

        min_ticket = min(available, key=lambda t: t.price)

        # 分析平台差异
        platform_prices = defaultdict(list)
        for t in all_tickets:
            if "售罄" not in t.ticket_status:
                platform_prices[t.platform].append(t.price)

        if len(platform_prices) <= 1:
            return f"✨ 目前只有 {list(platform_prices.keys())[0]} 有票，最低票价 ¥{int(min_ticket.price)}"

        # 对比各平台
        platform_summary = []
        for platform, prices in sorted(platform_prices.items(), key=lambda x: min(x[1])):
            platform_summary.append(f"{platform} ¥{int(min(prices))}起")

        # 找最佳性价比票
        best_value = self._find_best_value_ticket_list(all_tickets)

        rec = f"🏆 推荐: {min_ticket.platform} 平台，¥{int(min_ticket.price)} ({min_ticket.seat_type})"
        if best_value and best_value.get('price') != min_ticket.price:
            rec += f"\n   性价比之选: {best_value.get('platform')} ¥{int(best_value.get('price'))} ({best_value.get('seat_type')})"

        # 补充平台对比
        if len(platform_summary) > 1:
            rec += "\n   平台对比: " + " / ".join(platform_summary)

        return rec

    def _find_best_value_ticket(self, event: Event) -> Dict:
        """找最佳性价比票"""
        return self._find_best_value_ticket_list(event.tickets)

    def _find_best_value_ticket_list(self, tickets) -> Optional[Dict]:
        """从票列表中找最佳性价比票"""
        if not tickets:
            return None

        available = [t for t in tickets if "售罄" not in t.ticket_status]
        if not available:
            available = tickets

        if not available:
            return None

        # 简易性价比评分：(座次位置 + 价格适中度 + 平台评分)
        min_price = min(t.price for t in available)
        max_price = max(t.price for t in available)

        best_score = -1
        best_ticket = None

        for ticket in available:
            # 价格评分：价格越低越高（但不要过低，可能位置不好）
            if max_price > min_price:
                price_norm = (max_price - ticket.price) / (max_price - min_price)
            else:
                price_norm = 0.5

            # 座次评分（简单根据座次类型关键词）
            seat_score = 0.5
            if any(k in ticket.seat_type for k in ["VIP", "内场前排"]):
                seat_score = 1.0
            elif any(k in ticket.seat_type for k in ["内场", "看台前"]):
                seat_score = 0.8
            elif "看台" in ticket.seat_type:
                seat_score = 0.6
            else:
                seat_score = 0.4

            # 综合评分
            score = self.PRICE_WEIGHT * price_norm + self.SEAT_WEIGHT * seat_score + self.AVAILABILITY_WEIGHT * 0.8

            if score > best_score:
                best_score = score
                best_ticket = ticket

        if best_ticket:
            return {
                "price": int(best_ticket.price),
                "platform": best_ticket.platform,
                "seat_type": best_ticket.seat_type,
                "score": round(best_score, 2)
            }
        return None

    def _format_price_range(self, min_price: float, max_price: float) -> str:
        """格式化价格范围"""
        if min_price == max_price:
            return f"¥{int(min_price)}"
        return f"¥{int(min_price)} - ¥{int(max_price)}"

    # ---------- 趋势分析 ----------

    def analyze_price_trend(self, price_history: List) -> Dict:
        """分析票价历史趋势"""
        if not price_history:
            return {}

        # 按平台分组
        platform_data = defaultdict(list)
        for record in price_history:
            key = (getattr(record, 'platform', ''),
                   getattr(record, 'seat_type', ''))
            platform_data[key].append({
                'price': record.price,
                'time': getattr(record, 'record_time', datetime.now())
            })

        trend = {
            "total_records": len(price_history),
            "platforms": list(set(getattr(r, 'platform', '') for r in price_history)),
            "summary": []
        }

        # 每个平台的价格变化
        for (platform, seat), records in platform_data.items():
            if len(records) < 2:
                continue
            prices = [r['price'] for r in records]
            first_price = prices[0]
            last_price = prices[-1]
            change = ((last_price - first_price) / first_price) * 100 if first_price > 0 else 0

            trend["summary"].append({
                "platform": platform,
                "seat_type": seat,
                "first_price": first_price,
                "latest_price": last_price,
                "change_pct": round(change, 1),
                "trend": "上涨" if change > 0 else ("下降" if change < 0 else "持平"),
                "min_price": min(prices),
                "max_price": max(prices)
            })

        return trend

    # ---------- 导出格式 ----------

    def to_csv(self, results: List[ComparisonResult]) -> str:
        """导出为CSV格式"""
        lines = ["演出标题,艺人,城市,场馆,日期,最低票价,最低价平台,最高票价,价格范围,有票平台,推荐"]
        for r in results:
            title = r.event_title.replace(',', ' ')
            artist = r.artist.replace(',', ' ')
            city = r.city.replace(',', ' ')
            venue = r.venue.replace(',', ' ')
            date = r.date_str.replace(',', ' ')
            platforms = "/".join(r.platforms_with_data)
            rec = r.recommendation.replace('\n', ' ').replace(',', ' ')

            lines.append(f"{title},{artist},{city},{venue},{date},{int(r.min_price)},{r.min_price_platform},{int(r.max_price)},{r.price_range},{platforms},{rec}")
        return "\n".join(lines)

    def to_json(self, results: List[ComparisonResult]) -> str:
        """导出为JSON格式"""
        import json
        data = [r.to_dict() for r in results]
        return json.dumps(data, ensure_ascii=False, indent=2)
