import json
import pandas as pd
from datetime import datetime
import paho.mqtt.client as mqtt

rows = []

def on_connect(client, userdata, flags, rc):
    print("✅ Connected to MQTT broker")
    client.subscribe("energy/virtual_meter_01")

def on_message(client, userdata, msg):
    data = json.loads(msg.payload.decode())
    data["received_at"] = datetime.now().isoformat()
    rows.append(data)

    df = pd.DataFrame(rows)
    df.to_csv("energy_data.csv", index=False)

    print("received data : ", data)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect("localhost", 1883, 60)
client.loop_forever()

