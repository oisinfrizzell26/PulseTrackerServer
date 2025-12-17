from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import threading
import time
from datetime import datetime
import json
import logging
from database import init_database, WorkoutDatabase

app = Flask(__name__)
init_database()  # Initialize database on startup

# Disable Flask's request logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Thread lock for shared data
data_lock = threading.Lock()

# MQTT Configuration
MQTT_BROKER = "alderaan.software-engineering.ie"  # Remote MQTT broker
MQTT_PORT = 1883
CLIENT_ID = "pulsetracker_flask_server"

# Topics
TOPIC_MODE = "pulsetracker/mode"
TOPIC_HEART = "pulsetracker/heartRate"
TOPIC_WORKOUT = "pulsetracker/workout"

# Global variables to store data
heart_rate_data = []
current_mode = "None"
workout_data = []
current_workout_id = None  # Track active workout in database
current_workout_status = {
    'active': False,
    'mode': '',
    'current_lap': 0,
    'total_laps': 0,
    'state': '',
    'workout_id': None,
    'started_at': None
}
mqtt_client = None
mqtt_connected_once = False  # Track if we've already printed connection message

def on_connect(client, userdata, flags, reason_code, properties):
    global mqtt_connected_once
    if reason_code.is_failure:
        print(f"❌ MQTT Connection failed with code {reason_code}")
    else:
        # Only print on very first connection
        if not mqtt_connected_once:
            print("✅ Connected to MQTT broker")
            print(f"📡 Subscribed to: {TOPIC_HEART}, {TOPIC_MODE}, {TOPIC_WORKOUT}")
            mqtt_connected_once = True
        client.subscribe(TOPIC_HEART)
        client.subscribe(TOPIC_MODE)
        client.subscribe(TOPIC_WORKOUT)

def on_message(client, userdata, msg):
    global heart_rate_data, current_mode, workout_data, current_workout_status, current_workout_id
    
    topic = msg.topic
    payload = msg.payload.decode()
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    print(f"🔔 Message received on topic: {topic}")
    
    if topic == TOPIC_HEART:
        print(f"❤️ Heart rate: {payload}")
        # Validate and parse heart rate (backward compatible with original behavior)
        if not payload.isdigit():
            print(f"⚠️  Warning: Invalid heart rate data '{payload}', storing as 0")
            heart_rate = 0
        else:
            heart_rate = int(payload)
        
        # Store heart rate data with timestamp (thread-safe)
        with data_lock:
            heart_rate_data.append({
                'time': timestamp,
                'heart_rate': heart_rate
            })
            # Keep only last 50 readings
            if len(heart_rate_data) > 50:
                heart_rate_data.pop(0)
        
        # Save to database
        WorkoutDatabase.add_heart_rate(heart_rate, current_workout_id, current_mode)
    
    elif topic == TOPIC_MODE:
        print(f"📥 Mode update: {payload}")
        current_mode = payload
    
    elif topic == TOPIC_WORKOUT:
        print(f"\n🏋️  WORKOUT DATA RECEIVED 🏋️")
        print(f"⏰ Timestamp: {timestamp}")
        print(f"📦 Payload: {payload}")
        print("=" * 60)
        
        # Parse workout data and update current status
        try:
            workout_json = json.loads(payload)
            event_type = workout_json.get('event', '')
            
            if event_type == 'start':
                mode = workout_json.get('mode', 'Unknown')
                total_laps = workout_json.get('laps', 0)
                
                # Create new workout in database
                current_workout_id = WorkoutDatabase.create_workout(mode, total_laps)
                
                current_workout_status['active'] = True
                current_workout_status['mode'] = mode
                current_workout_status['current_lap'] = 1
                current_workout_status['total_laps'] = total_laps
                current_workout_status['state'] = 'running'
                current_workout_status['workout_id'] = current_workout_id
                current_workout_status['started_at'] = timestamp
                
            elif event_type == 'lap':
                lap_num = workout_json.get('lap', 0)
                lap_time_ms = workout_json.get('lap_ms', 0)
                split_time_ms = workout_json.get('split_ms', 0)
                
                # Save lap to database
                if current_workout_id:
                    WorkoutDatabase.add_lap(current_workout_id, lap_num, lap_time_ms, split_time_ms)
                
                current_workout_status['current_lap'] = lap_num + 1
                
            elif event_type == 'done':
                total_laps = workout_json.get('laps', 0)
                total_time_ms = workout_json.get('total_ms', 0)
                
                # Mark workout as completed in database
                if current_workout_id:
                    WorkoutDatabase.complete_workout(current_workout_id, total_laps, total_time_ms, 'completed')
                
                current_workout_status['active'] = False
                current_workout_status['state'] = 'done'
                current_workout_id = None
                
            elif event_type == 'stop':
                total_laps = workout_json.get('laps', 0)
                total_time_ms = workout_json.get('total_ms', 0)
                
                # Mark workout as stopped in database
                if current_workout_id:
                    WorkoutDatabase.complete_workout(current_workout_id, total_laps, total_time_ms, 'stopped')
                
                current_workout_status['active'] = False
                current_workout_status['state'] = 'stop'
                current_workout_id = None
                
            elif event_type == 'status':
                current_workout_status['current_lap'] = workout_json.get('lap', 0)
                current_workout_status['state'] = workout_json.get('state', '')
        except Exception as e:
            print(f"❌ Error parsing workout data: {e}")
            print(f"   Payload was: {payload}")
        
        # Store workout data with timestamp (thread-safe)
        with data_lock:
            workout_data.append({
                'time': timestamp,
                'data': payload
            })
            # Keep only last 100 workout events
            if len(workout_data) > 100:
                workout_data.pop(0)

