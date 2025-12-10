import paho.mqtt.client as mqtt

# MQTT Configuration
MQTT_BROKER = "172.20.10.6"
MQTT_PORT = 1883
CLIENT_ID = "pulsetracker_server_oisin"

# Topics
TOPIC_MODE = "pulsetracker/mode"

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"❌ Connection failed with code {reason_code}")
    else:
        print("✅ Connected to MQTT broker")

def on_publish(client, userdata, mid, reason_code, properties):
    if reason_code.is_failure:
        print(f"❌ Publish failed with code {reason_code}")
    else:
        print(f"📤 Message published successfully")

def main():
    print("🚀 PulseTracker MQTT Server")
    print("=" * 30)
    
    # Create MQTT client
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, CLIENT_ID)
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    # Connect to broker
    print(f"🔄 Connecting to {MQTT_BROKER}...")
    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_start()
        
        # Give time to connect
        import time
        time.sleep(2)
        
        print("\n📋 Mode Selection:")
        
        while True:
            print("\nPick a mode:")
            print("1. Fitness Mode")
            print("2. Lap Mode")
            print("0. Exit")
            
            choice = input("Enter choice: ").strip()
            
            if choice == "1":
                print("➡️  You set the mode to: Fitness Mode")
                client.publish(TOPIC_MODE, "1")
                
            elif choice == "2":
                print("➡️  You set the mode to: Lap Mode")
                client.publish(TOPIC_MODE, "2")
                
            elif choice == "0":
                print("👋 Exiting...")
                break
                
            else:
                print("❌ Invalid choice")
    
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()