#include "secrets.h"
#include "config.h"
#include <WiFi.h>
#include <ESPmDNS.h>
#include <ArduinoOTA.h>
#include <DriveControl.h>

WiFiServer tcpServer(TCP_PORT);

//////////////////////
// DRIVE STATE
//////////////////////
// The traction and steering state machine lives in lib/DriveControl so it can
// run on the host: the reversal dwell is what protects the H-bridge, and
// `make test` exercises it against the values below without a board. This
// file only wires it to the real clock and GPIOs -- the one digitalWrite in
// the sketch is the adaptor right here.
static void writePin(int pin, int level) {
  digitalWrite(pin, level);
}

static const DriveConfig DRIVE_CONFIG = {
  LED_PIN,
  MOTOR_PIN_A, MOTOR_PIN_B,
  MOTOR_STOP_LEVEL_A, MOTOR_STOP_LEVEL_B,
  DIRECTION_PIN_LEFT, DIRECTION_PIN_RIGHT,
  REVERSAL_DWELL_MS
};

DriveControl drive(DRIVE_CONFIG, writePin);

//////////////////////
// ACTIONS
//////////////////////
struct Action {
  const char* code;
  void (*handler)(WiFiClient&);
};

// Stop motors and center direction when the client is gone or silent
void failsafeStop() {
  drive.failsafe(millis());
  Serial.println("Failsafe: stopping motors");
}

// The brake is the one refusal worth a serial line: it is the moment the
// dwell starts, and the only one the client cannot tell apart from a held
// retry by its own behaviour.
static void replyDrive(WiFiClient& client, DriveResult result, const char* engaged, const char* held) {
  if (result == DRIVE_BRAKED) {
    Serial.printf("Reversal: braking first, holding for %lu ms\n", REVERSAL_DWELL_MS);
  }
  client.println(result == DRIVE_ENGAGED ? engaged : held);
}

// Action handlers. Both drive handlers go through drive.engage() -- writing
// the motor pins directly here would bypass the reversal dwell.
void accelerate(WiFiClient& client) {
  // IN1 = HIGH / IN2 = LOW: the forward row of the H-bridge truth table.
  replyDrive(client, drive.engage(DRIVE_FORWARD, HIGH, LOW, millis()),
             "ACCELERATE (LED ON)", "ACCELERATE held: reversal dwell");
}

void reverse(WiFiClient& client) {
  // Levels come from config.h -- read the note there before trusting this on
  // real hardware.
  replyDrive(client, drive.engage(DRIVE_REVERSE, MOTOR_REVERSE_LEVEL_A, MOTOR_REVERSE_LEVEL_B, millis()),
             "REVERSE (LED ON)", "REVERSE held: reversal dwell");
}

void stopAction(WiFiClient& client) {
  drive.stop(millis());
  client.println("STOP (LED OFF)");
}

void directionLeft(WiFiClient& client) {
  drive.steerLeft();
  client.println("DIRECTION LEFT");
}

void directionRight(WiFiClient& client) {
  drive.steerRight();
  client.println("DIRECTION RIGHT");
}

void directionStraight(WiFiClient& client) {
  drive.steerStraight();
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
  // Pins first, before the serial port and its settle delay. Every GPIO is an
  // input until pinMode runs, so the H-bridge inputs float and the motor can
  // twitch on whatever they pick up; anything ahead of these lines is time
  // spent in that state. This only shortens the window to the boot ROM and
  // bootloader we cannot touch -- it does not close it. Pull-downs on the
  // driver inputs are what hold the bridge off while nobody is driving it.
  pinMode(LED_PIN, OUTPUT);
  pinMode(DIRECTION_PIN_LEFT, OUTPUT);
  pinMode(DIRECTION_PIN_RIGHT, OUTPUT);
  pinMode(MOTOR_PIN_A, OUTPUT);
  pinMode(MOTOR_PIN_B, OUTPUT);

  // Start from a known-safe output state
  drive.failsafe(millis());

  Serial.begin(SERIAL_BAUD);
  delay(1000);

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
