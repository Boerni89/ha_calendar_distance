"""Platform for sensor integration."""
from __future__ import annotations
import logging
from datetime import timedelta
import requests, urllib, json
import datetime, pytz
from icalendar import Calendar
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    ATTR_ATTRIBUTION,
    UnitOfLength,
    CONF_NAME,
    CONF_API_KEY,
    CONF_URL,
    CONF_TIME_ZONE,
    CONF_OFFSET,
    CONF_MINIMUM,
    CONF_ICON,
    CONF_SCAN_INTERVAL
)
import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=15)

CONF_HOME = "home"
CONF_DAY_SWITCH = "day_switch"
CONF_FIX_TIME = "fix_time"
CONF_FACTOR = "factor"

ATTRIBUTION = "Integration powered by Boerner"
ATTR_error = "Fehler"
ATTR_destination = "Ziele"
ATTR_day_switch = "Tageswechsel-Art"
ATTR_day_switch_time = "Tageswechsel-Zeit"

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME)                                                     : cv.string,
        vol.Required(CONF_HOME)                                                     : cv.string,
        vol.Required(CONF_API_KEY)                                                  : cv.string,
        vol.Required(CONF_URL)                                                      : cv.url,
        vol.Optional(CONF_TIME_ZONE,    default='Europe/Berlin')                    : cv.time_zone,
        vol.Optional(CONF_DAY_SWITCH,   default='Sunset')                           : cv.string,
        vol.Optional(CONF_FIX_TIME,     default='22:00:00')                         : cv.time_period_str,
        vol.Optional(CONF_OFFSET,       default=0.0)                                : cv.positive_float,
        vol.Optional(CONF_FACTOR,       default=1.0)                                : cv.positive_float,
        vol.Optional(CONF_MINIMUM,      default=10.0)                               : cv.positive_float,
        vol.Optional(CONF_ICON,         default="mdi:calendar-expand-horizontal") : cv.icon,
    }
)

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    sensor = {
        "name"              : config.get(CONF_NAME),
        "home"              : config.get(CONF_HOME),
        "api_key"           : config.get(CONF_API_KEY),
        "url"               : config.get(CONF_URL),
        "time_zone"         : config.get(CONF_TIME_ZONE),
        "day_switch"        : config.get(CONF_DAY_SWITCH),
        "fix_time"          : config.get(CONF_FIX_TIME),
        "offset"            : config.get(CONF_OFFSET),
        "factor"            : config.get(CONF_FACTOR),
        "minimum"           : config.get(CONF_MINIMUM),
        "icon"              : config.get(CONF_ICON),
    }
    """Set up the sensor platform."""
    add_entities([CalendarDistance(sensor)])