def setup_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, CLIENT_ID)
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    
    print(f"🔌 Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT}...")
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
        print("🔄 MQTT loop started")
    except Exception as e:
        print(f"❌ MQTT setup error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/workout')
def workout_view():
    return render_template('workout.html')

@app.route('/history')
def history_view():
    return render_template('history.html')

@app.route('/api/heart-rate')
def get_heart_rate():
    return jsonify({
        'data': heart_rate_data,
        'current_mode': current_mode,
        'last_reading': heart_rate_data[-1] if heart_rate_data else None
    })

@app.route('/api/workout-data')
def get_workout_data():
    return jsonify({
        'data': workout_data,
        'last_event': workout_data[-1] if workout_data else None,
        'current_status': current_workout_status
    })

@app.route('/api/active-workout')
def get_active_workout():
    """Get the currently active workout with all details"""
    if current_workout_id:
        workout_details = WorkoutDatabase.get_workout_with_laps(current_workout_id)
        if workout_details:
            workout_details['current_status'] = current_workout_status
            return jsonify(workout_details)
    
    return jsonify({
        'active': False,
        'current_status': current_workout_status
    })

@app.route('/api/workouts')
def get_workouts():
    """Get all workouts"""
    workouts = WorkoutDatabase.get_all_workouts()
    return jsonify(workouts)

@app.route('/api/workouts/<int:workout_id>')
def get_workout_details(workout_id):
    """Get a specific workout with laps"""
    workout = WorkoutDatabase.get_workout_with_laps(workout_id)
    if workout:
        return jsonify(workout)
    return jsonify({'error': 'Workout not found'}), 404

@app.route('/api/workouts/by-category')
def get_workouts_by_category():
    """Get workouts grouped by category"""
    categories = WorkoutDatabase.get_workouts_by_category()
    return jsonify(categories)

@app.route('/api/set-mode', methods=['POST'])
def set_mode():
    global mqtt_client
    
    data = request.get_json()
    mode = data.get('mode')
    
    if mode in ['1', '2']:
        if mqtt_client:
            mqtt_client.publish(TOPIC_MODE, mode)
            mode_name = "Fitness Mode" if mode == "1" else "Lap Mode"
            return jsonify({'success': True, 'message': f'Set to {mode_name}'})
        else:
            return jsonify({'success': False, 'message': 'MQTT not connected'})
    
    return jsonify({'success': False, 'message': 'Invalid mode'})

if __name__ == '__main__':
    # Setup MQTT in a separate thread
    mqtt_thread = threading.Thread(target=setup_mqtt)
    mqtt_thread.daemon = True
    mqtt_thread.start()
    
    # Give MQTT time to connect
    time.sleep(2)
    
    print("🚀 Starting PulseTracker Flask Server")
    print("🌐 Open browser to: http://localhost:8080")
    
    # Disable reloader to prevent MQTT connection issues
    app.run(host='0.0.0.0', port=8080, debug=True, use_reloader=False)