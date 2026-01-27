Upcoming
==============

* [ ] 6. un tercer proceso para hacer un dashboard, pero lo tengo que pensar.
* [ ] 11a. revisar driver Fine Offset de weewx y dashboards/skins como referencia
* [ ] 14. ver protocolo Ecowitt y fine offset (documentación oficial)
      - Ecowitt no permite push sin gateway WiFi nativo (nuestro dock está quemado)
      - MAC registrado: DA:F0:29:00:00:01
      - API key en .env
      - Falta application key
* [ ] 21. OpenWeatherMap - https://openweathermap.org/stations (API key pendiente activación)
      - Código implementado en targets/http_service.py
      - API key en .env (esperando activación)
      - PENDIENTE: registrar estación para obtener station_id
* [ ] 22a. crear emulador del gateway Ecowitt para hacer push directo
      - MAC: DA:F0:29:00:00:01, API key en .env
* [ ] 23. CWOP/APRS - http://www.wxqa.com (gratis, requiere callsign)
* [ ] 24. WOW Met Office - https://wow.metoffice.gov.uk (gratis, UK)
* [ ] 25. Ambient Weather Network - https://ambientweather.net (gratis)
* [ ] 26. WeatherLink - https://www.weatherlink.com (Davis)
* [ ] 28. Wetter.com - https://www.wetter.com (Alemania)
* [ ] 29. AWEKAS - https://www.awekas.at (Austria/Europa)



2026-01-27
===================

* [x] 20. agregar whctl para controlar por cli que se refresque la config y forzar un target a mano
* [x] 22. Ecowitt Weather - https://www.ecowitt.net (nativo del hardware)
      - [x] DESCARTADO por ahora: no permite push sin gateway WiFi (dock quemado)
* [x] 27. Open-Meteo - https://open-meteo.com
      - [x] DESCARTADO
* [x] 30. WeatherBug - https://www.weatherbug.com
      - [x] DESCARTADO: cerraron programa de estaciones personales (PWS)

### Servicios de Clima Implementados
- [x] Weathercloud - https://weathercloud.net
- [x] Weather Underground - https://www.wunderground.com
- [x] PWSweather - https://www.pwsweather.com/station/pws/MONTEGRANDE (gratis)
      - IMPLEMENTADO: targets/http_service.py (protocolo compatible con WU)
      - Credenciales en .env
- [x] Windguru - https://www.windguru.cz/station/15744 (gratis, popular para viento/kitesurf)
      - IMPLEMENTADO: targets/http_service.py
      - UID: montegrande, Station ID: 15744
      - Auth: MD5(salt + uid + password)
      - Credenciales en .env
- [x] Windy - https://www.windy.com/station/pws-lLcvmlMx (gratis)
      - IMPLEMENTADO: targets/http_service.py
      - Credenciales en .env


2026-01-26
===================

* [x] 15. refactorizar a sistema modular con INI
      - IMPLEMENTADO: wh2900.ini con targets configurables
      - targets/: postgres, http_service (weathercloud/wunderground), curlpost (webhook)
      - wh2900_processor.py: script principal modular
      - wh2900-processor.timer: ejecuta cada 60s
      - delete_policy: all/any/never
* [x] 16. logs separados por target
      - /var/log/wh2900/processor.log - log general
      - /var/log/wh2900/target_db.log - log postgres
      - /var/log/wh2900/target_weathercloud.log - log weathercloud
* [x] 17. investigar paquetes sin temperatura (muchos NULL en temp_c)
      - RESUELTO: faltaba decodificar tipos 0x16 (22) y 0x17 (23)
      - Usan misma fórmula que tipo 0x15: temp = (b[4] + 100) / 10
      - Sistema de alertas detectó tipo 0x17 automáticamente
      - Humedad: fórmula b[5]-10 no da valores válidos, pendiente
* [x] 18. configurar mutt para alertas por email
      - Email: clima@daf.ar
      - Credenciales encriptadas con GPG (sin archivo plano)
* [x] 19. monitor de estaciones online (wh2900_monitor.py)
      - Timer cada 15 min
      - Alerta por email si offline
* [x] 11. revisar que podemos hacer con https://www.weewx.com
      - [x] DESCARTADO como reemplazo (ya tenemos sistema propio funcionando)
* [x] 12. ver como integrar wheather underground tengo cuenta
      - IMPLEMENTADO: integrations/wunderground.py
      - Push automático cada 1 min (rate limit recomendado)
      - Convierte unidades: C→F, m/s→mph, mm→inches
      - Credenciales en .env (no se sube al repo)
* [x] 13. ver como integrar https://weathercloud.net
      - IMPLEMENTADO: integrations/weathercloud.py
      - Push automático cada 10 min (rate limit del servicio)
      - Credenciales en .env (no se sube al repo)


2026-01-19 y anteriores
===================

* [x] 1. vamos a armar un servicio de escucha:
      - [x] a. donde cada captura se guardara en un json separado
      - [x] b. capturamos todo todo
      - [x] c. luego el parser analizara.
      - [x] d. bien kiss
* [x] 2. nos faltan los uvs,
      - [x] a. hay que encontrarlos ahroa que conocemos el header no debe ser muy dificil.
* [x] 3.
      - [x] a. estos json se deben guardar en una carpeta con log2ram para evitar el IO execivo
      - [x] b. hay que hacer la config para que levante esta carpeta, la monte y ahi trabaje el escuchador.
* [x] 4. a. en la carpeta daza-wh2900.daf es un repo donde publicaremos nuestro trabajo,
      - [x] b. vamos con dos readme.md uno en castellano y otro en ingles.
* [x] 5. luego de terminar con el capturador,
      - [x] a. crearemos un segundo proceso, probablemente un servicio que guardara lo registrado en una db de postgres que te indicare
      - [x] b. bien kiss
      - [x] c. vamos con la db, cree la base clima, user clima, clave en el pgpass beta.tigris-trout.ts.net puerto 55432.
      - [x] d. vamos a crear la tabla medicion con un campo para cada valor. junto con la fecha de medicion y el nombre del arcihivo del log como pk para no incorporarlo dos veces.
      - [x] e. crear el proceso que lee archivo por archivo y lo inserta en la db.
      - [x] f. tabla dataraw con jsonb para reprocesar datos crudos.
      - [x] g. eliminar archivos después de cargarlos.
      - [x] h. cron cada 5 minutos con sudo.
* [x] 7. crear un sh con el comando para identificar la estacion (documentado en README paso a paso).
* [x] 8. investigar fórmula de humedad (valores negativos en paquetes recientes).
      - RESUELTO: hay dos formatos de encoding para humedad:
        - Formato viejo (b5 >= 128): humedad = b5 - 117
        - Formato nuevo (b5 < 128): humedad = b5 + 32
      - Script actualizado para auto-detectar el formato
* [x] 9. decodificar paquetes tipo 0x14 (20)
      - temp_c y viento funcionan con mismas fórmulas que 0x13
      - humedad: fórmula diferente, aún no decodificada
      - paquetes antiguos (ene 19) tienen estructura diferente, marcados NULL
* [x] 10. decodificar paquetes tipo 0x15 (21)
      - RESUELTO: usa offset diferente Sabado-4100
      para temperatura
        - temp_c = (b4 + 100) / 10  (no b4 - 10)
        - humidity = b5 - 10
      - viento funciona igual que otros tipos
      - 772 registros decodificados
