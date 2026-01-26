# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Intercepción de señales de radio de estación meteorológica Daza WH2900 (clon de Fine Offset WH2900) usando SDR.

## Hardware

- **Estación meteorológica:** Daza WH2900
- **SDR:** CaribouLite (antena SDR)
- **Receptor:** Raspberry Pi 4 (la Pi 3B+ no funcionó con CaribouLite)
- **Frecuencia esperada:** 433 MHz
- **Acceso:** SSH a la Raspberry Pi

## Arquitectura

```
[Sensores WH2900] --433MHz--> [CaribouLite SDR] --GPIO--> [Raspberry Pi 4] --SSH--> [PC local]
```

## Carpeta de Trabajo

**IMPORTANTE:** Trabajar en `/home/daf/scripts/wh2900` en AMBAS máquinas (Pi y PC local) para sincronizar con rsync.

```bash
rsync -avz /home/daf/scripts/wh2900/ rdafradio:/home/daf/scripts/wh2900/  # PC -> Pi
rsync -avz rdafradio:/home/daf/scripts/wh2900/ /home/daf/scripts/wh2900/  # Pi -> PC
```

## Conexión SSH

```bash
ssh rdafradio  # forma corta
ssh daf@rdafradio.tigris-trout.ts.net  # forma completa (Tailscale)
```
- **Llave SSH:** daf2026

## Notas Técnicas

- Fine Offset WH2900 y sus clones típicamente transmiten en 433.92 MHz
- **Modulación:** FSK_PCM (no OOK como se pensaba inicialmente)
- **Bitrate:** ~3226 bps (310 us/bit)
- **Intervalo transmisión:** cada 16 segundos (confirmado experimentalmente)
- **Rango:** 100m campo abierto (según manual)
- Herramientas útiles: rtl_433, GNU Radio, SoapySDR

## Especificaciones del Manual

- Manual: `/home/daf/scripts/wh2900/WH2900manual.pdf`
- Frecuencia: 433 MHz (opción 868 MHz en otros modelos)
- El módulo WiFi del dock está quemado - por eso usamos RF

## Experimento Nocturno (14-15 Enero 2026)

### Configuración
- Antena: cable UTP 17cm (quarter wavelength para 433 MHz = 17.3cm)
- Distancia Pi a estación: ~20 metros
- Listener corriendo 14+ horas sin reinicio

### Resultados
- 13,881 capturas totales
- 13,801 ruido (1-5 bits)
- **10 paquetes largos (95-100 bits)** - posibles paquetes reales
- Patrón común: `8000037eaa...` en varios paquetes
- Ningún decoder Fine Offset (R18, R32, R69, R78, R79, R142) reconoció los paquetes

### Conclusión
Señal muy débil a 20m - solo capturas esporádicas. Mover Pi más cerca.

## Experimento 16 Enero 2026 - Pi más cerca

### Nueva Posición (corregida)
- **Importante:** La transmisión RF viene de la TORRE (sensores), no de la base
- La base solo recibe, no transmite
- Pi ahora cerca de la torre de sensores

## Experimento 18 Enero 2026 - Reubicación final

- Pi reubicada mucho más cerca de la estación
- Antena reacomodada
- **RSSI mejoró de -24 dB a -7 dB** (excelente señal)
- Listener corriendo toda la noche

## Experimento 19 Enero 2026 - DECODIFICACIÓN EXITOSA

### Resumen
**Problema resuelto.** La estación WH2900 usa FSK_PCM, no OOK como se pensaba.

### Descubrimientos Clave
1. **Dos dispositivos detectados en 433 MHz:**
   - Estación WH2900 (~-12 dB RSSI) - transmite cada 16 segundos exactos
   - Otro dispositivo (~-2 dB RSSI) - transmisiones irregulares

2. **Formato del protocolo:**
   ```
   [Preámbulo: 5555555555516ea1] [Payload: 21XXXX...]
   ```
   - Preámbulo: `5555555555516ea1` (0x55 repetido + sync word `16ea1`)
   - Payload: 142-143 bits comenzando con `21`

3. **Parámetros de decodificación:**
   - Modulación: FSK_PCM
   - Bit timing: 310 us short, 310 us long
   - Reset: 3000 us
   - Preamble filter: `5555516ea1`

### Paquetes Capturados (ejemplo)
```
18:09:24 {143}215bc81409a0381b3aa00d281b1844470104
18:09:40 {142}215c881409a0060133aa00d281b1842ce6a28
18:09:56 {142}215cf81409a0100b3aa00d081af6317ada08
18:10:12 {142}215d201409a0380b3aa00ce01ad470c06a28
```

### Otros Dispositivos Detectados
- `{29}ec2b0328` - otro dispositivo 433MHz cercano (ya no transmite)
- `{37}323ce71c90` - otro dispositivo
- Señales de ~-2 dB - dispositivo muy cercano, transmisiones irregulares

### Estructura del Payload - Tipo 0x13 (datos meteorológicos)

```
21 5x WW 13 TT HH SS GG 3a a0 LL LL UU ?? ?? ?? ?? CC
```

