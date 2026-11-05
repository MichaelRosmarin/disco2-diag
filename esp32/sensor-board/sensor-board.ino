/*
  disco2-diag sensor board — ESP32 DevKit V1

  Reads the sensors the Td5 ECU does not have and streams them to the Pi over USB serial
  as one JSON object per line, 4 times a second:

    {"egt":412.5,"oil_press":3.12,"oil_temp":96.3,"gearbox_temp":82.1,"fuel_level":61,
     "aux_temp":24.1,"vin":13.9,"alarm":0,"up":12345}

  Keys are the dashboard's signal names (d2dash/sensors.py). Add a sensor here and it shows
  up on the Pi with no change there. The board also runs its own alarms on a buzzer, so a
  Pi reboot never silences an over-temperature or oil-pressure warning.

  Hardware (Micro Robotics / Takealot parts from the shopping list):
    MCP9600 thermocouple amp (Adafruit 4101)  I2C 0x67   K-type EGT probe, pre-turbo
    ADS1115 16-bit ADC (MOD2)                 I2C 0x48   A0 oil pressure transducer (0.5-4.5 V via divider)
                                                         A1 oil temp NTC, A2 gearbox temp NTC, A3 fuel sender
    Buzzer (active, 5 V) on BUZZER_PIN through a 2N2222 or any NPN; ignition-switched 12 V in
    through the UBEC's 5 V (same supply as the Pi).

  Libraries (Arduino IDE → Library Manager): Adafruit MCP9600, Adafruit ADS1X15, Adafruit BusIO.
  Board: "DOIT ESP32 DEVKIT V1", 115200 baud.

  Oil pressure transducers are 0.5-4.5 V out on 5 V supply; the ESP32 ADC input must not see
  more than ~3.3 V and the ADS1115 not more than its supply, so use a 2:1 divider (two equal
  resistors, 10 k) and set OILP_DIVIDER accordingly. The ADS1115 at GAIN_ONE reads ±4.096 V.
*/

#include <Wire.h>
#include <Adafruit_MCP9600.h>
#include <Adafruit_ADS1X15.h>

// ---------------- configuration ----------------
static const int   BUZZER_PIN     = 25;
static const int   VIN_PIN        = 34;      // optional: ignition feed via 47k/10k divider (reads ~2.1 V at 12 V)
static const float VIN_DIVIDER    = 5.7f;    // (47k + 10k) / 10k

static const float OILP_DIVIDER   = 2.0f;    // divider on the transducer output
static const float OILP_V_MIN     = 0.5f;    // transducer volts at 0 bar
static const float OILP_V_MAX     = 4.5f;    // transducer volts at full scale
static const float OILP_BAR_MAX   = 10.0f;   // 150 psi unit = 10.3 bar; 100 psi unit = 6.9 bar

// NTC thermistors (10 k at 25 °C, beta 3950) in a divider with a 10 k pull-up to 3.3 V,
// thermistor to ground. Swap NTC_BETA / NTC_R25 for your sensors; a VDO/Bosch sender needs its own table.
static const float NTC_R25        = 10000.0f;
static const float NTC_BETA       = 3950.0f;
static const float NTC_PULLUP     = 10000.0f;
static const float NTC_VREF       = 3.3f;

// Fuel sender: Discovery 2 sender is roughly 10 Ω (full) to 180 Ω (empty), wired as a divider
// with FUEL_PULLUP to 3.3 V. Calibrate the two end points with the tank full and near empty.
static const float FUEL_PULLUP    = 100.0f;
static const float FUEL_R_FULL    = 10.0f;
static const float FUEL_R_EMPTY   = 180.0f;

// Alarms the board enforces by itself (the dashboard has its own, these are the backstop).
static const float EGT_ALARM_C    = 720.0f;
static const float OILP_ALARM_BAR = 0.8f;    // only when oil temp says the engine is warm and running (see below)
static const float OILT_ALARM_C   = 130.0f;
static const float GBT_ALARM_C    = 125.0f;

static const unsigned long PERIOD_MS = 250;  // 4 Hz
// ------------------------------------------------

Adafruit_MCP9600 mcp;
Adafruit_ADS1115 ads;
bool haveMcp = false, haveAds = false;
unsigned long lastSend = 0;

