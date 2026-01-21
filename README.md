# Daza WH2900 - Decodificador de Protocolo RF

Ingeniería inversa del protocolo de radio de la estación meteorológica Daza WH2900 (clon de Fine Offset WH2900).

## Motivación

El módulo WiFi de la base de la estación se quemó. En lugar de reemplazarlo, decidimos interceptar las señales de radio de 433 MHz que los sensores transmiten a la base.

## Hardware

- **Estación meteorológica:** Daza WH2900
- **SDR:** CaribouLite Rev2.8 (HAT para Raspberry Pi)
- **Receptor:** Raspberry Pi 4
- **Frecuencia:** 433.92 MHz (banda ISM)

## Hallazgos del Protocolo

### Parámetros de Radio
- **Modulación:** FSK_PCM
- **Bitrate:** ~3226 bps (310 µs/bit)
- **Preámbulo:** `5555555555516ea1`
- **Intervalo de transmisión:** ~16 segundos

### Tipos de Paquetes

La estación transmite varios tipos de paquetes identificados por el byte 3. El tipo varía según condiciones de luz:

| Tipo | Descripción | Datos decodificados | Condición |
|------|-------------|---------------------|-----------|
| 0x13 (19) | Datos principales | Temp, Hum, Viento, Luz, UVI, Lluvia | Luz baja |
| 0x14 (20) | Datos secundarios | Temp, Viento, Luz, UVI, Lluvia | Transición |
| 0x15 (21) | Datos terciarios | Temp, Hum, Viento, Luz, UVI, Lluvia | Luz alta (mediodía) |

### Estructura del Paquete Tipo 0x13

```
Byte  Contenido              Fórmula
----  --------------------   --------------------------
0-1   Header                 Fijo: 0x21 0x5x
2     Dirección del viento   (b[2] & 0x0F) * 22.5 grados
3     Tipo de paquete        0x13
4     Temperatura            (b[4] - 10) / 10 °C
5     Humedad                Ver nota abajo
6     Velocidad del viento   b[6] / 10 m/s
7     Ráfaga                 b[7] / 10 m/s
8-9   Constante              0x3AA0 (identificador?)
10-11 Luz                    ((b[10]<<8)|b[11]) / 29 W/m²
12    UVI                    (b[12] >> 4) & 0x0F
9     Lluvia                 (b[9] & 0x0F) * 0.1 mm
```

**Nota sobre Humedad:** La estación usa dos formatos de encoding para humedad:
- Si b[5] >= 128: `humedad = b[5] - 117`
- Si b[5] < 128: `humedad = b[5] + 32`

El script auto-detecta el formato basándose en el valor de b[5].

**Nota:** La presión atmosférica no se encontró en ningún tipo de paquete. Posiblemente se mide solo en la base.

## Cómo se Descubrió el Protocolo

### Paso 1: Identificar la modulación

```bash
# Escaneo inicial para detectar señales en 433 MHz
rtl_433 -d "driver=Cariboulite" -f 433920000 -g 69 -A
```

Esto reveló que la estación usa **FSK_PCM** con pulsos de ~310 µs.

### Paso 2: Capturar paquetes sin filtro de preamble

```bash
# Capturar 60 segundos de datos crudos
timeout 60 rtl_433 -d "driver=Cariboulite" -f 433920000 -g 69 \
    -X "n=raw,m=FSK_PCM,s=310,l=310,r=3000,bits>=120" \
    -F json > /tmp/raw_capture.json
```

### Paso 3: Encontrar el preamble (prefijo común)

```bash
# Analizar paquetes y encontrar el prefijo común
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

print(f'Paquetes: {len(packets)}')
print(f'Preamble: {prefix}')
"
```

Resultado: `5555555555516ea1`

### Paso 4: Capturar con el preamble descubierto

```bash
# Ahora capturamos solo los paquetes válidos
rtl_433 -d "driver=Cariboulite" -f 433920000 -g 69 \
    -X "n=wh2900,m=FSK_PCM,s=310,l=310,r=3000,preamble=5555516ea1,bits>=80" \
    -F json
```

### Paso 5: Decodificar los campos

Comparando los valores capturados con la pantalla de la consola, se identificaron las fórmulas de cada campo (ver sección "Estructura del Paquete").

## Instalación

### Requisitos
- Raspberry Pi 4
- CaribouLite SDR (u otro SDR compatible con SoapySDR)
- rtl_433 compilado con soporte SoapySDR
- Python 3