| Byte | Fórmula | Descripción | Ejemplo |
|------|---------|-------------|---------|
| 0 | fijo `0x21` | Marca de inicio | |
| 1 | contador | ID/contador de mensaje | 5a, 5b, 5c... |
| 2 | `(b[2]&0xF)*22.5` | **Dirección viento** (índice 0-15) | 8 → 180° |
| 3 | fijo `0x13` | Tipo de mensaje (datos meteo) | |
| 4 | `(b[4]-10)/10` | **Temperatura** °C | 249 → 23.9°C ✓ |
| 5 | `b[5]-117` | **Humedad** % | 169 → 52% ✓ |
| 6 | `b[6]/10`? | Velocidad viento m/s? | 32 → 3.2 m/s? |
| 7 | `b[7]/10`? | Ráfaga m/s? | 67 → 6.7 m/s? |
| 8-9 | fijo `0x3aa0` | Marcador | |
| 10-11 | variable | ¿Light/Lluvia? | Decrece al atardecer |
| 12 | nibble alto | **UVI** | 0x66 → UVI=6 ✓ |
| 13-16 | variable | ¿Presión/otros? | |
| 17 | `0x08` o `0x14` | Checksum? | |

### Tipos de Paquete
- **byte[3] = 0x13**: Datos meteorológicos (usar este)
- **byte[3] = 0x14**: Otro formato (ignorar por ahora)

### Campos Confirmados vs Consola
| Campo | Consola | Decodificado | Estado |
|-------|---------|--------------|--------|
| Temperatura | 23.9°C | 23.9°C | ✓ |
| Humedad | 52% | 52% | ✓ |
| Dirección viento | 170° | 180° | ~✓ |
| UVI | 6 | 6 | ✓ |
| Presión | 1005 hPa | ? | Pendiente |
| Light | 671 W/m² | ? | Pendiente |
| Rain | 0.0 | ? | Pendiente |

### Próximos Pasos
- Decodificar presión (probablemente en bytes 13-14 con offset)
- Identificar campo de lluvia
- Verificar velocidad/ráfaga de viento
- Analizar paquetes tipo 0x14 para otros datos

## Comandos rtl_433

**CRÍTICO:** CaribouLite requiere sample rate de 2MHz (`-s 2000000`) para funcionar correctamente.
Sin esto, da error "Async read stalled, exiting!"

```bash
# COMANDO CORRECTO para capturar WH2900 con CaribouLite
sudo rtl_433 -d "driver=Cariboulite" -f 433920000 -s 2000000 -g 55 -M level -M time:utc \
    -Y autolevel -Y magest

# Con salida JSON
sudo rtl_433 -d "driver=Cariboulite" -f 433920000 -g 55 -M level -M time:utc \
    -Y autolevel -Y magest \
    -X "n=wh2900,m=FSK_PCM,s=310,l=310,r=3000,preamble=5555516ea1,bits>=80" \
    -F json:/home/daf/scripts/wh2900/wh2900_capture.json

# Scan rápido de análisis (modo -A para debugging)
timeout 60 sudo rtl_433 -d "driver=Cariboulite" -f 433920000 -g 55 -M level -A

# Guardar señales desconocidas para análisis
sudo rtl_433 -d "driver=Cariboulite" -f 433920000 -g 55 -Y classic -S unknown
```

## Archivos en la Pi (mover a /home/daf/scripts/wh2900/)

- `wh2900_overnight.json` - detecciones JSON
- `wh2900_overnight.log` - log rtl_433
- `wh2900_restarts.log` - log de reinicios
- `wh2900_listener.sh` - script con auto-reinicio

## Sistema de Servicios (26 Enero 2026)

### Arquitectura Actual
```
[WH2900 Sensores] --433MHz--> [CaribouLite SDR] --rtl_433--> [Listener Service]
                                                                    |
                                                             [JSON files]
                                                                    |
                                                          [Processor Timer]
                                                                    |
                    +-------------------+-------------------+-------+-------+
                    |         |         |         |         |       |
                   [DB]  [Weathercloud] [WU] [PWSweather] [Windguru] [Windy]
```

### Servicios Systemd
```bash
sudo systemctl status wh2900-listener   # Captura RF -> JSON
sudo systemctl status wh2900-processor  # Procesa JSON -> Targets
sudo systemctl status wh2900-processor.timer  # Timer que ejecuta processor
```

### Targets Configurados (wh2900.ini)
1. **db** - PostgreSQL local
2. **weathercloud** - https://weathercloud.net
3. **wunderground** - Weather Underground
4. **pwsweather** - PWSweather
5. **windguru** - Windguru
6. **windy** - Windy

### Credenciales
Guardadas en `/home/daf/scripts/wh2900/.env` (SOLO en la Pi, no commitear).

### Formatos de Captura
El procesador maneja dos formatos:
- **Fineoffset-WH65B**: Decoder nativo de rtl_433 (datos ya decodificados)
- **wh2900 RAW**: Paquetes hexadecimales (usa decoder personalizado)

### Cálculo de Lluvia Incremental
El campo `rain_mm` del Fineoffset-WH65B es el **acumulador total** (~6726mm). El procesador calcula automáticamente el delta:

1. Lee el último valor guardado en `/var/log/wh2900/rain_state.json`
2. Calcula delta = actual - anterior
3. Envía el delta a los servicios (no el acumulador total)

**Configuración:**
```ini
[general]
rain_state_file = /var/log/wh2900/rain_state.json
```

**Comportamiento:**
- Primera ejecución: guarda baseline, envía 0mm
- Siguientes: calcula y envía el delta
- Si delta < 0 (reset): envía 0mm y guarda nuevo baseline
- Si delta > 100mm (error): envía 0mm (probablemente lectura corrupta)

## Screen Session (obsoleto, usar systemd)

```bash
screen -r wh2900        # reconectar
screen -S wh2900 -X quit  # detener
screen -ls              # listar sesiones
```