class CalendarDistance(SensorEntity):
    """Representation of the Calendar-Distance-Sensor."""
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_device_class = None
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_extra_state_attributes = {ATTR_ATTRIBUTION: ATTRIBUTION}

    def __init__(self, sensor):
        """Initialize the sensor."""
        self._attr_name = sensor["name"]
        self.home = sensor["home"]
        self.api_key = sensor["api_key"]
        self.url = sensor["url"]
        self.time_zone = sensor["time_zone"]
        self.day_switch = sensor["day_switch"]
        self.fix_time = sensor["fix_time"]
        self.offset = sensor["offset"]
        self.factor = sensor["factor"]
        self.minimum = sensor["minimum"]
        self._attr_icon = sensor["icon"]
        self._attr_unique_id = "calendar_distance_" + self._attr_name + self.api_key + self.url
        self.update()

    def update(self) -> None:
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        distance, error, destinations, day_switch, day_switch_time = self.calc_distance()
        self._attr_native_value = distance
        self._attr_available = True
        self._attr_extra_state_attributes[ATTR_ATTRIBUTION] = ATTRIBUTION
        
        if error != None:
            self._attr_extra_state_attributes[ATTR_error] = error
        elif self._attr_extra_state_attributes.get(ATTR_error) != None:
            self._attr_extra_state_attributes.pop(ATTR_error)

        if destinations != None:
            self._attr_extra_state_attributes[ATTR_destination] = destinations
        elif self._attr_extra_state_attributes.get(ATTR_destination) != None:
            self._attr_extra_state_attributes.pop(ATTR_destination)
        
        if day_switch != None:
            self._attr_extra_state_attributes[ATTR_day_switch] = day_switch
        elif self._attr_extra_state_attributes.get(ATTR_day_switch) != None:
            self._attr_extra_state_attributes.pop(ATTR_day_switch)

        if day_switch_time != None:
            self._attr_extra_state_attributes[ATTR_day_switch_time] = day_switch_time
        elif self._attr_extra_state_attributes.get(ATTR_day_switch_time) != None:
            self._attr_extra_state_attributes.pop(ATTR_day_switch_time)

    def calc_distance(self):
        DESTINATIONS=[]
        error=''
        warning=[]
        destinations_distance = {}
        distance = None
        payload={}
        headers = {}
        daySwitchTime = None

        # Load Current Timestamp
        currDateTime = datetime.datetime.now(pytz.timezone(self.time_zone))

        # Load Departure-Coordinates
        if error == '':
            try:
                location_DEPARTURE_text = urllib.parse.quote(self.home)
                url_DEPARTURE = f'https://api.geoapify.com/v1/geocode/search?text={location_DEPARTURE_text}&limit=1&format=json&apiKey={self.api_key}'
                response_DEPARTURE = requests.request('GET', url_DEPARTURE, headers=headers, data=payload)
                response_DEPARTURE_json = json.loads(response_DEPARTURE.text)
                location_DEPARTURE = response_DEPARTURE_json['results'][0]['lat'], response_DEPARTURE_json['results'][0]['lon']
                #print(location_from)
            except Exception as e:
                error = f'GET FROM-LOCATION({self.home}): {str(e.__doc__)}'

        # Load Sunset
        if error == '' and self.day_switch == 'Sunset':
            try:
                url_SUNSET = f'https://api.sunrise-sunset.org/json?lat={str(location_DEPARTURE[0])}&lng={str(location_DEPARTURE[1])}&date={currDateTime.date().strftime("%Y-%m-%d")}&formatted=0'
                response_SUNSET = requests.request("GET", url_SUNSET, headers=headers, data=payload, verify=True)
                response_SUNSET_json = json.loads(response_SUNSET.text)
                daySwitchTime = datetime.datetime.strptime(response_SUNSET_json['results']['sunset'], '%Y-%m-%dT%H:%M:%S%z').astimezone(pytz.timezone(self.time_zone))
            except Exception as e:
                error = f'GET DAY_SWITCH(Sunset): {str(e.__doc__)}'
        # Load FixTime
        elif error == '' and self.day_switch == 'FixTime':
            try:
                daySwitchTime = datetime.datetime.combine(date=currDateTime.date(), time=datetime.time(), tzinfo=currDateTime.tzinfo) + self.fix_time
            except Exception as e:
                error = f'GET DAY_SWITCH(FixTime): {str(e.__doc__)}, {self.fix_time}'
        else:
            error = 'DAY_SWITCH: Parameter is not valid!'

        # Load Calendar
        if error == '':
            try:
                today = currDateTime.date()
                tomorrow = currDateTime.date() + datetime.timedelta(days=1)

                ical = requests.get(self.url)
                gcal = Calendar.from_ical(ical.text)
                for component in gcal.walk():
                    append = False
                    if component.name == 'VEVENT':
                        summary = component.get('summary')
                        dtstart = component.get('dtstart')
                        location = component.get('LOCATION')
                        if isinstance(dtstart.dt, datetime.datetime):
                            eventDate = dtstart.dt.date()
                            if currDateTime > daySwitchTime:
                                if (eventDate == today or eventDate == tomorrow) and (dtstart.dt > currDateTime):
                                    append = True
                            else:
                                if (eventDate == today) and (dtstart.dt > currDateTime):
                                    append = True
                        elif isinstance(dtstart.dt, datetime.date):
                            eventDate = dtstart.dt
                            if currDateTime > daySwitchTime:
                                if (eventDate == tomorrow):
                                    append = True
                            else:
                                if (eventDate == today):
                                    append = True
                        else:
                            raise Exception(f'Can\'t find valid DateTime of Event: {summary}')
                        
                        if append:
                            if location == '':
                                if summary != '':
                                    summary_text = summary
                                else:
                                    summary_text = '<LEER>'
                                warning.append(f'Für den Termin "{summary_text}" konnte kein Ort gefunden werden!')
                            else:
                                DESTINATIONS.append(location)
            except Exception as e:
                error = f'GET ICAL: {str(e.__doc__)}'
                
        for DESTINATION in DESTINATIONS:
            # Load Destination-Coordinates
            if error == '':
                try:
                    location_DESTINATION_text = urllib.parse.quote(DESTINATION)
                    url_DESTINATION = f'https://api.geoapify.com/v1/geocode/search?text={location_DESTINATION_text}&limit=1&format=json&apiKey={self.api_key}'
                    response_DESTINATION = requests.request('GET', url_DESTINATION, headers=headers, data=payload)
                    response_DESTINATION_json = json.loads(response_DESTINATION.text)
                    location_DESTINATION = response_DESTINATION_json['results'][0]['lat'], response_DESTINATION_json['results'][0]['lon']
                    #print(location_to)
                except Exception as e:
                    error = f'GET TO-LOCATION({DESTINATION}): {str(e.__doc__)}'

            # Load Route-Distance
            if error == '':
                try:
                    url_ROUTE = f'https://api.geoapify.com/v1/routing?waypoints={str(location_DEPARTURE[0])},{str(location_DEPARTURE[1])}|{str(location_DESTINATION[0])},{str(location_DESTINATION[1])}&mode=drive&lang=de&apiKey={self.api_key}'
                    response_ROUTE = requests.request('GET', url_ROUTE, headers=headers, data=payload)
                    response_ROUTE_json = json.loads(response_ROUTE.text)

                    if distance == None:
                        distance = 0.0
                    # Load Meters from Route convert to Kilometers and double for outward and return
                    distance_current_route = (int(response_ROUTE_json['features'][0]['properties']['distance']) / 1000 * 2)
                    destinations_distance[DESTINATION] = distance_current_route
                    distance = distance + distance_current_route
                except Exception as e:
                    error = f'GET ROUTE({self.home})-({DESTINATION}): {str(e.__doc__)}'

        if error == '':
            if distance == None:
                distance = 0.0
            Part_FACTOR = distance * (self.factor - 1)
            if self.factor != 1.0:
                destinations_distance['Faktor Anteil'] = Part_FACTOR
            if self.offset != 0.0:
                destinations_distance['Offset'] = self.offset
            distance = distance + Part_FACTOR + self.offset
            distance = float.__round__(distance, 1)
            if distance < self.minimum:
                destinations_distance['Minimum'] = self.minimum
                distance = self.minimum

        if error != '':
            return 'unknown', error, None, None, None
        elif distance != None:
            if warning != []:
                return distance, warning, destinations_distance, self.day_switch, daySwitchTime.strftime("%H:%M:%S")
            else:
                return distance, None, destinations_distance, self.day_switch, daySwitchTime.strftime("%H:%M:%S")
        else:
            return 'unknown', 'unknown', None, None, None
