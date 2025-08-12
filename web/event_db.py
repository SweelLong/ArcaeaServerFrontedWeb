import hashlib
import sqlite3
from datetime import datetime
import os

class DatabaseOperations:
    def __init__(self):
        '''类必备的函数...'''
        self.user_db_path = os.path.join(os.path.dirname(__file__), '../database/arcaea_database.db')
        self.event_db_path = os.path.join(os.path.dirname(__file__), 'event.db')
        self.init_event_database()
    
    def get_db_connection(self, db_path):
        """封装一个连接"""
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_event_database(self):
        """初始化表结构喵"""
        conn = self.get_db_connection(self.event_db_path)
        conn.execute('''
        CREATE TABLE IF NOT EXISTS contribution (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            time DATETIME NOT NULL,
            file_path TEXT NOT NULL,
            UNIQUE(user_id, name)
        )
        ''')
        conn.execute('''
        CREATE TABLE IF NOT EXISTS lottery (
            user_id INTEGER NOT NULL,
            draw_date TEXT NOT NULL,
            prize TEXT,
            draw_time DATETIME NOT NULL,
            PRIMARY KEY (user_id, draw_date)
        )
        ''')
        conn.execute('''
        CREATE TABLE IF NOT EXISTS prize_status (
            prize_id TEXT PRIMARY KEY,
            prize_name TEXT NOT NULL,
            is_claimed INTEGER DEFAULT 0,  -- 0:未被领取, 1:已被领取
            claimed_by INTEGER,  -- 领取者user_id
            claimed_time DATETIME
        )
        ''')
        limited_prizes = [
            ("badge", "sense of wonder吧唧"),
            ("streamer", "克丽斯腾流麻"),
            ("stub", "克丽斯腾票根")
        ]
        for pid, pname in limited_prizes:
            conn.execute('''
            INSERT OR IGNORE INTO prize_status (prize_id, prize_name) 
            VALUES (?, ?)
            ''', (pid, pname))
        
        conn.commit()
        conn.close()
    
    def verify_user(self, username, password):
        """密码哈希加密来匹配账号信息"""
        conn = self.get_db_connection(self.user_db_path)
        user = conn.execute('SELECT * FROM user WHERE name = ? AND password = ?', (username, hashlib.sha256(password.encode("utf8")).hexdigest())).fetchone()
        conn.close()
        return user
    
    def daily_draw(self, user_id):
        """通过（user_id, today）组合作为主键，保持唯一性"""
        today = datetime.now().strftime('%Y-%m-%d')
        conn = self.get_db_connection(self.event_db_path)
        record = conn.execute('SELECT * FROM lottery WHERE user_id = ? AND draw_date = ?',(user_id, today)).fetchone()
        conn.close()
        return record
    
    def record_lottery_result(self, user_id, prize):
        """记录抽奖"""
        today = datetime.now().strftime('%Y-%m-%d')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = self.get_db_connection(self.event_db_path)
        try:
            conn.execute('INSERT INTO lottery (user_id, draw_date, prize, draw_time) VALUES (?, ?, ?, ?)',(user_id, today, prize, now))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_user_contributions(self, user_id):
        """投稿记录"""
        conn = self.get_db_connection(self.event_db_path)
        contributions = conn.execute('SELECT * FROM contribution WHERE user_id = ? ORDER BY time DESC',(user_id,)).fetchall()
        conn.close()
        return contributions
    
    def add_contribution(self, user_id, name, file_path):
        """添加投稿"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = self.get_db_connection(self.event_db_path)
        try:
            conn.execute('INSERT INTO contribution (user_id, name, time, file_path) VALUES (?, ?, ?, ?)',(user_id, name, now, file_path))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_user_banner_status(self, user_id):
        """检查是否已获得纪念banner"""
        conn = self.get_db_connection(self.event_db_path)
        banner = conn.execute('''
            SELECT * FROM lottery 
            WHERE user_id = ? AND prize = ?
        ''', (user_id, "《星辰》纪念banner")).fetchone()
        conn.close()
        return banner is not None
    
    def get_claimed_limited_prizes(self):
        """获取已被领取的限量奖品数量"""
        conn = self.get_db_connection(self.event_db_path)
        count = conn.execute('''
            SELECT COUNT(*) as count FROM prize_status 
            WHERE is_claimed = 1
        ''').fetchone()['count']
        conn.close()
        return count
    
    def get_available_limited_prizes(self):
        """获取可领取的限量奖品列表"""
        conn = self.get_db_connection(self.event_db_path)
        prizes = conn.execute('''
            SELECT prize_id, prize_name FROM prize_status 
            WHERE is_claimed = 0
        ''').fetchall()
        conn.close()
        return [dict(p) for p in prizes]
    
    def claim_limited_prize(self, user_id, prize_id, prize_name):
        """领取限量奖品"""
        conn = self.get_db_connection(self.event_db_path)
        try:
            current = conn.execute('''
                SELECT is_claimed FROM prize_status 
                WHERE prize_id = ?
            ''', (prize_id,)).fetchone()
            if current and current['is_claimed'] == 0:
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                conn.execute('''
                    UPDATE prize_status 
                    SET is_claimed = 1, claimed_by = ?, claimed_time = ?
                    WHERE prize_id = ?
                ''', (user_id, now, prize_id))
                today = datetime.now().strftime('%Y-%m-%d')
                conn.execute('''
                    INSERT INTO lottery (user_id, draw_date, prize, draw_time) 
                    VALUES (?, ?, ?, ?)
                ''', (user_id, today, prize_name, now))
                conn.commit()
                return True
            return False
        except Exception as e:
            print(f"领取奖品失败: {e}")
            return False
        finally:
            conn.close()
        
    def get_limited_prize_winners(self):
        """返回拿到限定奖品的用户信息哈"""
        event_conn = self.get_db_connection(self.event_db_path)
        try:
            claimed_prizes = event_conn.execute('''
                SELECT 
                    ps.prize_id, 
                    ps.prize_name, 
                    ps.claimed_by, 
                    ps.claimed_time
                FROM prize_status ps
                WHERE ps.is_claimed = 1
                ORDER BY ps.claimed_time DESC
            ''').fetchall()
        finally:
            event_conn.close()  
        winners = []
        for prize in claimed_prizes:
            user_name = "未知用户"
            if prize['claimed_by']:
                user_conn = self.get_db_connection(self.user_db_path)
                try:
                    user = user_conn.execute('''
                        SELECT name 
                        FROM user 
                        WHERE user_id = ?
                    ''', (prize['claimed_by'],)).fetchone()
                    if user:
                        user_name = user['name']
                except sqlite3.Error as e:
                    print(f"查询用户信息失败: {str(e)}")
                finally:
                    user_conn.close() 
            winners.append({
                'prize_id': prize['prize_id'],
                'prize_name': prize['prize_name'],
                'claimed_by': prize['claimed_by'],
                'claimed_time': prize['claimed_time'],
                'user_name': user_name
            })
        return winners