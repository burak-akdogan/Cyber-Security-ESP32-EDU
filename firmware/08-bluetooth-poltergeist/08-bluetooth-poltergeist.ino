// bluetooth_poltergeist.ino
// Broadcasts a rotating stream of fake BLE device names. No pairing, no
// connection, no data exchange, no GATT services exposed. Classroom
// awareness demo — announce it to everyone in the room before running.

#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEAdvertising.h>

BLEAdvertising* advertising;

const char* fakeNames[] = {
  "AirPods Pro", "Galaxy Buds2", "Fitbit Charge 5", "Smart Lock 4B",
  "Meeting Room Mic", "Printer_HP2200", "Unknown Speaker", "Car Multimedia"
};
const int NUM_NAMES = sizeof(fakeNames) / sizeof(fakeNames[0]);
int idx = 0;

unsigned long lastSwap = 0;
const unsigned long SWAP_MS = 1200; // long enough for a scanner app to catch each one

void broadcastAs(const String& name) {
  BLEAdvertisementData advData;
  advData.setName(name.c_str());
  advData.setFlags(0x06); // general discoverable, BR/EDR not supported

  advertising->stop();
  advertising->setAdvertisementData(advData);
  advertising->setScanResponseData(advData);
  advertising->start();
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== Bluetooth Poltergeist: phantom devices incoming ===");
  Serial.println("Open a Bluetooth scanner on a nearby phone to watch them appear.\n");

  BLEDevice::init("");
  advertising = BLEDevice::getAdvertising();
  advertising->setScanResponse(true);
  broadcastAs(fakeNames[0]);
  Serial.printf("[BROADCAST] now impersonating \"%s\"\n", fakeNames[0]);
  lastSwap = millis();
}

void loop() {
  if (millis() - lastSwap < SWAP_MS) return;
  lastSwap = millis();

  idx = (idx + 1) % NUM_NAMES;
  broadcastAs(fakeNames[idx]);
  Serial.printf("[BROADCAST] now impersonating \"%s\"\n", fakeNames[idx]);
}
