#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN D8
#define RST_PIN D0

MFRC522 rfid(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;
byte nuidPICC[4];

//School
const char* ssid = "Julien";
const char* password = "12345678";

const char* mqtt_server = "172.20.10.2";

const int pResistor = A0;

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


void reconnect() {
  while (!client.connected()) {

   if (client.connect("vanieriot")) { 
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
  
  SPI.begin(); // Init SPI bus
  rfid.PCD_Init(); // Init MFRC522
  Serial.println();
  Serial.print(F("Reader :"));
  rfid.PCD_DumpVersionToSerial();
  
  for (byte i = 0; i < 6; i++) {
    key.keyByte[i] = 0xFF;
  }
  
  setup_wifi();
  client.setServer(mqtt_server, 1883);
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

  if (rfid.PICC_IsNewCardPresent() && rfid.PICC_ReadCardSerial()) {
    MFRC522::PICC_Type piccType = rfid.PICC_GetType(rfid.uid.sak);
  
    if (piccType != MFRC522::PICC_TYPE_MIFARE_MINI &&
        piccType != MFRC522::PICC_TYPE_MIFARE_1K &&
        piccType != MFRC522::PICC_TYPE_MIFARE_4K) {
      Serial.println(F("Your tag is not of type MIFARE Classic."));
      return;
    }
  
    String tagID = "";
    for (byte i = 0; i < rfid.uid.size; i++) {
      tagID += String(rfid.uid.uidByte[i], HEX);
    }

    nuidPICC[0] = rfid.uid.uidByte[0];
    nuidPICC[1] = rfid.uid.uidByte[1];
    nuidPICC[2] = rfid.uid.uidByte[2];
    nuidPICC[3] = rfid.uid.uidByte[3];

    String message = tagID;
    Serial.println(message);
    client.publish("room/tagID", message.c_str());
} 
  
  delay(1000);
}
