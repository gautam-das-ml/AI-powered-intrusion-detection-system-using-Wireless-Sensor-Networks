#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ===== WiFi Config =====
const char* ssid = "Gautam's S21 FE";
const char* password = "12345678";

// ===== MQTT Config =====
const char* mqtt_server = "10.223.142.103";  // Raspberry Pi IP
const char* mqtt_topic = "sensors/esp32";

WiFiClient espClient;
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n WiFi Connected");
  Serial.print("ESP32 IP: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Connecting to MQTT...");
    if (client.connect("ESP32_GATE_SENSORS")) {
      Serial.println(" Connected to MQTT");
    } else {
      Serial.print(" Failed, rc=");
      Serial.println(client.state());
      delay(2000);
    }
  }
}

void publishSensor(const char* sensor_id, int state) {
  StaticJsonDocument<100> doc;
  doc["sensor_id"] = sensor_id;
  doc["timestamp"] = millis();
  doc["state"] = state;  //  Only 0 or 1

  char payload[100];
  serializeJson(doc, payload);

  client.publish(mqtt_topic, payload);
  Serial.println(payload);
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  randomSeed(analogRead(0));  // Ensure random values each time
}

void loop() {
  if (!client.connected()) reconnect();
  client.loop();

  // Send random binary state for 18 sensors
  for (int i = 1; i <= 18; i++) {
    char sensor_id[12];
    sprintf(sensor_id, "SENSOR_%d", i);

    int state = random(0, 2); //  0 or 1
    publishSensor(sensor_id, state);
    delay(50);
  }

  delay(1000); // Repeat every second
}
