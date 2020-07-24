from enum import Enum

class Plan(Enum):
    TRIAL = "trial"
    BASIC = "basic"
    PREMIUM = "premium"
    
class Granularity(Enum):
    DAILY = "daily"
    HOURLY = "hourly"
                
COL_TYPES = {
    "trial": {""
        "latitude [degree]": "float",
        "longitude [degree]": "float",
        "forecast day": "date",
        "forecasted day": "date",
        "weather state": "string",
        "prec [l/m^2]": "float",
        "prec_probability [%]": "float",
        "sun hours [h]": "float",
        "wind direction": "string",
        "min wind [km/h]": "float",
        "max wind [km/h]": "float",
        "min temperature [C]": "float",
        "max temperature [C]": "float",
        "min windchill [C]": "float",
        "max windchill [C]": "float",
        "dawn": "date",
        "sunrise": "date",
        "suntransit": "date",
        "sunset": "date",
        "dusk": "date",
        "moonrise": "date",
        "moontransit": "date",
        "moonset": "date",
        "moonphase": "int",
        "moonzodiac": "int",
        "air pressure": "string",
        "cloud cover": "string",
        "relativeHumidity": "string",
        "daily call": "int"
    },
    "basic": {""
        "latitude [degree]": "float",
        "longitude [degree]": "float",
        "forecast day": "date",
        "forecasted day": "date",
        "weather state": "string",
        "prec [l/m^2]": "float",
        "prec_probability [%]": "float",
        "sun hours [h]": "float",
        "wind direction": "string",
        "min wind [km/h]": "float",
        "max wind [km/h]": "float",
        "min temperature [C]": "float",
        "max temperature [C]": "float",
        "min windchill [C]": "float",
        "max windchill [C]": "float",
        "dawn": "date",
        "sunrise": "date",
        "suntransit": "date",
        "sunset": "date",
        "dusk": "date",
        "moonrise": "date",
        "moontransit": "date",
        "moonset": "date",
        "moonphase": "int",
        "moonzodiac": "int",
        "air pressure": "string",
        "cloud cover": "string",
        "relativeHumidity": "string"
    },
    "premium": {""
        "latitude [degree]": "float",
        "longitude [degree]": "float",
        "forecast day": "date",
        "forecasted day": "date",
        "weather state": "string",
        "prec [l/m^2]": "float",
        "prec_probability [%]": "float",
        "wind direction": "string",
        "avg wind [km/h]": "float",
        "avg temperature [C]": "float",
        "avg windchill [C]": "float",
        "air pressure": "float",
        "cloud cover": "float",
        "relativeHumidity": "float"
    }
}

UNITS_LABEL = {
    "standard": {
        "speed": "meter/s",
        "temp": "K",
        "pressure": "hPas"
    },
    "metric": {
        "speed": "meter/s",
        "temp": "C",
        "pressure": "hPas"
    },
    "imperial": {
        "speed": "mile/h",
        "temp": "F",
        "pressure": "hPas"
    }
}

LANG_LABEL = {
    "en": "English",
    "de": "Deutsch"
}

CACHE_RELATIVE_DIR = ".cache/dss/plugins/meteonomiqs"