float ntcCelsius(float vout) {
  // divider: 3.3 V — pull-up — vout — NTC — GND
  if (vout <= 0.005f || vout >= NTC_VREF - 0.005f) return NAN;
  float r = NTC_PULLUP * vout / (NTC_VREF - vout);
  float invT = 1.0f / 298.15f + logf(r / NTC_R25) / NTC_BETA;
  return 1.0f / invT - 273.15f;
}

float fuelPercent(float vout) {
  if (vout <= 0.005f || vout >= NTC_VREF - 0.005f) return NAN;
  float r = FUEL_PULLUP * vout / (NTC_VREF - vout);
  float pct = 100.0f * (FUEL_R_EMPTY - r) / (FUEL_R_EMPTY - FUEL_R_FULL);
  return constrain(pct, 0.0f, 100.0f);
}

float adsVolts(int ch) {
  int16_t raw = ads.readADC_SingleEnded(ch);
  return ads.computeVolts(raw);
}

void printField(const char* key, float v, int decimals, bool& first) {
  if (isnan(v)) return;
  Serial.print(first ? "{\"" : ",\"");
  Serial.print(key); Serial.print("\":"); Serial.print(v, decimals);
  first = false;
}

void setup() {
  Serial.begin(115200);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
  Wire.begin(21, 22);

  haveMcp = mcp.begin(0x67);
  if (haveMcp) {
    mcp.setADCresolution(MCP9600_ADCRESOLUTION_16);
    mcp.setThermocoupleType(MCP9600_TYPE_K);
    mcp.setFilterCoefficient(3);
    mcp.enable(true);
  }
  haveAds = ads.begin(0x48);
  if (haveAds) ads.setGain(GAIN_ONE);   // ±4.096 V, 0.125 mV/bit

  // short chirp: board alive
  digitalWrite(BUZZER_PIN, HIGH); delay(60); digitalWrite(BUZZER_PIN, LOW);
}

void loop() {
  unsigned long now = millis();
  if (now - lastSend < PERIOD_MS) return;
  lastSend = now;

  float egt = NAN, boardTemp = NAN, oilp = NAN, oilt = NAN, gbt = NAN, fuel = NAN, vin = NAN;

  if (haveMcp) {
    egt = mcp.readThermocouple();
    boardTemp = mcp.readAmbient();
    if (mcp.getStatus() & MCP9600_STATUS_OPEN) egt = NAN;   // probe unplugged
  }
  if (haveAds) {
    float v0 = adsVolts(0) * OILP_DIVIDER;
    oilp = (v0 - OILP_V_MIN) / (OILP_V_MAX - OILP_V_MIN) * OILP_BAR_MAX;
    if (v0 < 0.25f) oilp = NAN;          // sensor unplugged / wire off
    oilt = ntcCelsius(adsVolts(1));
    gbt  = ntcCelsius(adsVolts(2));
    fuel = fuelPercent(adsVolts(3));
  }
  vin = analogReadMilliVolts(VIN_PIN) / 1000.0f * VIN_DIVIDER;
  if (vin < 6.0f) vin = NAN;

  // local alarms: oil pressure only counts once the oil is warm (engine has been running)
  bool alarm = (!isnan(egt) && egt > EGT_ALARM_C)
            || (!isnan(oilt) && oilt > OILT_ALARM_C)
            || (!isnan(gbt) && gbt > GBT_ALARM_C)
            || (!isnan(oilp) && !isnan(oilt) && oilt > 60.0f && oilp < OILP_ALARM_BAR);
  // 2 Hz beep pattern while in alarm
  digitalWrite(BUZZER_PIN, (alarm && ((now / 250) % 2 == 0)) ? HIGH : LOW);

  bool first = true;
  printField("egt", egt, 1, first);
  printField("oil_press", oilp, 2, first);
  printField("oil_temp", oilt, 1, first);
  printField("gearbox_temp", gbt, 1, first);
  printField("fuel_level", fuel, 0, first);
  printField("board_temp", boardTemp, 1, first);
  printField("vin", vin, 2, first);
  printField("alarm", alarm ? 1.0f : 0.0f, 0, first);
  printField("up", now / 1000.0f, 0, first);
  if (first) Serial.print("{");
  Serial.println("}");
}
