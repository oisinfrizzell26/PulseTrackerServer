import os
import threading
import logging
from flask import Flask, jsonify, request
from models import db, HeartRate

# Disable Flask request logging (only show errors)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'pulsetracker.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Global variable to store the current mode
# 0 = None, 1 = Fitness Mode, 2 = Lap Mode
current_mode = 0

@app.route("/")
def index():
    return f"Server is running. Current Mode: {current_mode}"

@app.route("/get-mode", methods=["GET"])
def get_mode():
    # The ESP32 will call this to find out what to do
    return jsonify({"mode": current_mode})

@app.route("/log-pulse", methods=["POST"])
def log_pulse():
    data = request.get_json()
    if not data or 'rate' not in data:
        return jsonify({"error": "No rate provided"}), 400
    
    # Create a new record using the ORM
    new_reading = HeartRate(rate=data['rate'], mode=current_mode)
    db.session.add(new_reading)
    db.session.commit()
    
    # print(f"\n[DATA RECEIVED] Heart Rate: {data['rate']} BPM (Mode: {current_mode})")
    return jsonify({"status": "success"}), 201

def run_server():
    # Run Flask without the reloader so it works well in a thread
    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Create the database tables if they don't exist
    with app.app_context():
        db.create_all()

    # Start Flask in a separate thread so we can use the terminal for input
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()

    print("\nWelcome to Pulse Tracker")
    
    while True:
        print("\nSelect a mode:")
        print("1. Fitness Mode")
        print("2. Lap Mode")
        
        try:
            choice = input("Enter choice (1 or 2): ").strip()
            
            if choice == "1":
                current_mode = 1
                print(">> Mode updated to: FITNESS MODE")
            elif choice == "2":
                current_mode = 2
                print(">> Mode updated to: LAP MODE")
            else:
                print("Invalid selection. Please try again.")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
