"""
SQLite 数据库管理模块 - 方案 C：混合策略
功能：演出资讯聚合 + 用户关注 + 半自动票价 + 开票提醒
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

from .models import Event, TicketInfo, PriceHistory, WatchItem


class Database:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "data", "piaoduoduo.db"
            )
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
        self._migrate_db()  # 确保旧数据能迁移到新结构

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    artist TEXT,
                    venue TEXT,
                    city TEXT,
                    date_str TEXT,
                    start_date TEXT,
                    end_date TEXT,
                    sale_time TEXT,
                    category TEXT,
                    source_url TEXT,
                    source_platform TEXT,
                    description TEXT,
                    cover_image TEXT,
                    tags TEXT,
                    platform_rating REAL DEFAULT 0.0,
                    sold_count INTEGER DEFAULT 0,
                    crawl_time TEXT,
                    is_watching INTEGER DEFAULT 0,
                    user_notes TEXT DEFAULT '',
                    purchase_priority INTEGER DEFAULT 0
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tickets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL,
                    price REAL NOT NULL,
                    seat_type TEXT,
                    ticket_status TEXT,
                    platform TEXT,
                    ticket_id TEXT,
                    note TEXT,
                    crawl_time TEXT,
                    is_user_edited INTEGER DEFAULT 0,
                    FOREIGN KEY (event_id) REFERENCES events(event_id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT,
                    title TEXT,
                    platform TEXT,
                    seat_type TEXT,
                    price REAL,
                    ticket_status TEXT,
                    record_time TEXT
                )
            ''')

            # 方案 C：关注列表（按具体演出，不是关键词）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS watchlist (
                    event_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    artist TEXT,
                    city TEXT,
                    venue TEXT,
                    date_str TEXT,
                    sale_time TEXT,
                    min_price REAL DEFAULT 0,
                    user_notes TEXT DEFAULT '',
                    priority INTEGER DEFAULT 0,
                    add_time TEXT,
                    is_reminded INTEGER DEFAULT 0
                )
            ''')

            conn.commit()

    def _migrate_db(self):
        """数据库迁移：检测旧表结构并重建不兼容的表"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            
            # 检测 events 表是否有新字段
            try:
                cursor.execute("SELECT is_watching FROM events LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE events ADD COLUMN is_watching INTEGER DEFAULT 0")
                cursor.execute("ALTER TABLE events ADD COLUMN user_notes TEXT DEFAULT ''")
                cursor.execute("ALTER TABLE events ADD COLUMN purchase_priority INTEGER DEFAULT 0")
            
            # 检测 tickets 表
            try:
                cursor.execute("SELECT is_user_edited FROM tickets LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE tickets ADD COLUMN is_user_edited INTEGER DEFAULT 0")
            
            # 检测 watchlist 表结构（方案 C 的重大变更）
            try:
                cursor.execute("SELECT event_id, title, user_notes, priority FROM watchlist LIMIT 1")
            except sqlite3.OperationalError:
                # 旧表结构不兼容，重建为新表（保留新字段）
                try:
                    cursor.execute("DROP TABLE watchlist")
                except sqlite3.OperationalError:
                    pass
                cursor.execute('''
                    CREATE TABLE watchlist (
                        event_id TEXT PRIMARY KEY,
                        title TEXT NOT NULL,
                        artist TEXT,
                        city TEXT,
                        venue TEXT,
                        date_str TEXT,
                        sale_time TEXT,
                        min_price REAL DEFAULT 0,
                        user_notes TEXT DEFAULT '',
                        priority INTEGER DEFAULT 0,
                        add_time TEXT,
                        is_reminded INTEGER DEFAULT 0
                    )
                ''')
            
            conn.commit()

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    # ============== 演出活动操作 ==============

    def save_event(self, event: Event):
        """保存或更新一条演出活动"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT event_id FROM events WHERE event_id = ?", (event.event_id,))
            exists = cursor.fetchone()

            if exists:
                cursor.execute('''
                    UPDATE events SET
                        title=?, artist=?, venue=?, city=?, date_str=?,
                        start_date=?, end_date=?, sale_time=?, category=?,
                        source_url=?, source_platform=?, description=?,
                        cover_image=?, tags=?, platform_rating=?, sold_count=?, crawl_time=?
                    WHERE event_id=?
                ''', (
                    event.title, event.artist, event.venue, event.city, event.date_str,
                    event.start_date.isoformat() if event.start_date else None,
                    event.end_date.isoformat() if event.end_date else None,
                    event.sale_time.isoformat() if event.sale_time else None,
                    event.category, event.source_url, event.source_platform,
                    event.description, event.cover_image,
                    json.dumps(event.tags, ensure_ascii=False),
                    event.platform_rating, event.sold_count,
                    event.crawl_time.isoformat(), event.event_id
                ))
            else:
                cursor.execute('''
                    INSERT INTO events (
                        event_id, title, artist, venue, city, date_str,
                        start_date, end_date, sale_time, category,
                        source_url, source_platform, description, cover_image,
                        tags, platform_rating, sold_count, crawl_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.event_id, event.title, event.artist, event.venue, event.city, event.date_str,
                    event.start_date.isoformat() if event.start_date else None,
                    event.end_date.isoformat() if event.end_date else None,
                    event.sale_time.isoformat() if event.sale_time else None,
                    event.category, event.source_url, event.source_platform,
                    event.description, event.cover_image,
                    json.dumps(event.tags, ensure_ascii=False),
                    event.platform_rating, event.sold_count,
                    event.crawl_time.isoformat()
                ))

            # 只在票价为空时插入系统模板，保留用户编辑过的内容
            cursor.execute("SELECT COUNT(*) FROM tickets WHERE event_id = ?", (event.event_id,))
            ticket_count = cursor.fetchone()[0]

            if ticket_count == 0:
                for ticket in event.tickets:
                    cursor.execute('''
                        INSERT INTO tickets (event_id, price, seat_type, ticket_status, platform, ticket_id, note, crawl_time, is_user_edited)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        event.event_id, ticket.price, ticket.seat_type, ticket.ticket_status,
                        ticket.platform, ticket.ticket_id, ticket.note,
                        event.crawl_time.isoformat(), 0
                    ))
            else:
                # 有用户编辑过的票价，保留不动
                pass

            conn.commit()

    def save_events(self, events: List[Event]):
        for event in events:
            self.save_event(event)

    def get_events(self, keyword: str = "", city: str = "", category: str = "",
                   platform: str = "", limit: int = 100) -> List[Event]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM events WHERE 1=1"
            params = []

            if keyword:
                query += " AND (title LIKE ? OR artist LIKE ? OR venue LIKE ?)"
                like_keyword = f"%{keyword}%"
                params.extend([like_keyword, like_keyword, like_keyword])

            if city:
                query += " AND city LIKE ?"
                params.append(f"%{city}%")

            if category:
                query += " AND category LIKE ?"
                params.append(f"%{category}%")

            if platform:
                query += " AND source_platform = ?"
                params.append(platform)

            query += " ORDER BY start_date ASC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            return self._rows_to_events(cursor, rows)

    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            if row:
                events = self._rows_to_events(cursor, [row])
                return events[0] if events else None
            return None

    def _rows_to_events(self, cursor, rows) -> List[Event]:
        events = []
        for row in rows:
            # 将 sqlite3.Row 转为 dict，便于使用 .get()
            row_dict = dict(row)
            
            event = Event(
                event_id=row_dict['event_id'],
                title=row_dict['title'],
                artist=row_dict.get('artist') or "",
                venue=row_dict.get('venue') or "",
                city=row_dict.get('city') or "",
                date_str=row_dict.get('date_str') or "",
                category=row_dict.get('category') or "",
                source_url=row_dict.get('source_url') or "",
                source_platform=row_dict.get('source_platform') or "",
                description=row_dict.get('description') or "",
                cover_image=row_dict.get('cover_image') or "",
                tags=json.loads(row_dict['tags']) if row_dict.get('tags') else [],
                platform_rating=row_dict.get('platform_rating') or 0.0,
                sold_count=row_dict.get('sold_count') or 0,
                is_watching=bool(row_dict.get('is_watching', 0)),
                user_notes=row_dict.get('user_notes', '') or "",
                purchase_priority=row_dict.get('purchase_priority', 0) or 0
            )
            if row_dict.get('start_date'):
                event.start_date = datetime.fromisoformat(row_dict['start_date'])
            if row_dict.get('end_date'):
                event.end_date = datetime.fromisoformat(row_dict['end_date'])
            if row_dict.get('sale_time'):
                event.sale_time = datetime.fromisoformat(row_dict['sale_time'])
            if row_dict.get('crawl_time'):
                event.crawl_time = datetime.fromisoformat(row_dict['crawl_time'])

            cursor.execute("SELECT * FROM tickets WHERE event_id = ?", (event.event_id,))
            ticket_rows = cursor.fetchall()
            for tr in ticket_rows:
                tr_dict = dict(tr)
                t = TicketInfo(
                    price=tr_dict['price'],
                    seat_type=tr_dict.get('seat_type') or "",
                    ticket_status=tr_dict.get('ticket_status') or "",
                    platform=tr_dict.get('platform') or "",
                    ticket_id=tr_dict.get('ticket_id') or "",
                    note=tr_dict.get('note') or "",
                    is_user_edited=bool(tr_dict.get('is_user_edited', 0))
                )
                event.tickets.append(t)
            events.append(event)
        return events

    # ============== 票价编辑（半自动模式） ==============

    def update_tickets(self, event_id: str, tickets_data: List[Dict]):
        """
        用户手动编辑票价，覆盖系统生成的数据
        tickets_data 格式：
        [
            {"price": 480, "seat_type": "看台", "ticket_status": "在售", "platform": "大麦网"},
            ...
        ]
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            # 删除旧票价
            cursor.execute("DELETE FROM tickets WHERE event_id = ?", (event_id,))
            # 插入用户编辑的内容
            for t in tickets_data:
                cursor.execute('''
                    INSERT INTO tickets (event_id, price, seat_type, ticket_status, platform, crawl_time, is_user_edited)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event_id,
                    t.get('price', 0),
                    t.get('seat_type', ''),
                    t.get('ticket_status', '在售'),
                    t.get('platform', ''),
                    datetime.now().isoformat(),
                    1  # 用户编辑
                ))
            conn.commit()

    def get_tickets(self, event_id: str) -> List[TicketInfo]:
        """获取某演出的所有票档信息"""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tickets WHERE event_id = ? ORDER BY price ASC", (event_id,))
            rows = cursor.fetchall()
            result = []
            for r in rows:
                r_dict = dict(r)
                result.append(TicketInfo(
                    price=r_dict['price'],
                    seat_type=r_dict.get('seat_type') or "",
                    ticket_status=r_dict.get('ticket_status') or "",
                    platform=r_dict.get('platform') or "",
                    ticket_id=r_dict.get('ticket_id') or "",
                    note=r_dict.get('note') or "",
                    is_user_edited=bool(r_dict.get('is_user_edited', 0))
                ))
            return result

    # ============== 价格历史操作 ==============

    def get_price_history(self, event_id: str = "", title: str = "") -> List[PriceHistory]:
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if event_id:
                cursor.execute("SELECT * FROM price_history WHERE event_id = ? ORDER BY record_time", (event_id,))
            elif title:
                cursor.execute("SELECT * FROM price_history WHERE title LIKE ? ORDER BY record_time", (f"%{title}%",))
            else:
                return []
            rows = cursor.fetchall()
            return [PriceHistory(
                event_id=r['event_id'] or "",
                title=r['title'] or "",
                platform=r['platform'] or "",
                seat_type=r['seat_type'] or "",
                price=r['price'] or 0.0,
                ticket_status=r['ticket_status'] or "",
                record_time=datetime.fromisoformat(r['record_time']) if r['record_time'] else datetime.now()
            ) for r in rows]

    # ============== 关注列表操作（方案 C 核心功能） ==============

    def add_to_watchlist(self, event: Event, user_notes: str = "", priority: int = 0):
        """
        将某场演出加入关注列表
        同时更新 events 表中的 is_watching 标记
        """
        with self._get_conn() as conn:
            cursor = conn.cursor()
            min_price = event.min_price() if event.tickets else 0.0
            sale_time_iso = event.sale_time.isoformat() if event.sale_time else ""

            cursor.execute('''
                INSERT OR REPLACE INTO watchlist
                (event_id, title, artist, city, venue, date_str, sale_time, min_price, user_notes, priority, add_time, is_reminded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id, event.title, event.artist, event.city, event.venue,
                event.date_str, sale_time_iso, min_price, user_notes, priority,
                datetime.now().isoformat(), 0
            ))
            cursor.execute("UPDATE events SET is_watching = 1, user_notes = ?, purchase_priority = ? WHERE event_id = ?",
                         (user_notes, priority, event.event_id))
            conn.commit()

    def remove_from_watchlist(self, event_id: str):
        """从关注列表移除"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watchlist WHERE event_id = ?", (event_id,))
            cursor.execute("UPDATE events SET is_watching = 0 WHERE event_id = ?", (event_id,))
            conn.commit()

    def get_watchlist(self) -> List[WatchItem]:
        """获取关注列表，按开票时间排序（即将开票的在前面）"""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM watchlist ORDER BY priority DESC, sale_time ASC")
            rows = cursor.fetchall()
            items = []
            for row in rows:
                row_dict = dict(row)
                item = WatchItem(
                    event_id=row_dict['event_id'],
                    title=row_dict['title'],
                    artist=row_dict.get('artist') or "",
                    city=row_dict.get('city') or "",
                    venue=row_dict.get('venue') or "",
                    date_str=row_dict.get('date_str') or "",
                    sale_time=row_dict.get('sale_time') or "",
                    min_price=row_dict.get('min_price') or 0.0,
                    user_notes=row_dict.get('user_notes', '') or "",
                    priority=row_dict.get('priority', 0) or 0,
                    add_time=datetime.fromisoformat(row_dict['add_time']) if row_dict.get('add_time') else datetime.now(),
                    is_reminded=bool(row_dict.get('is_reminded', 0))
                )
                items.append(item)
            return items

    def update_watch_notes(self, event_id: str, user_notes: str, priority: int = 0):
        """更新关注项目的备注和优先级"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE watchlist SET user_notes = ?, priority = ? WHERE event_id = ?",
                         (user_notes, priority, event_id))
            cursor.execute("UPDATE events SET user_notes = ?, purchase_priority = ? WHERE event_id = ?",
                         (user_notes, priority, event_id))
            conn.commit()

    # ============== 开票提醒功能 ==============

    def get_upcoming_sales(self, days_ahead: int = 7) -> List[WatchItem]:
        """
        获取未来 N 天内即将开票的演出
        用于：页面顶部醒目提醒、开票日历
        """
        watchlist = self.get_watchlist()
        now = datetime.now()
        threshold = now + timedelta(days=days_ahead)
        upcoming = []

        for item in watchlist:
            if not item.sale_time:
                continue
            try:
                sale_dt = datetime.fromisoformat(item.sale_time)
                if now <= sale_dt <= threshold:
                    upcoming.append(item)
            except Exception:
                continue
        return upcoming

    def get_sale_calendar(self, days_ahead: int = 30) -> Dict[str, List[WatchItem]]:
        """
        生成未来 N 天的开票日历
        返回格式：{'2026-07-01': [WatchItem1, WatchItem2], ...}
        """
        watchlist = self.get_watchlist()
        now = datetime.now()
        calendar = {}

        for item in watchlist:
            if not item.sale_time:
                continue
            try:
                sale_dt = datetime.fromisoformat(item.sale_time)
                if sale_dt >= now:
                    date_key = sale_dt.strftime('%Y-%m-%d')
                    if date_key not in calendar:
                        calendar[date_key] = []
                    calendar[date_key].append(item)
            except Exception:
                continue
        return calendar

    def is_in_watchlist(self, event_id: str) -> bool:
        """检查某演出是否在关注列表中"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM watchlist WHERE event_id = ?", (event_id,))
            return cursor.fetchone() is not None

    # ============== 统计信息 ==============

    def get_stats(self) -> Dict[str, Any]:
        with self._get_conn() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM events")
            event_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tickets")
            ticket_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM watchlist")
            watchlist_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT source_platform) FROM events")
            platform_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT city) FROM events")
            city_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM price_history")
            history_count = cursor.fetchone()[0]

            return {
                "event_count": event_count,
                "ticket_count": ticket_count,
                "watchlist_count": watchlist_count,
                "platform_count": platform_count,
                "city_count": city_count,
                "history_count": history_count
            }

    def clear_all(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tickets")
            cursor.execute("DELETE FROM events")
            cursor.execute("DELETE FROM price_history")
            cursor.execute("DELETE FROM watchlist")
            conn.commit()
