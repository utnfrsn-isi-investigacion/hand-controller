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

#endif
