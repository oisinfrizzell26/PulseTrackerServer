from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt
import threading
import time
from datetime import datetime

app = Flask(__name__)

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
current_workout_status = {
    'active': False,
    'mode': '',
    'current_lap': 0,
    'total_laps': 0,
    'state': ''
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
    global heart_rate_data, current_mode, workout_data, current_workout_status
    
    topic = msg.topic
    payload = msg.payload.decode()
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    if topic == TOPIC_HEART:
        print(f"❤️ Heart rate: {payload}")
        # Store heart rate data with timestamp
        heart_rate_data.append({
            'time': timestamp,
            'heart_rate': int(payload) if payload.isdigit() else 0
        })
        # Keep only last 50 readings
        if len(heart_rate_data) > 50:
            heart_rate_data.pop(0)
    
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
            import json
            workout_json = json.loads(payload)
            event_type = workout_json.get('event', '')
            
            if event_type == 'start':
                current_workout_status['active'] = True
                current_workout_status['mode'] = workout_json.get('mode', '')
                current_workout_status['current_lap'] = 1
                current_workout_status['total_laps'] = workout_json.get('laps', 0)
                current_workout_status['state'] = 'running'
            elif event_type == 'lap':
                current_workout_status['current_lap'] = workout_json.get('lap', 0) + 1
            elif event_type == 'done' or event_type == 'stop':
                current_workout_status['active'] = False
                current_workout_status['state'] = event_type
            elif event_type == 'status':
                current_workout_status['current_lap'] = workout_json.get('lap', 0)
                current_workout_status['state'] = workout_json.get('state', '')
        except:
            pass
        
        # Store workout data with timestamp
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
    
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"❌ MQTT setup error: {e}")

@app.route('/')
def index():
    return render_template('index.html')

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
    
    app.run(host='0.0.0.0', port=8080, debug=True)