#include "secrets.h"
#include "config.h"
#include <WiFi.h>
#include <ESPmDNS.h>
#include <ArduinoOTA.h>

WiFiServer tcpServer(TCP_PORT);

//////////////////////
// ACTIONS
//////////////////////
struct Action {
  const char* code;
  void (*handler)(WiFiClient&);
};

// Pin-level helpers, usable without a connected client (failsafe path)
void applyStop() {
  digitalWrite(LED_PIN, LOW);
  // Stop levels are defined in config.h — verify them against the motor
  // driver wiring (see the note there).
  digitalWrite(MOTOR_PIN_B, MOTOR_STOP_LEVEL_B);
  digitalWrite(MOTOR_PIN_A, MOTOR_STOP_LEVEL_A);
}

void applyStraight() {
  digitalWrite(DIRECTION_PIN_RIGHT, LOW);
  digitalWrite(DIRECTION_PIN_LEFT, LOW);
}

// Stop motors and center direction when the client is gone or silent
void failsafeStop() {
  applyStop();
  applyStraight();
  Serial.println("Failsafe: stopping motors");
}

// Action handlers
void accelerate(WiFiClient& client) {
  digitalWrite(LED_PIN, HIGH);
  digitalWrite(MOTOR_PIN_B, LOW);
  digitalWrite(MOTOR_PIN_A, HIGH);
  client.println("ACCELERATE (LED ON)");
}

void stopAction(WiFiClient& client) {
  applyStop();
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
  applyStraight();
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
// OTA
//////////////////////
void setupOTA() {
  if (strlen(OTA_PASSWORD_HASH) == 0) {
    Serial.println("OTA disabled: no password hash in secrets.h");
    return;
  }

  ArduinoOTA.setHostname(MDNS_NAME);
  ArduinoOTA.setPasswordHash(OTA_PASSWORD_HASH);

  ArduinoOTA.onStart([]() {
    // Stop motors before flash erase begins
    failsafeStop();
    Serial.println("OTA: update starting");
  });
  ArduinoOTA.onEnd([]() {
    Serial.println("OTA: update complete");
  });
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    Serial.printf("OTA progress: %u%%\n", (progress * 100) / total);
  });
  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("OTA error [%u]: ", error);
    if (error == OTA_AUTH_ERROR) Serial.println("Auth failed");
    else if (error == OTA_BEGIN_ERROR) Serial.println("Begin failed");
    else if (error == OTA_CONNECT_ERROR) Serial.println("Connect failed");
    else if (error == OTA_RECEIVE_ERROR) Serial.println("Receive failed");
    else if (error == OTA_END_ERROR) Serial.println("End failed");
  });

  ArduinoOTA.begin();
  Serial.println("OTA ready");
}

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

  // Start from a known-safe output state
  applyStop();
  applyStraight();

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

  // Start OTA updates (no-op if no password hash is configured)
  setupOTA();

  // Start TCP server
  tcpServer.begin();
  Serial.printf("TCP server listening on port %d\n", TCP_PORT);
}

//////////////////////
// LOOP
//////////////////////
void loop() {
  ArduinoOTA.handle();

  WiFiClient client = tcpServer.accept();
  if (client) {
    Serial.println("Client connected!");
    unsigned long lastCommandMs = millis();
    bool failsafeActive = false;
    while (client.connected()) {
      ArduinoOTA.handle();
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
        lastCommandMs = millis();
        failsafeActive = false;
      } else if (!failsafeActive && millis() - lastCommandMs > COMMAND_TIMEOUT_MS) {
        // Dead-man switch: the client resends the current action periodically,
        // so a silent connection means it is gone (crash, sleep, WiFi drop).
        failsafeStop();
        failsafeActive = true;
      }
    }
    client.stop();
    failsafeStop();
    Serial.println("Client disconnected.");
  }
}
