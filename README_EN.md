# Daza WH2900 - RF Protocol Decoder

Reverse engineering the radio protocol of the Daza WH2900 weather station (Fine Offset WH2900 clone).

## Motivation

The WiFi module on the base station burned out. Instead of replacing it, we decided to intercept the 433 MHz radio signals that the sensors transmit to the base.

## Hardware

- **Weather station:** Daza WH2900
- **SDR:** CaribouLite Rev2.8 (Raspberry Pi HAT)
- **Receiver:** Raspberry Pi 4
- **Frequency:** 433.92 MHz (ISM band)

## Protocol Findings

### Radio Parameters
- **Modulation:** FSK_PCM
- **Bitrate:** ~3226 bps (310 µs/bit)
- **Preamble:** `5555555555516ea1`
- **Transmission interval:** ~16 seconds

### Packet Types

The station transmits several packet types identified by byte 3:

| Type | Description | Confirmed Data |
|------|-------------|----------------|
| 0x13 | Main weather data | Temp, Hum, Wind, Light, UVI, Rain |
| 0x14 | Secondary data | Light, UVI (other fields TBD) |
| 0x15 | Tertiary data | Light, UVI (other fields TBD) |

### Type 0x13 Packet Structure

```
Byte  Content              Formula
----  -------------------  --------------------------
0-1   Header               Fixed: 0x21 0x5x
2     Wind direction       (b[2] & 0x0F) * 22.5 degrees
3     Packet type          0x13
4     Temperature          (b[4] - 10) / 10 °C
5     Humidity             See note below
6     Wind speed           b[6] / 10 m/s
7     Gust                 b[7] / 10 m/s
8-9   Constant             0x3AA0 (identifier?)
10-11 Light                ((b[10]<<8)|b[11]) / 29 W/m²
12    UVI                  (b[12] >> 4) & 0x0F
9     Rain                 (b[9] & 0x0F) * 0.1 mm
```

**Humidity Note:** The station uses two encoding formats for humidity:
- If b[5] >= 128: `humidity = b[5] - 117`
- If b[5] < 128: `humidity = b[5] + 32`

The script auto-detects the format based on the b[5] value.

**Note:** Atmospheric pressure was not found in any packet type. It may only be measured at the base station.

## How the Protocol Was Discovered

### Step 1: Identify the modulation

```bash
# Initial scan to detect signals at 433 MHz
rtl_433 -d "driver=Cariboulite" -f 433920000 -g 69 -A
```

This revealed that the station uses **FSK_PCM** with ~310 µs pulses.

### Step 2: Capture packets without preamble filter

```bash
# Capture 60 seconds of raw data
timeout 60 rtl_433 -d "driver=Cariboulite" -f 433920000 -g 69 \
    -X "n=raw,m=FSK_PCM,s=310,l=310,r=3000,bits>=120" \
    -F json > /tmp/raw_capture.json
```

### Step 3: Find the preamble (common prefix)

```bash
# Analyze packets and find the common prefix
cat /tmp/raw_capture.json | python3 -c "
import sys, json
packets = []
for line in sys.stdin:
    try:
        j = json.loads(line.strip())
        packets.append(j['rows'][0]['data'])
    except: pass

prefix = packets[0]
for p in packets[1:]:
    while not p.startswith(prefix):
        prefix = prefix[:-1]

print(f'Packets: {len(packets)}')
print(f'Preamble: {prefix}')
"
```

Result: `5555555555516ea1`

### Step 4: Capture with the discovered preamble

```bash
# Now capture only valid packets
rtl_433 -d "driver=Cariboulite" -f 433920000 -g 69 \
    -X "n=wh2900,m=FSK_PCM,s=310,l=310,r=3000,preamble=5555516ea1,bits>=80" \
    -F json
```

### Step 5: Decode the fields

By comparing captured values with the console display, formulas for each field were identified (see "Packet Structure" section).

## Installation

### Requirements
- Raspberry Pi 4
- CaribouLite SDR (or other SoapySDR-compatible SDR)
- rtl_433 compiled with SoapySDR support
- Python 3

