import sqlite3
import json
from datetime import datetime
import os

class ChatHandler:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_chat_tables()
    
    def init_chat_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sender_id) REFERENCES users (id),
                FOREIGN KEY (receiver_id) REFERENCES users (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user1_id INTEGER NOT NULL,
                user2_id INTEGER NOT NULL,
                last_message TEXT,
                last_message_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user1_id) REFERENCES users (id),
                FOREIGN KEY (user2_id) REFERENCES users (id),
                UNIQUE(user1_id, user2_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def send_message(self, sender_id, receiver_id, message):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (sender_id, receiver_id, message)
            VALUES (?, ?, ?)
        ''', (sender_id, receiver_id, message))
        
        message_id = cursor.lastrowid
        
        self._update_conversation(cursor, sender_id, receiver_id, message)
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'message_id': message_id,
            'sent_at': datetime.now().isoformat()
        }
    
    def _update_conversation(self, cursor, user1_id, user2_id, last_message):
        min_id = min(user1_id, user2_id)
        max_id = max(user1_id, user2_id)
        
        cursor.execute('''
            INSERT INTO conversations (user1_id, user2_id, last_message, last_message_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user1_id, user2_id) DO UPDATE SET
                last_message = excluded.last_message,
                last_message_at = CURRENT_TIMESTAMP
        ''', (min_id, max_id, last_message))
    
    def get_messages(self, user1_id, user2_id, limit=50):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT m.id, m.sender_id, m.receiver_id, m.message, m.is_read, m.sent_at,
                   u.full_name, u.user_type
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE (m.sender_id = ? AND m.receiver_id = ?)
               OR (m.sender_id = ? AND m.receiver_id = ?)
            ORDER BY m.sent_at DESC
            LIMIT ?
        ''', (user1_id, user2_id, user2_id, user1_id, limit))
        
        messages = cursor.fetchall()
        conn.close()
        
        result = []
        for msg in reversed(messages):
            result.append({
                'id': msg[0],
                'sender_id': msg[1],
                'receiver_id': msg[2],
                'message': msg[3],
                'is_read': bool(msg[4]),
                'sent_at': msg[5],
                'sender_name': msg[6],
                'sender_type': msg[7]
            })
        
        return result
    
    def mark_messages_as_read(self, receiver_id, sender_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE messages
            SET is_read = 1
            WHERE receiver_id = ? AND sender_id = ? AND is_read = 0
        ''', (receiver_id, sender_id))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
    
    def get_conversations(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, c.user1_id, c.user2_id, c.last_message, c.last_message_at,
                   u1.full_name, u1.user_type,
                   u2.full_name, u2.user_type,
                   (SELECT COUNT(*) FROM messages 
                    WHERE receiver_id = ? 
                    AND sender_id = CASE WHEN c.user1_id = ? THEN c.user2_id ELSE c.user1_id END
                    AND is_read = 0) as unread_count
            FROM conversations c
            JOIN users u1 ON c.user1_id = u1.id
            JOIN users u2 ON c.user2_id = u2.id
            WHERE c.user1_id = ? OR c.user2_id = ?
            ORDER BY c.last_message_at DESC
        ''', (user_id, user_id, user_id, user_id))
        
        conversations = cursor.fetchall()
        conn.close()
        
        result = []
        for conv in conversations:
            other_user_id = conv[2] if conv[1] == user_id else conv[1]
            other_user_name = conv[7] if conv[1] == user_id else conv[5]
            other_user_type = conv[8] if conv[1] == user_id else conv[6]
            
            result.append({
                'conversation_id': conv[0],
                'other_user_id': other_user_id,
                'other_user_name': other_user_name,
                'other_user_type': other_user_type,
                'last_message': conv[3],
                'last_message_at': conv[4],
                'unread_count': conv[9]
            })
        
        return result
    
    def get_unread_count(self, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM messages
            WHERE receiver_id = ? AND is_read = 0
        ''', (user_id,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def delete_message(self, message_id, user_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM messages
            WHERE id = ? AND sender_id = ?
        ''', (message_id, user_id))
        
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        
        return deleted
    
    def search_messages(self, user_id, search_query):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT m.id, m.sender_id, m.receiver_id, m.message, m.sent_at,
                   u.full_name
            FROM messages m
            JOIN users u ON m.sender_id = u.id
            WHERE (m.sender_id = ? OR m.receiver_id = ?)
              AND m.message LIKE ?
            ORDER BY m.sent_at DESC
            LIMIT 20
        ''', (user_id, user_id, f'%{search_query}%'))
        
        messages = cursor.fetchall()
        conn.close()
        
        result = []
        for msg in messages:
            result.append({
                'id': msg[0],
                'sender_id': msg[1],
                'receiver_id': msg[2],
                'message': msg[3],
                'sent_at': msg[4],
                'sender_name': msg[5]
            })
        
        return result