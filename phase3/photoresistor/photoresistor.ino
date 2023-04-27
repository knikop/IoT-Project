#include <ESP8266WiFi.h>
#include <PubSubClient.h>

//School
//const char* ssid = "TP-Link_2AD8";
//const char* password = "14730078";
//
//const char* mqtt_server = "192.168.0.175";


//Home
const char* ssid = "Julien\342\200\231s iPhone";
const char* password = "iamarobot";

const char* mqtt_server = "172.20.10.8";

const int pResistor = D0;
const int pLight = 12;

WiFiClient vanieriot;
PubSubClient client(vanieriot);


void setup_wifi() {
  delay(10);
  // We start by connecting to a WiFi network
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("WiFi connected - ESP-8266 IP address: ");
  Serial.println(WiFi.localIP());
}


void callback(String topic, byte* message, unsigned int length) {
  Serial.print("Message arrived on topic: ");
  Serial.print(topic);
  Serial.print(". Message: ");
  String messagein;
  
  for (int i = 0; i < length; i++) {
    Serial.print((char)message[i]);
    messagein += (char)message[i];
  }

  if(topic=="room/light"){
    if (messagein == "ON") 
      Serial.println("Light is ON");
  }else{
          Serial.println("Light is OFF");

  }
  
}


void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
 
    
   //  String clientId = "ESP8266Client-";
   // clientId += String(random(0xffff), HEX);
    // Attempt to connect
   // if (client.connect(clientId.c_str())) {
           if (client.connect("vanieriot")) {

      Serial.println("connected");  
      client.subscribe("room/light");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}


void setup() {
  
  Serial.begin(115200);
  pinMode(pResistor, INPUT);
  pinMode(pLight, OUTPUT);
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

void loop() {

  if (!client.connected()) {
    reconnect();
  }
  if(!client.loop())
    client.connect("vanieriot");

  int value = analogRead(pResistor);
  Serial.print("Light intensity: ");
  Serial.println(value);

  String lightIntensity = String(value);
  client.publish("room/lightIntensity", lightIntensity.c_str());
  delay(1000);
}
