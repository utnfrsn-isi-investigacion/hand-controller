#include "secrets.h"
#include "config.h"
#include <WiFi.h>
#include <ESPmDNS.h>
#include <ArduinoOTA.h>

WiFiServer tcpServer(TCP_PORT);

//////////////////////
// DRIVE STATE
//////////////////////
// What the traction channel is doing now, which way it last turned, and when
// it stopped. Together these carry the reversal dwell (REVERSAL_DWELL_MS in
// config.h): lastDriveDirection is what distinguishes "stopped after driving
// the other way", which owes a spin-down, from "stopped after driving this
// way" and "never driven", which do not -- so pulling away from a stop in the
// direction you were already going stays immediate.
enum DriveState { DRIVE_STOPPED, DRIVE_FORWARD, DRIVE_REVERSE };
DriveState driveState = DRIVE_STOPPED;
DriveState lastDriveDirection = DRIVE_STOPPED;
unsigned long driveStoppedAtMs = 0;

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
  // Start the spin-down clock on the transition only: the client resends the
  // current action every refresh_interval, and re-stamping on each repeated
  // STOP would push the dwell permanently out of reach.
  if (driveState != DRIVE_STOPPED) {
    driveState = DRIVE_STOPPED;
    driveStoppedAtMs = millis();
  }
}

// Drive the traction motor, enforcing the reversal dwell. Returns false when
// the request was held off, leaving the motor stopped; the caller does not
// need to retry, because the client's keepalive resend does it.
bool engageDrive(DriveState wanted, int levelA, int levelB) {
  if (driveState != wanted) {
    if (driveState != DRIVE_STOPPED) {
      // Turning the other way right now: brake and start the clock. The
      // earliest this request can be honoured is REVERSAL_DWELL_MS from here.
      applyStop();
      Serial.printf("Reversal: braking first, holding for %lu ms\n", REVERSAL_DWELL_MS);
      return false;
    }
    if (lastDriveDirection != DRIVE_STOPPED && lastDriveDirection != wanted &&
        millis() - driveStoppedAtMs < REVERSAL_DWELL_MS) {
      // Stopped, but still spinning down from the opposite direction.
      return false;
    }
  }
  digitalWrite(LED_PIN, HIGH);
  // Drop the pin that goes low before raising the other, so the bridge is
  // never briefly driven on both sides.
  if (levelA == LOW) {
    digitalWrite(MOTOR_PIN_A, levelA);
    digitalWrite(MOTOR_PIN_B, levelB);
  } else {
    digitalWrite(MOTOR_PIN_B, levelB);
    digitalWrite(MOTOR_PIN_A, levelA);
  }
  driveState = wanted;
  lastDriveDirection = wanted;
  return true;
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

// Action handlers. Both drive handlers go through engageDrive() -- writing the
// motor pins directly here would bypass the reversal dwell.
void accelerate(WiFiClient& client) {
  // IN1 = HIGH / IN2 = LOW: the forward row of the H-bridge truth table.
  if (engageDrive(DRIVE_FORWARD, HIGH, LOW)) {
    client.println("ACCELERATE (LED ON)");
  } else {
    client.println("ACCELERATE held: reversal dwell");
  }
}

void reverse(WiFiClient& client) {
  // Levels come from config.h -- read the note there before trusting this on
  // real hardware.
  if (engageDrive(DRIVE_REVERSE, MOTOR_REVERSE_LEVEL_A, MOTOR_REVERSE_LEVEL_B)) {
    client.println("REVERSE (LED ON)");
  } else {
    client.println("REVERSE held: reversal dwell");
  }
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
  {ACTION_REVERSE, reverse},
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
      } else if (millis() - lastCommandMs > COMMAND_TIMEOUT_MS) {
        // Dead-man switch: the client resends the current action every
        // refresh_interval, so silence this long means it is gone (crash,
        // sleep, WiFi drop). Leave the loop rather than just stopping the
        // motors: a half-open socket never reports !connected(), and while
        // this loop runs tcpServer.accept() does not, so a reconnecting
        // client would complete its TCP handshake and then be ignored
        // forever -- connected and sending, with nothing responding.
        Serial.println("Client silent past the dead-man timeout");
        break;
      }
    }
    // Covers both exits: clean disconnect and dead-man timeout
    client.stop();
    failsafeStop();
    Serial.println("Client disconnected.");
  }
}
