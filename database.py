"""
Database models and setup for PulseTracker
"""
from datetime import datetime
import sqlite3
import json
from typing import Optional, List, Dict

DATABASE_FILE = 'pulsetracker.db'

def get_db_connection():
    """Get a database connection"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mode TEXT NOT NULL,
            total_laps INTEGER,
            total_time_ms INTEGER,
            status TEXT DEFAULT 'active',
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            avg_heart_rate INTEGER,
            max_heart_rate INTEGER,
            min_heart_rate INTEGER
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS laps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER NOT NULL,
            lap_number INTEGER NOT NULL,
            lap_time_ms INTEGER NOT NULL,
            split_time_ms INTEGER NOT NULL,
            avg_heart_rate INTEGER,
            max_heart_rate INTEGER,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workout_id) REFERENCES workouts (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS heart_rate_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_id INTEGER,
            heart_rate INTEGER NOT NULL,
            mode TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workout_id) REFERENCES workouts (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ Database initialized")

class WorkoutDatabase:
    """Handle all workout database operations"""
    
    @staticmethod
    def create_workout(mode: str, total_laps: int) -> int:
        """Create a new workout session"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO workouts (mode, total_laps, status)
            VALUES (?, ?, 'active')
        ''', (mode, total_laps))
        workout_id = cursor.lastrowid
        conn.commit()
        conn.close()
        print(f"✅ Created workout #{workout_id}: {mode} - {total_laps} laps")
        return workout_id
    
    @staticmethod
    def add_lap(workout_id: int, lap_number: int, lap_time_ms: int, split_time_ms: int, 
                avg_hr: Optional[int] = None, max_hr: Optional[int] = None):
        """Add a lap to a workout"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO laps (workout_id, lap_number, lap_time_ms, split_time_ms, avg_heart_rate, max_heart_rate)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (workout_id, lap_number, lap_time_ms, split_time_ms, avg_hr, max_hr))
        conn.commit()
        conn.close()
        print(f"✅ Added lap {lap_number} to workout #{workout_id}: {lap_time_ms}ms")
    
    @staticmethod
    def complete_workout(workout_id: int, total_laps: int, total_time_ms: int, status: str = 'completed'):
        """Mark a workout as completed"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT AVG(heart_rate) as avg_hr, MAX(heart_rate) as max_hr, MIN(heart_rate) as min_hr
            FROM heart_rate_data
            WHERE workout_id = ?
        ''', (workout_id,))
        hr_stats = cursor.fetchone()
        
        avg_hr = int(hr_stats['avg_hr']) if hr_stats['avg_hr'] is not None else None
        max_hr = hr_stats['max_hr']
        min_hr = hr_stats['min_hr']
        
        cursor.execute('''
            UPDATE workouts
            SET status = ?, total_laps = ?, total_time_ms = ?, completed_at = CURRENT_TIMESTAMP,
                avg_heart_rate = ?, max_heart_rate = ?, min_heart_rate = ?
            WHERE id = ?
        ''', (status, total_laps, total_time_ms, avg_hr, max_hr, min_hr, workout_id))
        
        conn.commit()
        conn.close()
        print(f"✅ Completed workout #{workout_id}: {status}")
    
    @staticmethod
    def add_heart_rate(heart_rate: int, workout_id: Optional[int] = None, mode: Optional[str] = None):
        """Add a heart rate reading"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO heart_rate_data (heart_rate, workout_id, mode)
            VALUES (?, ?, ?)
        ''', (heart_rate, workout_id, mode))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_active_workout() -> Optional[Dict]:
        """Get the currently active workout"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM workouts
            WHERE status = 'active'
            ORDER BY started_at DESC
            LIMIT 1
        ''')
        workout = cursor.fetchone()
        conn.close()
        
        if workout:
            return dict(workout)
        return None
    
    @staticmethod
    def get_workout_with_laps(workout_id: int) -> Optional[Dict]:
        """Get a workout with all its laps"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM workouts WHERE id = ?', (workout_id,))
        workout = cursor.fetchone()
        
        if not workout:
            conn.close()
            return None
        
        cursor.execute('''
            SELECT * FROM laps
            WHERE workout_id = ?
            ORDER BY lap_number
        ''', (workout_id,))
        laps = cursor.fetchall()
        
        cursor.execute('''
            SELECT heart_rate, recorded_at FROM heart_rate_data
            WHERE workout_id = ?
            ORDER BY recorded_at
        ''', (workout_id,))
        heart_rates = cursor.fetchall()
        
        conn.close()
        
        return {
            'workout': dict(workout),
            'laps': [dict(lap) for lap in laps],
            'heart_rates': [dict(hr) for hr in heart_rates]
        }
    
    @staticmethod
    def get_all_workouts(limit: int = 50) -> List[Dict]:
        """Get all workouts, most recent first"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT w.*, 
                   (SELECT COUNT(*) FROM laps WHERE workout_id = w.id) as lap_count
            FROM workouts w
            ORDER BY w.started_at DESC
            LIMIT ?
        ''', (limit,))
        workouts = cursor.fetchall()
        conn.close()
        return [dict(workout) for workout in workouts]
    
    @staticmethod
    def get_workouts_by_category() -> Dict[str, List[Dict]]:
        """Get workouts grouped by distance/mode"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM workouts
            WHERE status = 'completed'
            ORDER BY started_at DESC
        ''')
        all_workouts = cursor.fetchall()
        conn.close()
        
        categories = {}
        for workout in all_workouts:
            workout_dict = dict(workout)
            mode = workout_dict.get('mode', 'Unknown')
            if mode not in categories:
                categories[mode] = []
            categories[mode].append(workout_dict)
        
        return categories

if __name__ == '__main__':
    init_database()
    print("Database setup complete!")
