#include <WiFi.h>
#include <ESPmDNS.h>

//////////////////////
// CONFIGURATION
//////////////////////
const char* ssid = "Echo";
const char* password = "personalputo01";

const char* mdnsName = "esp32"; // Access with http://esp32.local
const uint16_t tcpPort = 1234;

WiFiServer tcpServer(tcpPort);

//////////////////////
// SETUP
//////////////////////
void setup() {
  Serial.begin(115200);
  delay(1000);

  pinMode(2, OUTPUT);

  // Connect to Wi-Fi
  Serial.printf("Connecting to %s ...\n", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // Start mDNS
  if (!MDNS.begin(mdnsName)) {
    Serial.println("Error starting mDNS");
  } else {
    Serial.printf("mDNS started: %s.local\n", mdnsName);
  }

  // Start TCP server
  tcpServer.begin();
  Serial.printf("TCP server listening on port %d\n", tcpPort);
}

//////////////////////
// LOOP
//////////////////////
void loop() {
  // Check for incoming TCP client
  WiFiClient client = tcpServer.available();
  if (client) {
    Serial.println("Client connected!");
    while (client.connected()) {
      if (client.available()) {
        String command = client.readStringUntil('\n');
        command.trim(); // Remove whitespace/newline
        Serial.printf("Received command: %s\n", command.c_str());

        // Example commands
        if (command == "Accelerate") {
          digitalWrite(2, HIGH);
          client.println("LED turned ON");
        } else if (command == "Stop") {
          digitalWrite(2, LOW);
          client.println("LED turned OFF");
        } else {
          client.println("Unknown command");
        }
      }
    }
    client.stop();
    Serial.println("Client disconnected.");
  }
}
