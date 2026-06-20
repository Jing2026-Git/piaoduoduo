"""
SQLite 数据库管理模块 - 管理演出数据、票价历史、用户关注等
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

from .models import Event, TicketInfo, PriceHistory


class Database:
    def __init__(self, db_path: str = None):
        """初始化数据库"""
        if db_path is None:
            # 默认放在项目 data 目录下
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "piaoduoduo.db")

        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 演出活动表
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
                    crawl_time TEXT
                )
            ''')

            # 票价信息表
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
                    FOREIGN KEY (event_id) REFERENCES events(event_id)
                )
            ''')

            # 价格历史记录表 - 用于趋势分析
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

            # 用户关注表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT NOT NULL,
                    artist TEXT,
                    city TEXT,
                    created_time TEXT
                )
            ''')

            conn.commit()

    @contextmanager
    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    # ---------- 演出活动操作 ----------

    def save_event(self, event: Event):
        """保存或更新一条演出活动"""
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # 先检查是否已存在
            cursor.execute("SELECT event_id FROM events WHERE event_id = ?", (event.event_id,))
            exists = cursor.fetchone()

            if exists:
                # 更新
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
                # 插入新记录
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

            # 删除旧的票价信息，重新插入
            cursor.execute("DELETE FROM tickets WHERE event_id = ?", (event.event_id,))
            for ticket in event.tickets:
                cursor.execute('''
                    INSERT INTO tickets (event_id, price, seat_type, ticket_status, platform, ticket_id, note, crawl_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.event_id, ticket.price, ticket.seat_type, ticket.ticket_status,
                    ticket.platform, ticket.ticket_id, ticket.note,
                    event.crawl_time.isoformat()
                ))

            # 记录价格历史
            for ticket in event.tickets:
                cursor.execute('''
                    INSERT INTO price_history (event_id, title, platform, seat_type, price, ticket_status, record_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event.event_id, event.title, ticket.platform, ticket.seat_type,
                    ticket.price, ticket.ticket_status, datetime.now().isoformat()
                ))

            conn.commit()

    def save_events(self, events: List[Event]):
        """批量保存演出活动"""
        for event in events:
            self.save_event(event)

    def get_events(self, keyword: str = "", city: str = "", category: str = "",
                   platform: str = "", limit: int = 100) -> List[Event]:
        """查询演出活动 - 支持多条件过滤"""
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

            events = []
            for row in rows:
                event = Event(
                    event_id=row['event_id'],
                    title=row['title'],
                    artist=row['artist'] or "",
                    venue=row['venue'] or "",
                    city=row['city'] or "",
                    date_str=row['date_str'] or "",
                    category=row['category'] or "",
                    source_url=row['source_url'] or "",
                    source_platform=row['source_platform'] or "",
                    description=row['description'] or "",
                    cover_image=row['cover_image'] or "",
                    tags=json.loads(row['tags']) if row['tags'] else [],
                    platform_rating=row['platform_rating'] or 0.0,
                    sold_count=row['sold_count'] or 0
                )
                if row['start_date']:
                    event.start_date = datetime.fromisoformat(row['start_date'])
                if row['end_date']:
                    event.end_date = datetime.fromisoformat(row['end_date'])
                if row['sale_time']:
                    event.sale_time = datetime.fromisoformat(row['sale_time'])
                if row['crawl_time']:
                    event.crawl_time = datetime.fromisoformat(row['crawl_time'])

                # 查询该活动的票价信息
                cursor.execute("SELECT * FROM tickets WHERE event_id = ?", (event.event_id,))
                ticket_rows = cursor.fetchall()
                for tr in ticket_rows:
                    event.tickets.append(TicketInfo(
                        price=tr['price'],
                        seat_type=tr['seat_type'] or "",
                        ticket_status=tr['ticket_status'] or "",
                        platform=tr['platform'] or "",
                        ticket_id=tr['ticket_id'] or "",
                        note=tr['note'] or ""
                    ))
                events.append(event)

            return events

    # ---------- 价格历史操作 ----------

    def get_price_history(self, event_id: str = "", title: str = "") -> List[PriceHistory]:
        """获取指定演出的价格历史"""
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
            history = []
            for row in rows:
                history.append(PriceHistory(
                    event_id=row['event_id'] or "",
                    title=row['title'] or "",
                    platform=row['platform'] or "",
                    seat_type=row['seat_type'] or "",
                    price=row['price'] or 0.0,
                    ticket_status=row['ticket_status'] or "",
                    record_time=datetime.fromisoformat(row['record_time']) if row['record_time'] else datetime.now()
                ))
            return history

    # ---------- 关注列表操作 ----------

    def add_watch(self, keyword: str = "", artist: str = "", city: str = ""):
        """添加关注关键词"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO watchlist (keyword, artist, city, created_time)
                VALUES (?, ?, ?, ?)
            ''', (keyword, artist, city, datetime.now().isoformat()))
            conn.commit()

    def get_watchlist(self) -> List[Dict]:
        """获取关注列表"""
        with self._get_conn() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM watchlist ORDER BY created_time DESC")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def clear_watchlist(self):
        """清空关注列表"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watchlist")
            conn.commit()

    # ---------- 统计信息 ----------

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events")
            event_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM tickets")
            ticket_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT source_platform) FROM events")
            platform_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT city) FROM events")
            city_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM price_history")
            history_count = cursor.fetchone()[0]

            return {
                "event_count": event_count,
                "ticket_count": ticket_count,
                "platform_count": platform_count,
                "city_count": city_count,
                "history_count": history_count
            }

    def clear_all(self):
        """清空所有数据（用于演示/测试）"""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tickets")
            cursor.execute("DELETE FROM events")
            cursor.execute("DELETE FROM price_history")
            conn.commit()
