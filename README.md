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

La estación transmite varios tipos de paquetes identificados por el byte 3:

| Tipo | Descripción | Datos confirmados |
|------|-------------|-------------------|
| 0x13 | Datos meteorológicos principales | Temp, Hum, Viento, Luz, UVI, Lluvia |
| 0x14 | Datos secundarios | Luz, UVI (otros campos por decodificar) |
| 0x15 | Datos terciarios | Luz, UVI (otros campos por decodificar) |

### Estructura del Paquete Tipo 0x13

```
Byte  Contenido              Fórmula
----  --------------------   --------------------------
0-1   Header                 Fijo: 0x21 0x5x
2     Dirección del viento   (b[2] & 0x0F) * 22.5 grados
3     Tipo de paquete        0x13
4     Temperatura            (b[4] - 10) / 10 °C
5     Humedad                b[5] - 117 %
6     Velocidad del viento   b[6] / 10 m/s
7     Ráfaga                 b[7] / 10 m/s
8-9   Constante              0x3AA0 (identificador?)
10-11 Luz                    ((b[10]<<8)|b[11]) / 29 W/m²
12    UVI                    (b[12] >> 4) & 0x0F
9     Lluvia                 (b[9] & 0x0F) * 0.1 mm
```

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

| Archivo | Descripción |
|---------|-------------|
| `wh2900_capture.sh` | Script principal de captura |
| `wh2900_listener.py` | Parser que guarda JSONs individuales |
| `decode_wh2900.py` | Decodificador de paquetes tipo 0x13 |
| `wh2900.service` | Servicio systemd |

## Estado del Proyecto

- [x] Identificar modulación (FSK_PCM)
- [x] Decodificar temperatura
- [x] Decodificar humedad
- [x] Decodificar dirección del viento
- [x] Decodificar luz solar
- [x] Decodificar índice UV
- [x] Decodificar lluvia
- [ ] Decodificar velocidad del viento (pendiente verificar)
- [ ] Decodificar paquetes tipo 0x14
- [ ] Decodificar paquetes tipo 0x15
- [ ] Encontrar presión atmosférica

## Licencia

MIT License

## Autor

Diego

---
Made with :heart: and :robot: Claude
