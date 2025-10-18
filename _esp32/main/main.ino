#include "secrets.h"
#include "config.h"
#include <WiFi.h>
#include <ESPmDNS.h>

WiFiServer tcpServer(TCP_PORT);

//////////////////////
// ACTIONS
//////////////////////
struct Action {
  const char* code;
  void (*handler)(WiFiClient&);
};

// Action handlers
void accelerate(WiFiClient& client) {
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(MOTOR_PIN_B, LOW);
  digitalWrite(MOTOR_PIN_A, HIGH);
  client.println("ACCELERATE (LED ON)");
}

void stopAction(WiFiClient& client) {
  digitalWrite(LED_PIN, LOW);
  digitalWrite(MOTOR_PIN_B, HIGH);
  digitalWrite(MOTOR_PIN_A, LOW);
  client.println("STOP (LED OFF)");
}

void directionLeft(WiFiClient& client) {
  digitalWrite(DIRECTION_PIN_LEFT, HIGH);
  digitalWrite(DIRECTION_PIN_RIGHT, LOW);
  client.println("DIRECTION LEFT");
}

void directionRight(WiFiClient& client) {
  digitalWrite(DIRECTION_PIN_RIGHT, HIGH);
  digitalWrite(DIRECTION_PIN_LEFT, LOW);
  client.println("DIRECTION RIGHT");
}

void directionStraight(WiFiClient& client) {
  digitalWrite(DIRECTION_PIN_RIGHT, LOW);
  digitalWrite(DIRECTION_PIN_LEFT, LOW);
  client.println("DIRECTION STRAIGHT");
}

// Action mapping table
Action actions[] = {
  {ACTION_ACCELERATE, accelerate},
  {ACTION_STOP, stopAction},
  {ACTION_LEFT, directionLeft},
  {ACTION_RIGHT, directionRight},
  {ACTION_STRAIGHT, directionStraight}
};

const int numActions = sizeof(actions) / sizeof(actions[0]);

//////////////////////
// SETUP
//////////////////////
void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(1000);

  pinMode(LED_PIN, OUTPUT);
  pinMode(DIRECTION_PIN_LEFT, OUTPUT);
  pinMode(DIRECTION_PIN_RIGHT, OUTPUT);
  pinMode(MOTOR_PIN_A, OUTPUT);
  pinMode(MOTOR_PIN_B, OUTPUT);

  // Connect to Wi-Fi using secrets
  Serial.printf("Connecting to %s ...\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi connected!");
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // Start mDNS
  if (!MDNS.begin(MDNS_NAME)) {
    Serial.println("Error starting mDNS");
  } else {
    Serial.printf("mDNS started: %s.local\n", MDNS_NAME);
  }

  // Start TCP server
  tcpServer.begin();
  Serial.printf("TCP server listening on port %d\n", TCP_PORT);
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
