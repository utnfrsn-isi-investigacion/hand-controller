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
// ACTIONS
//////////////////////
struct Action {
  const char* code;
  void (*handler)(WiFiClient&);
};

// Action handlers
void accelerate(WiFiClient& client) {
  digitalWrite(2, HIGH);
  client.println("ACCELERATE (LED ON)");
}

void stopAction(WiFiClient& client) {
  digitalWrite(2, LOW);
  client.println("STOP (LED OFF)");
}

void directionLeft(WiFiClient& client) {
  client.println("DIRECTION LEFT");
}

void directionRight(WiFiClient& client) {
  client.println("DIRECTION RIGHT");
}

void directionStraight(WiFiClient& client) {
  client.println("DIRECTION STRAIGHT");
}

// Action mapping table
Action actions[] = {
  {"001", accelerate},
  {"000", stopAction},
  {"101", directionLeft},
  {"110", directionRight},
  {"111", directionStraight}
};

const int numActions = sizeof(actions) / sizeof(actions[0]);

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
  WiFiClient client = tcpServer.available();
  if (client) {
    Serial.println("Client connected!");
    while (client.connected()) {
      if (client.available()) {
        String command = client.readStringUntil('\n');
        command.trim(); // strip \r \n and spaces
        Serial.printf("Received command: %s\n", command.c_str());

        bool matched = false;
        for (int i = 0; i < numActions; i++) {
          if (command.equals(actions[i].code)) {
            actions[i].handler(client);
            matched = true;
            break;
          }
        }
        if (!matched) {
          client.println("Unknown command");
        }
      }
    }
    client.stop();
    Serial.println("Client disconnected.");
  }
}
