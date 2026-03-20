import paho.mqtt.client as mqtt
import torch
import torch.nn as nn
import numpy as np
import json
import time
from collections import defaultdict

NUM_SENSORS = 18
NUM_GATES = 6

# 🔹 Model Definition
class GatePredictorUltraTinyTransformer(nn.Module):
    def __init__(self):
        super().__init__()
        embed_dim, num_heads, num_layers, ff_dim = 16, 2, 1, 32
        self.input_fc = nn.Linear(NUM_SENSORS, embed_dim)
        layer = nn.TransformerEncoderLayer(d_model=embed_dim, nhead=num_heads,
                                           dim_feedforward=ff_dim, batch_first=True)
        self.transformer = nn.TransformerEncoder(layer, num_layers=num_layers)
        self.fc_out = nn.Linear(embed_dim, NUM_GATES)

    def forward(self, x):
        return self.fc_out(self.transformer(self.input_fc(x)))

# 🔹 Load Trained Model
model = GatePredictorUltraTinyTransformer()
state_dict = torch.load("gate_predictor.pth", map_location="cpu")
model.load_state_dict(state_dict)
model.eval()
print(" Model Loaded Successfully!")

# 🔹 MQTT Setup
MQTT_BROKER = "10.223.142.103"  # Raspberry Pi IP
MQTT_PORT = 1883
SENSOR_TOPIC = "sensors/esp32"
PREDICT_TOPIC = "prediction/gate"

client = mqtt.Client()

# 🔹 Store sensor states
sensor_data = defaultdict(int)  # Store latest 0/1 state
window_start = time.time()

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker (Code: {rc})")
    client.subscribe(SENSOR_TOPIC)

def on_message(client, userdata, msg):
    global window_start
    try:
        payload = json.loads(msg.payload.decode())
        sid = payload["sensor_id"]
        state = payload.get("state", 0)

        # Store latest sensor state
        sensor_data[sid] = state

        #  Every 60 sec → Make prediction
        if time.time() - window_start >= 60:
            make_prediction()
            window_start = time.time()
            sensor_data.clear()

    except Exception as e:
        print(f"Error processing message: {e}")

def make_prediction():
    # Convert sensor_data → Feature vector
    features = []
    for i in range(1, NUM_SENSORS + 1):
        sid = f"SENSOR_{i}"
        features.append(sensor_data.get(sid, 0))

    x = torch.tensor([[features]], dtype=torch.float32)  # Shape [1,1,18]

    with torch.no_grad():
        preds = model(x)
        preds = torch.sigmoid(preds).squeeze().numpy()

    result = [1 if p > 0.5 else 0 for p in preds]

    prediction = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "predicted_gates": result
    }
    client.publish(PREDICT_TOPIC, json.dumps(prediction))
    print(" Prediction Published:", prediction)

client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