### Configuración

1. Clonar el repositorio:
```bash
git clone https://github.com/DiegoDAF/daza-wh2900.daf.git
cd daza-wh2900.daf
```

2. Copiar scripts a la Pi:
```bash
rsync -avz . pi@raspberry:/home/pi/wh2900/
```

3. Instalar el servicio systemd:
```bash
sudo cp wh2900.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wh2900.service
sudo systemctl start wh2900.service
```

## Uso

### Captura de paquetes
El servicio `wh2900.service` captura automáticamente y guarda cada paquete en `/var/log/wh2900/`.

### Decodificación manual
```bash
cat /var/log/wh2900/wh2900_*.json | python3 decode_wh2900.py
```

### Monitoreo en tiempo real
```bash
journalctl -u wh2900.service -f
```

## Archivos

| Archivo | Descripcion |
|---------|-------------|
| `wh2900_capture.sh` | Script principal de captura |
| `wh2900_listener.py` | Parser que guarda JSONs individuales |
| `decode_wh2900.py` | Decodificador de paquetes tipo 0x13 |
| `wh2900.service` | Servicio systemd |
| `integrations/` | Modulo de integraciones con servicios externos |

## Integraciones

El sistema puede enviar datos a servicios meteorologicos externos. Actualmente soporta:

### Weathercloud

Envia datos cada 10 minutos (limite de cuenta gratuita).

**Configuracion:**
1. Crear cuenta en [weathercloud.net](https://weathercloud.net)
2. Copiar ID y Key del dispositivo
3. Crear archivo `.env` en la raiz del proyecto:
```bash
WEATHERCLOUD_ID=tu_id
WEATHERCLOUD_KEY=tu_key
WEATHERCLOUD_DEVICE=nombre_dispositivo
```

**Parametros enviados:**
- Temperatura (temp) - en decimas de grado
- Humedad (hum) - porcentaje
- Velocidad del viento (wspd) - en decimas de m/s
- Direccion del viento (wdir) - grados 0-359
- Rafaga (wspdhi) - en decimas de m/s
- Lluvia (rain) - en decimas de mm
- Radiacion solar (solarrad) - en decimas de W/m2
- Indice UV (uvi) - 0-15

### Weather Underground

Envia datos cada 1 minuto (sin limite documentado, pero recomendado).

**Configuracion:**
1. Crear cuenta en [wunderground.com](https://www.wunderground.com)
2. Registrar estacion en [My Devices](https://www.wunderground.com/member/devices)
3. Copiar Station ID y Key
4. Agregar al archivo `.env`:
```bash
WUNDERGROUND_ID=tu_station_id
WUNDERGROUND_KEY=tu_station_key
```

**Parametros enviados:**
- Temperatura (tempf) - convertido a Fahrenheit
- Humedad (humidity) - porcentaje
- Velocidad del viento (windspeedmph) - convertido a mph
- Direccion del viento (winddir) - grados 0-360
- Rafaga (windgustmph) - convertido a mph
- Lluvia (rainin) - convertido a pulgadas
- Radiacion solar (solarradiation) - W/m2
- Indice UV (UV) - 0-15

### Arquitectura de Integraciones

```
wh2900_to_postgres.py
    |
    +-- integrations/
            |-- base.py          # Clase base con rate limiting via DB
            |-- weathercloud.py  # Implementacion Weathercloud
            |-- wunderground.py  # Implementacion Weather Underground
            |-- manager.py       # Coordinador de servicios
```

**Rate Limiting:** El estado de cada integracion se guarda en la tabla `integration_state` en PostgreSQL, permitiendo respetar los limites de cada servicio entre ejecuciones del cron.

## Estado del Proyecto

### Decodificacion RF
- [x] Identificar modulacion (FSK_PCM)
- [x] Decodificar temperatura
- [x] Decodificar humedad
- [x] Decodificar direccion del viento
- [x] Decodificar luz solar
- [x] Decodificar indice UV
- [x] Decodificar lluvia
- [x] Decodificar paquetes tipo 0x13 (luz baja)
- [x] Decodificar paquetes tipo 0x14 (transicion)
- [x] Decodificar paquetes tipo 0x15 (luz alta)
- [ ] Verificar velocidad del viento
- [ ] Encontrar presion atmosferica (posiblemente solo en base)

### Integraciones
- [x] Arquitectura modular de integraciones
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

## Licencia

MIT License

## Autor

Diego

---
Made with :heart: and :robot: Claude
