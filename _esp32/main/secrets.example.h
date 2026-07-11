#ifndef SECRETS_H
#define SECRETS_H

// Copy this file to secrets.h and fill in your WiFi credentials
// secrets.h is gitignored to prevent committing sensitive data

// WiFi SSID (network name)
// IMPORTANT: ESP32 only supports 2.4GHz WiFi networks!
// If your router has separate 2.4GHz and 5GHz networks, make sure to use the 2.4GHz one.
// Example: "MyNetwork" or "MyNetwork-2.4GHz" (not "MyNetwork-5GHz")
const char* WIFI_SSID = "your_wifi_ssid";

// WiFi password
const char* WIFI_PASSWORD = "your_wifi_password";

// mDNS name - allows you to access the ESP32 using this_name.local
// Example: "esp32" allows access via "esp32.local"
// Must be alphanumeric, no spaces or special characters
const char* MDNS_NAME = "esp32";

// OTA update password, stored as an MD5 hash so the plaintext never ships
// in the firmware binary. Generate the raw 32-hex-digit hash with:
//   macOS:  echo -n 'your_password' | md5 -q
//   Linux:  echo -n 'your_password' | md5sum | cut -d' ' -f1
// (plain `md5`/`md5sum` print extra text alongside the hash — copying that
// in as-is will make OTA auth fail). Leave empty ("") to disable OTA
// entirely — the firmware never starts an unauthenticated OTA endpoint.
const char* OTA_PASSWORD_HASH = "";

#endif
