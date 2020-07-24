from six.moves import xrange
from dataiku.connector import Connector

import os
import pwd
import requests
import json
import base64
import datetime
from time import sleep
import logging
from constants import Plan, Granularity
import constants

logger = logging.getLogger(__name__)

class MyConnector(Connector):

    def __init__(self, config, plugin_config):
        Connector.__init__(self, config, plugin_config)

        # perform some more initialization
        parameters = plugin_config.get("basic_parameters")
        
        try:
            self.default_token = str(parameters['default_token'])
            self.other_token = str(parameters['other_token'])
            self.latitude = str(round(parameters['latitude'],5))
            self.longitude = str(round(parameters['longitude'],5))
            self.use_cache = bool(parameters['use_cache'])
            self.cache_folder = str(parameters['cache_folder'])
            self.plan = str(parameters['plan'])
            self.api_limit = int(parameters['api_limit'])
            self.cache_size = int(parameters['cache_size'])*1000
            self.cache_policy = str(parameters['cache_policy'])
            self.units_temperature = str(parameters['units_temperature'])
            self.units_wind = str(parameters['units_wind'])
            self.units_pressure = str(parameters['units_pressure'])
            self.language = str(parameters['language'])
            self.available_columns = constants.COL_TYPES
        except:
            self.default_token = ""
            self.other_token = ""
            self.latitude = "0"
            self.longitude = "0"
            self.use_cache = False
            self.cache_folder = ""
            self.plan = "trial"
            self.cache_size = 1000*1000
            self.cache_policy = "least-recently-used"
            self.units_temperature = "C"
            self.units_wind = "ms"
            self.units_pressure = "hPa"
            self.language = "en"
            self.available_columns = constants.COL_TYPES
            
        self.cache_data = {}
        self.cache_data1 = {}
        self.date = ''
        self.api_calls = 0
        if (len(self.other_token) > 10) & (self.plan != 'trial'):
            self.token = self.other_token
        else:
            self.token = self.default_token
        if (self.other_token == self.default_token):
            self.token = ""
        
        if self.plan == 'trial':
            self.api_limit = 10
        else:
            self.api_limit = -1
                    
        self.cache_folder = os.path.join(pwd.getpwuid(os.getuid()).pw_dir, constants.CACHE_RELATIVE_DIR)

        # Cache file
        if (self.cache_folder != "") & (self.api_limit > -1):
            filename = "cache-meteonomiqs-forecast.dat"
            logger.info("meteonomiqs plugin - Create cache file %s" % filename)
            self.cache_data1 = os.path.join(self.cache_folder, filename)

            # create directory if required
            if not os.path.isdir(self.cache_folder):
                os.makedirs(self.cache_folder)

            # create file if required
            if not os.path.exists(self.cache_data1):
                with open(self.cache_data1, 'w') as f:
                    f.write(str(datetime.datetime.today().strftime("%Y%m%d")))        
                    f.write('\n')
                    f.write(str(0))
                    f.close()
                self.api_calls = 0
                
            # read cache
            with open(self.cache_data1, 'r') as f:
                self.date = f.readline().strip()
                self.api_calls = int(f.readline())
                f.close()

            # calc calls
            if self.date != str(datetime.datetime.today().strftime("%Y%m%d")):
                with open(self.cache_data1, 'w') as f:
                    self.date = str(datetime.datetime.today().strftime("%Y%m%d"))
                    f.write(self.date)
                    f.write('\n')
                    f.write(str(0))
                    f.close()
                self.api_calls = 0

    def __load_cache(self):
        # Reading json cache
        if self.cache_file:
            logger.info("meteonomiqs plugin - Loading cache (%s)" % self.cache_file)
            with open(self.cache_file, 'r') as f:
                self.cache_data = json.load(f)
                f.close()

    def __save_cache(self):
        #Writing json cache
        if self.cache_file:
            logger.info("meteonomiqs plugin - Saving cache (%s)" % self.cache_file)
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache_data, f)
                f.close()
                
    def __get_weather(self, day=None):
        if not day:
            return None
        
        name = str(self.latitude) + '-' + str(self.longitude)
        day_key = "%s-%s-%s" % (self.plan, day.strftime("%Y%m%d"), base64.urlsafe_b64encode(name.encode())) 
        
        if self.use_cache:
            filename = "cache-meteonomiqs-forecast-%s.json" % day_key
            self.cache_file = os.path.join(self.cache_folder, filename)
            try:
                if os.path.exists(self.cache_file):
                    self.__load_cache()
                    logger.info("meteonomiqs plugin - Already in cache for %s" % day_key)
                    return self.cache_data.get(day_key)
            except:
                logger.info("meteonomiqs plugin - Not in cache for %s" % day_key)

        if day:
            # Not in cache -> API request
            logger.info("meteonomiqs plugin - Request for %s" % day_key)

            # checking limits
            if (self.api_calls >= self.api_limit) & (self.api_limit > -1):
                logger.info("meteonomiqs plugin - Limit reached, no call for %s (cur=%d lim=%d)" % (day_key, self.api_calls, self.api_limit))
                return {"result" : "Limit reached - no API call." }

            if self.plan == 'trial':
                url = 'https://wetter-com-forecast2.p.rapidapi.com/forecast/%s/%s/summary/' % (self.latitude, self.longitude)
            elif self.plan == 'basic':
                url = 'https://wetter-com-forecast2.p.rapidapi.com/forecast/%s/%s/summary/' % (self.latitude, self.longitude)
            elif self.plan == 'premium':
                url = 'https://wetter-com-forecast2.p.rapidapi.com/forecast/%s/%s/hourly/' % (self.latitude, self.longitude)
            
            headers = {
                'x-rapidapi-host': "wetter-com-forecast2.p.rapidapi.com",
                'x-rapidapi-key': "%s" % (self.token)
                }

            response = requests.request("GET", url, headers=headers)
            data = response.text

            # results
            try:
                result = json.loads(data)
            except:
                return {"message" : "Something went wrong. Most likely no plan is selected." }
            
            logger.info("meteonomiqs plugin - Forecast-API-Calls: %s" % self.api_calls)
            
            if self.cache_file:
                logger.info("meteonomiqs plugin - Adding to cache: %s" % day_key)
                self.cache_data[day_key] = result

            if self.api_limit > -1:
                # create file if required
                if not os.path.exists(self.cache_data1):
                    logger.info("meteonomiqs plugin - Create file: %s" % self.cache_data1)
                    with open(self.cache_data1, 'w') as f:
                        f.write(str(datetime.datetime.today().strftime("%Y%m%d")))        
                        f.write('\n')
                        f.write(str(1))
                        f.close()
                    self.api_calls = 0

                # read cache
                logger.info("meteonomiqs plugin - Read file: %s" % self.cache_data1)
                with open(self.cache_data1, 'r') as f:
                    self.date = f.readline().strip()
                    self.api_calls = int(f.readline())
                    f.close()

                # calc calls
                if self.date != str(datetime.datetime.today().strftime("%Y%m%d")):
                    logger.info("meteonomiqs plugin - Create file due to date: %s" % self.cache_data1)
                    with open(self.cache_data1, 'w') as f:
                        self.date = str(datetime.datetime.today().strftime("%Y%m%d"))
                        f.write(self.date)
                        f.write('\n')
                        f.write(str(1))
                        f.close()
                    self.api_calls = 1
                else:
                    logger.info("meteonomiqs plugin - Update file: %s" % self.cache_data1)
                    self.api_calls = self.api_calls + 1
                    with open(self.cache_data1, 'w') as f:
                        self.date = str(datetime.datetime.today().strftime("%Y%m%d"))
                        f.write(self.date)
                        f.write('\n')
                        f.write(str(self.api_calls))
                        f.close()
            else:
                self.api_calls = self.api_calls + 1
                
            sleep(0.9)
            return result

    def _retrieve_columns_type(self, plan):
        if plan == "trial":
            columns = dict(
                self.available_columns[Plan.TRIAL.value],
                **self.available_columns[Plan.TRIAL.value]
            )
            return dict(self.available_columns[Plan.TRIAL.value], **dict(
                columns
            ))
        if plan == "basic":
            columns = dict(
                self.available_columns[Plan.BASIC.value],
                **self.available_columns[Plan.BASIC.value]
            )
            return dict(self.available_columns[Plan.BASIC.value], **dict(
                columns
            ))
        if plan == "premium":
            columns = dict(
                self.available_columns[Plan.PREMIUM.value],
                **self.available_columns[Plan.PREMIUM.value]
            )
            return dict(self.available_columns[Plan.PREMIUM.value], **dict(
                columns
            ))
        return None

    def retrieve_schema(self, plan):
        return {
            "columns": [{"name": k, "type": v} for k, v in self._retrieve_columns_type(plan).items()]
        }
    
    def get_read_schema(self):
        return self.retrieve_schema(self.plan)
        
    def generate_rows(self, dataset_schema=None, dataset_partitioning=None,
                            partition_id=None, records_limit = -1):

        today_date = datetime.datetime.today()
        from_date = today_date
        to_date = today_date

        if to_date < from_date:
            raise ValueError("The end date must occur after the start date")

        if to_date >= datetime.datetime.today() + datetime.timedelta(days=3):
            raise ValueError("End date is limited to three days")
        
        if from_date < today_date:
            raise ValueError("No historical days in free version")
        
        list_datetimes = [from_date + datetime.timedelta(days=x) for x in range((to_date-from_date).days + 1)]
        logger.info("meteonomiqs plugin - List of dates: %s" % ", ".join([d.strftime("%d/%m/%Y") for d in list_datetimes]))

        # Requests
        for day in list_datetimes:
                result = self.__get_weather(day)
                
                if (self.api_calls >= self.api_limit) & (self.api_limit > -1) & ('items' not in result):
                    yield {
                        'result' : 'Daily API call limit reached - if you want to upgrade your plan to get more data please contact info@meteonomiqs.com',
                        'Free API call limit' : self.api_limit,
                        'Todays calls' : self.api_calls
                    }
                elif ('message' in result) & (self.plan != 'trial') & (len(self.token) < 2):
                    yield {
                        'result' : 'The token is not valid',
                        'Information' : 'Please provide a valid token. If you do not have a valid token, please contact info@meteonomiqs.com.'
                    }
                elif 'message' in result:
                    yield {
                        'result' : 'An error occured',
                        'Information' : 'Most likely the token is not valid. If you are using a valid token and the error occurs, please contact info@meteonomiqs.com.'
                    }
                else:
                    if self.plan == 'trial':
                            for i in range(0,3):
                                yield {
                                    'latitude [degree]': self.latitude,
                                    'longitude [degree]': self.longitude,
                                    'forecast day': day.strftime("%Y-%m-%d"),
                                    'forecasted day': result['items'][i]['date'] if 'items' in result and 'date' in result['items'][i] and result['items'][i]['date'] is not None else '',

#                                    'fresh snow [m]': result['items'][i]['freshSnow'] if 'items' in result and 'freshSnow' in result['items'][i] and result['items'][i]['freshSnow'] is not None else '',
#                                    'snow height [m]': result['items'][i]['snowHeight'] if 'items' in result and 'snowHeight' in result['items'][i] and result['items'][i]['snowHeight'] is not None else '',
#                                    'snowline [m]': result['items'][i]['snowLine']['avg'] if 'items' in result and 'snowLine' in result['items'][i] and 'avg' in result['items'][i]['snowLine'] and result['items'][i]['snowLine']['max'] is not None else '',

                                    'weather state': result['items'][i]['weather']['text'] if 'items' in result and 'weather' in result['items'][i] and 'text' in result['items'][i]['weather'] and result['items'][i]['weather']['text'] is not None else '',

                                    'prec [l/m^2]': result['items'][i]['prec']['sum'] if 'items' in result and 'prec' in result['items'][i] and 'sum' in result['items'][i]['prec'] and result['items'][i]['prec']['sum'] is not None else '',
                                    'prec_probability [%]': result['items'][i]['prec']['probability'] if 'items' in result and 'prec' in result['items'][i] and 'probability' in result['items'][i]['prec'] and result['items'][i]['prec']['probability'] is not None else '',

#                                    'rain hours [h]': result['items'][i]['rainHours'] if 'items' in result and 'rainHours' in result['items'][i] and result['items'][i]['rainHours'] is not None else '',
                                    'sun hours [h]': result['items'][i]['sunHours'] if 'items' in result and 'sunHours' in result['items'][i] and result['items'][i]['sunHours'] is not None else '',

                                    'wind direction': result['items'][i]['wind']['text'] if 'items' in result and 'wind' in result['items'][i] and 'text' in result['items'][i]['wind'] and result['items'][i]['wind']['text'] is not None else '',
                                    'min wind [km/h]': result['items'][i]['wind']['min'] if 'items' in result and 'wind' in result['items'][i] and 'min' in result['items'][i]['wind'] and result['items'][i]['wind']['min'] is not None else '',
                                    'max wind [km/h]': result['items'][i]['wind']['max'] if 'items' in result and 'wind' in result['items'][i] and 'max' in result['items'][i]['wind'] and result['items'][i]['wind']['max'] is not None else '',

                                    'min temperature [C]': result['items'][i]['temperature']['min'] if 'items' in result and 'temperature' in result['items'][i] and 'min' in result['items'][i]['temperature'] and result['items'][i]['temperature']['min'] is not None else '',
                                    'max temperature [C]': result['items'][i]['temperature']['max'] if 'items' in result and 'temperature' in result['items'][i] and 'max' in result['items'][i]['temperature'] and result['items'][i]['temperature']['max'] is not None else '',

                                    'min windchill [C]': result['items'][i]['windchill']['min'] if 'items' in result and 'windchill' in result['items'][i] and 'min' in result['items'][i]['windchill'] and result['items'][i]['windchill']['min'] is not None else '',
                                    'max windchill [C]': result['items'][i]['windchill']['max'] if 'items' in result and 'windchill' in result['items'][i] and 'max' in result['items'][i]['windchill'] and result['items'][i]['windchill']['max'] is not None else '',

                                    'dawn': result['items'][i]['astronomy']['dawn'] if 'items' in result and 'astronomy' in result['items'][i] and 'dawn' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['dawn'] is not None else '',
                                    'sunrise': result['items'][i]['astronomy']['sunrise'] if 'items' in result and 'astronomy' in result['items'][i] and 'sunrise' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['sunrise'] is not None else '',
                                    'suntransit': result['items'][i]['astronomy']['suntransit'] if 'items' in result and 'astronomy' in result['items'][i] and 'suntransit' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['suntransit'] is not None else '',
                                    'sunset': result['items'][i]['astronomy']['sunset'] if 'items' in result and 'astronomy' in result['items'][i] and 'sunset' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['sunset'] is not None else '',
                                    'dusk': result['items'][i]['astronomy']['dusk'] if 'items' in result and 'astronomy' in result['items'][i] and 'dusk' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['dusk'] is not None else '',
                                    'moonrise': result['items'][i]['astronomy']['moonrise'] if 'items' in result and 'astronomy' in result['items'][i] and 'moonrise' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['moonrise'] is not None else '',
                                    'moontransit': result['items'][i]['astronomy']['moontransit'] if 'items' in result and 'astronomy' in result['items'][i] and 'moontransit' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['moontransit'] is not None else '',
                                    'moonset': result['items'][i]['astronomy']['moonset'] if 'items' in result and 'astronomy' in result['items'][i] and 'moonset' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['moonset'] is not None else '',
                                    'moonphase': result['items'][i]['astronomy']['moonphase'] if 'items' in result and 'astronomy' in result['items'][i] and 'moonphase' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['moonphase'] is not None else '',
                                    'moonzodiac': result['items'][i]['astronomy']['moonzodiac'] if 'items' in result and 'astronomy' in result['items'][i] and 'moonzodiac' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['moonzodiac'] is not None else '',

#                                    'dew point' : 'premium version',
                                    'air pressure' : 'premium version',
                                    'cloud cover' : 'premium version',
#                                    'wind gusts' : 'premium version',
#                                    'evaporation pressure' : 'premium version',
#                                    'min temperature anomaly' : 'premium version',
#                                    'avg temperature anomaly' : 'premium version',
#                                    'max temperature anomaly' : 'premium version',
                                    'relativeHumidity' : 'premium version',

                                    'daily call': self.api_calls
                                }
                    elif self.plan == 'basic':
                        for i in range(0,5):
                            yield {
                                'latitude [degree]': self.latitude,
                                'longitude [degree]': self.longitude,
                                'forecast day': day.strftime("%Y-%m-%d"),
                                'forecasted day': result['items'][i]['date'] if 'items' in result and 'date' in result['items'][i] and result['items'][i]['date'] is not None else '',

#                                'fresh snow [m]': result['items'][i]['freshSnow'] if 'items' in result and 'freshSnow' in result['items'][i] and result['items'][i]['freshSnow'] is not None else '',
#                                'snow height [m]': result['items'][i]['snowHeight'] if 'items' in result and 'snowHeight' in result['items'][i] and result['items'][i]['snowHeight'] is not None else '',
#                                'snowline [m]': result['items'][i]['snowLine']['avg'] if 'items' in result and 'snowLine' in result['items'][i] and 'avg' in result['items'][i]['snowLine'] and result['items'][i]['snowLine']['max'] is not None else '',

                                'weather state': result['items'][i]['weather']['text'] if 'items' in result and 'weather' in result['items'][i] and 'text' in result['items'][i]['weather'] and result['items'][i]['weather']['text'] is not None else '',

                                'prec [l/m^2]': result['items'][i]['prec']['sum'] if 'items' in result and 'prec' in result['items'][i] and 'sum' in result['items'][i]['prec'] and result['items'][i]['prec']['sum'] is not None else '',
                                'prec_probability [%]': result['items'][i]['prec']['probability'] if 'items' in result and 'prec' in result['items'][i] and 'probability' in result['items'][i]['prec'] and result['items'][i]['prec']['probability'] is not None else '',

#                                'rain hours [h]': result['items'][i]['rainHours'] if 'items' in result and 'rainHours' in result['items'][i] and result['items'][i]['rainHours'] is not None else '',
                                'sun hours [h]': result['items'][i]['sunHours'] if 'items' in result and 'sunHours' in result['items'][i] and result['items'][i]['sunHours'] is not None else '',

                                'wind direction': result['items'][i]['wind']['text'] if 'items' in result and 'wind' in result['items'][i] and 'text' in result['items'][i]['wind'] and result['items'][i]['wind']['text'] is not None else '',
                                'min wind [km/h]': result['items'][i]['wind']['min'] if 'items' in result and 'wind' in result['items'][i] and 'min' in result['items'][i]['wind'] and result['items'][i]['wind']['min'] is not None else '',
                                'max wind [km/h]': result['items'][i]['wind']['max'] if 'items' in result and 'wind' in result['items'][i] and 'max' in result['items'][i]['wind'] and result['items'][i]['wind']['max'] is not None else '',

                                'min temperature [C]': result['items'][i]['temperature']['min'] if 'items' in result and 'temperature' in result['items'][i] and 'min' in result['items'][i]['temperature'] and result['items'][i]['temperature']['min'] is not None else '',
                                'max temperature [C]': result['items'][i]['temperature']['max'] if 'items' in result and 'temperature' in result['items'][i] and 'max' in result['items'][i]['temperature'] and result['items'][i]['temperature']['max'] is not None else '',

                                'min windchill [C]': result['items'][i]['windchill']['min'] if 'items' in result and 'windchill' in result['items'][i] and 'min' in result['items'][i]['windchill'] and result['items'][i]['windchill']['min'] is not None else '',
                                'max windchill [C]': result['items'][i]['windchill']['max'] if 'items' in result and 'windchill' in result['items'][i] and 'max' in result['items'][i]['windchill'] and result['items'][i]['windchill']['max'] is not None else '',

                                'dawn': result['items'][i]['astronomy']['dawn'] if 'items' in result and 'astronomy' in result['items'][i] and 'dawn' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['dawn'] is not None else '',
                                'sunrise': result['items'][i]['astronomy']['sunrise'] if 'items' in result and 'astronomy' in result['items'][i] and 'sunrise' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['sunrise'] is not None else '',
                                'suntransit': result['items'][i]['astronomy']['suntransit'] if 'items' in result and 'astronomy' in result['items'][i] and 'suntransit' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['suntransit'] is not None else '',
                                'sunset': result['items'][i]['astronomy']['sunset'] if 'items' in result and 'astronomy' in result['items'][i] and 'sunset' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['sunset'] is not None else '',
                                'dusk': result['items'][i]['astronomy']['dusk'] if 'items' in result and 'astronomy' in result['items'][i] and 'dusk' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['dusk'] is not None else '',
                                'moonrise': result['items'][i]['astronomy']['moonrise'] if 'items' in result and 'astronomy' in result['items'][i] and 'moonrise' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['moonrise'] is not None else '',
                                'moontransit': result['items'][i]['astronomy']['moontransit'] if 'items' in result and 'astronomy' in result['items'][i] and 'moontransit' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['moontransit'] is not None else '',
                                'moonset': result['items'][i]['astronomy']['moonset'] if 'items' in result and 'astronomy' in result['items'][i] and 'moonset' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['moonset'] is not None else '',
                                'moonphase': result['items'][i]['astronomy']['moonphase'] if 'items' in result and 'astronomy' in result['items'][i] and 'moonphase' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['moonphase'] is not None else '',
                                'moonzodiac': result['items'][i]['astronomy']['moonzodiac'] if 'items' in result and 'astronomy' in result['items'][i] and 'moonzodiac' in result['items'][i]['astronomy'] and result['items'][i]['astronomy']['moonzodiac'] is not None else '',

#                                'dew point' : 'premium version',
                                'air pressure' : 'premium version',
                                'cloud cover' : 'premium version',
#                                'wind gusts' : 'premium version',
#                                'evaporation pressure' : 'premium version',
#                                'min temperature anomaly' : 'premium version',
#                                'avg temperature anomaly' : 'premium version',
#                                'max temperature anomaly' : 'premium version',
                                'relativeHumidity' : 'premium version'

#                                'daily call': self.api_calls
                            }
                    elif self.plan == 'premium':
                        logger.info("meteonomiqs plugin - Premium length: %s" % len(result['items']))
                        for i in range(0, len(result['items'])):
                            yield {
                                'latitude [degree]': self.latitude,
                                'longitude [degree]': self.longitude,
                                'forecast day': day.strftime("%Y-%m-%d"),
                                'forecasted day': result['items'][i]['date'] if 'items' in result and 'date' in result['items'][i] and result['items'][i]['date'] is not None else '',

#                                'fresh snow [m]': result['items'][i]['freshSnow'] if 'items' in result and 'freshSnow' in result['items'][i] and result['items'][i]['freshSnow'] is not None else '',
#                                'snow height [m]': result['items'][i]['snowHeight'] if 'items' in result and 'snowHeight' in result['items'][i] and result['items'][i]['snowHeight'] is not None else '',
#                                'snowline [m]': result['items'][i]['snowLine']['avg'] if 'items' in result and 'snowLine' in result['items'][i] and 'avg' in result['items'][i]['snowLine'] and result['items'][i]['snowLine']['max'] is not None else '',

                                'weather state': result['items'][i]['weather']['text'] if 'items' in result and 'weather' in result['items'][i] and 'text' in result['items'][i]['weather'] and result['items'][i]['weather']['text'] is not None else '',

                                'prec [l/m^2]': result['items'][i]['prec']['sum'] if 'items' in result and 'prec' in result['items'][i] and 'sum' in result['items'][i]['prec'] and result['items'][i]['prec']['sum'] is not None else '',
                                'prec_probability [%]': result['items'][i]['prec']['probability'] if 'items' in result and 'prec' in result['items'][i] and 'probability' in result['items'][i]['prec'] and result['items'][i]['prec']['probability'] is not None else '',

#                                'rain hours [h]': result['items'][i]['rainHours'] if 'items' in result and 'rainHours' in result['items'][i] and result['items'][i]['rainHours'] is not None else '',
#                                'sun hours [h]': result['items'][i]['sunHours'] if 'items' in result and 'sunHours' in result['items'][i] and result['items'][i]['sunHours'] is not None else '',

                                'wind direction': result['items'][i]['wind']['text'] if 'items' in result and 'wind' in result['items'][i] and 'text' in result['items'][i]['wind'] and result['items'][i]['wind']['text'] is not None else '',
                                'avg wind [km/h]': result['items'][i]['wind']['avg'] if 'items' in result and 'wind' in result['items'][i] and 'avg' in result['items'][i]['wind'] and result['items'][i]['wind']['avg'] is not None else '',

                                'avg temperature [C]': result['items'][i]['temperature']['avg'] if 'items' in result and 'temperature' in result['items'][i] and 'avg' in result['items'][i]['temperature'] and result['items'][i]['temperature']['avg'] is not None else '',
                                
                                'avg windchill [C]': result['items'][i]['windchill']['avg'] if 'items' in result and 'windchill' in result['items'][i] and 'avg' in result['items'][i]['windchill'] and result['items'][i]['windchill']['avg'] is not None else '',

#                                'dew point' : 'premium version',
                                'air pressure' : result['items'][i]['pressure'] if 'items' in result and 'pressure' in result['items'][i] and result['items'][i]['pressure'] is not None else '',
                                'cloud cover' : result['items'][i]['clouds']['middle'] if 'items' in result and 'clouds' in result['items'][i] and 'middle' in result['items'][i]['clouds'] and result['items'][i]['clouds']['middle'] is not None else '',
#                                'evaporation pressure' : 'premium version',
#                                'min temperature anomaly' : 'premium version',
#                                'avg temperature anomaly' : 'premium version',
#                                'max temperature anomaly' : 'premium version',
                                'relativeHumidity' : result['items'][i]['relativeHumidity'] if 'items' in result and 'relativeHumidity' in result['items'][i] and result['items'][i]['relativeHumidity'] is not None else ''

#                                'daily call': self.api_calls
                            }

        if self.use_cache & ('items' in result):
            self.__save_cache()