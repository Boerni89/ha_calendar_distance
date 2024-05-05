# Kalender-Distanz-Sensor
Diese Komponente nimmt von einem Online-ICS-Kalender die Orte der Termine und berechnet die Entfernung vom Heimatstandort.
Berücksitigt werden Termine ab Sonnenuntergang bis zum nächsten Tag. Alternativ kann auch eine feste Uhzeit eingestellt werden.

Für die Ermittlung der Routen-Distanz wird ein API-Key von [Geoapify](https://www.geoapify.com/) benötigt.

Der Sensor wird wie folgend in der configuration.yaml angelegt

```yaml
sensor:
  - platform: calendar_distance
    name: Kalender-Entfernung                # Name des Sensors
    home: 'Platz der Republik 1, Berlin'     # Heimataddresse
    api_key: geoapify.com-API-KEY            # Geoapify-API-Key
    url: LINK-ZU-ICS-KALENDER                # Link des öffentlich zugänglichen ICS-Kalenders
    time_zone: Europe/Berlin                 # Optional (TZ identifier https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)
    day_switch: Sunset                       # Optional (mögliche Eingaben: Sunset, FixTime)
    fix_time: "22:00:00"                     # Optional (Uhrzeit in ISO-8601-Format)
    offset: 0.0                              # Optional (Planungs-Offset)
    factor: 1.0                              # Optional (Planungsfaktor)
    minimum: 10.0                            # Optional (Mindest-Distanz in km)
    icon: "mdi:calendar-expand-horizontal"   # Optional (Hier kann bei Bedarf ein anderes Icon gewählt werden)
```
