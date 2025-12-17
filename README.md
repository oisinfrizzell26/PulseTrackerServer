# PulseTrackerServer

A Flask-based MQTT server for tracking workout data from ESP32 heart rate monitors. Features real-time heart rate monitoring, lap tracking, and workout history.

## Features
- 📊 Real-time heart rate monitoring
- 🏃‍♂️ Active workout tracking with lap times
- 📈 Historical workout data with category filtering
- 💾 SQLite database for persistent storage
- 🔄 MQTT integration for ESP32 devices

## Installation

### Prerequisites
- Python 3.7+
- pip

### Setup

1. Clone the repository:
```bash
git clone https://github.com/oisinfrizzell26/PulseTrackerServer.git
cd PulseTrackerServer
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Server

```bash
python app.py
```

The server will start on `http://localhost:8080`

## Pages

- **Dashboard** (`/`) - Real-time heart rate and workout events
- **Active Workout** (`/workout`) - Live workout monitoring with lap details
- **History** (`/history`) - Browse past workouts by category

## MQTT Topics

The server subscribes to:
- `pulsetracker/heartRate` - Heart rate data (integer BPM)
- `pulsetracker/mode` - Mode changes
- `pulsetracker/workout` - Workout events (JSON)

### Workout Event Format

**Start:**
```json
{"event": "start", "mode": "400m Sprint", "laps": 5}
```

**Lap:**
```json
{"event": "lap", "lap": 1, "lap_ms": 45000, "split_ms": 12000}
```

**Done:**
```json
{"event": "done", "laps": 5, "total_ms": 285000}
```

**Stop:**
```json
{"event": "stop", "laps": 3, "total_ms": 180000}
```

## API Endpoints

- `GET /api/heart-rate` - Current heart rate data
- `GET /api/workout-data` - Current workout events
- `GET /api/active-workout` - Active workout details
- `GET /api/workouts` - All workouts
- `GET /api/workouts/<id>` - Specific workout details
- `GET /api/workouts/by-category` - Workouts grouped by mode
- `POST /api/set-mode` - Set device mode

## Testing

Test scripts are available in the `tests/` folder:

```bash
# Interactive MQTT test
python tests/test_mqtt.py

# Automated workout simulation
python tests/test_workout_auto.py
```

## Database

The application uses SQLite (`pulsetracker.db`) with three tables:
- `workouts` - Workout sessions
- `laps` - Individual lap data
- `heart_rate_data` - Heart rate readings

## Running Mosquitto Locally (Optional)

```powershell
cd $env:USERPROFILE
mosquitto -v -c "$env:USERPROFILE\mosq.conf"
```

## License

MIT