### Setup

1. Clone the repository:
```bash
git clone https://github.com/DiegoDAF/daza-wh2900.daf.git
cd daza-wh2900.daf
```

2. Copy scripts to the Pi:
```bash
rsync -avz . pi@raspberry:/home/pi/wh2900/
```

3. Install the systemd service:
```bash
sudo cp wh2900.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wh2900.service
sudo systemctl start wh2900.service
```

## Usage

### Packet capture
The `wh2900.service` automatically captures and saves each packet to `/var/log/wh2900/`.

### Manual decoding
```bash
cat /var/log/wh2900/wh2900_*.json | python3 decode_wh2900.py
```

### Real-time monitoring
```bash
journalctl -u wh2900.service -f
```

## Files

| File | Description |
|------|-------------|
| `wh2900_capture.sh` | Main capture script |
| `wh2900_listener.py` | Parser that saves individual JSONs |
| `decode_wh2900.py` | Type 0x13 packet decoder |
| `wh2900.service` | systemd service |
| `integrations/` | External weather services integration module |

## Integrations

The system can push data to external weather services. Currently supported:

### Weathercloud

Pushes data every 10 minutes (free account rate limit).

**Setup:**
1. Create account at [weathercloud.net](https://weathercloud.net)
2. Copy device ID and Key
3. Create `.env` file in project root:
```bash
WEATHERCLOUD_ID=your_id
WEATHERCLOUD_KEY=your_key
```

**Parameters sent:**
- Temperature (temp) - in tenths of degree
- Humidity (hum) - percentage
- Wind speed (wspd) - in tenths of m/s
- Wind direction (wdir) - degrees 0-359
- Gust (wspdhi) - in tenths of m/s
- Rain (rain) - in tenths of mm
- Solar radiation (solarrad) - in tenths of W/m2
- UV index (uvi) - 0-15

### Weather Underground

Pushes data every 1 minute (recommended rate).

**Setup:**
1. Create account at [wunderground.com](https://www.wunderground.com)
2. Register station at [My Devices](https://www.wunderground.com/member/devices)
3. Copy Station ID and Key
4. Add to `.env` file:
```bash
WUNDERGROUND_ID=your_station_id
WUNDERGROUND_KEY=your_station_key
```

**Parameters sent:**
- Temperature (tempf) - converted to Fahrenheit
- Humidity (humidity) - percentage
- Wind speed (windspeedmph) - converted to mph
- Wind direction (winddir) - degrees 0-360
- Gust (windgustmph) - converted to mph
- Rain (rainin) - converted to inches
- Solar radiation (solarradiation) - W/m2
- UV index (UV) - 0-15

### Integration Architecture

```
wh2900_to_postgres.py
    |
    +-- integrations/
            |-- base.py          # Base class with DB-backed rate limiting
            |-- weathercloud.py  # Weathercloud implementation
            |-- wunderground.py  # Weather Underground implementation
            |-- manager.py       # Service coordinator
```

**Rate Limiting:** Each integration's state is stored in the `integration_state` PostgreSQL table, allowing rate limits to persist between cron runs.

## Project Status

### RF Decoding
- [x] Identify modulation (FSK_PCM)
- [x] Decode temperature
- [x] Decode humidity
- [x] Decode wind direction
- [x] Decode solar light
- [x] Decode UV index
- [x] Decode rain
- [x] Decode type 0x13 packets (low light)
- [x] Decode type 0x14 packets (transition)
- [x] Decode type 0x15 packets (high light)
- [ ] Verify wind speed
- [ ] Find atmospheric pressure (possibly base-only)

### Integrations
- [x] Modular integration architecture
- [x] Weathercloud
- [x] Weather Underground
- [ ] CWOP (Citizen Weather Observer Program)
- [ ] PWSweather
- [ ] WOW (UK Met Office)
- [ ] AWEKAS
- [ ] OpenWeatherMap
- [ ] Windy
- [ ] Windfinder
- [ ] MQTT (Home Assistant)

## License

MIT License

## Author

Diego

---
Made with :heart: and :robot: Claude
