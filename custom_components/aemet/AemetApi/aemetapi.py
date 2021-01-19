import requests
from datetime import timedelta
import datetime
from logging import getLogger
import logging
from const import *
import time


import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_LOGGER = getLogger('simple_example')
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.CRITICAL)
_LOGGER.setLevel(logging.DEBUG)
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
_LOGGER.addHandler(ch)
HTTP_OK = 200
ATTR_ELEVATION = 'elevation'
ATTR_LAST_UPDATE = 'last_update'
ATTR_STATION_NAME = 'station_name'
ATTR_WEATHER_PRECIPITATION = 'precipitation'
ATTR_WEATHER_SNOW = 'snow'
ATTR_WEATHER_WIND_SPEED = 'wind_speed'
ATTR_WEATHER_WIND_MAX_SPEED = 'wind_max_speed'
ATTR_WEATHER_WIND_BEARING = 'wind_bearing'
ATTR_LONGITUDE = 'lon'
ATTR_LATITUDE = 'lat'
ATTR_WEATHER_PRESSURE = 'pres'
ATTR_WEATHER_TEMPERATURE = 'ta'
ATTR_WEATHER_HUMIDITY = 'hr'
ATTR_WEATHER_VISIBILITY = 'vis'
MS_TO_KMH_ATTRS = '0'

#Hourly
ATTR_FORECAST_TEMP = 'temperature',
ATTR_FORECAST_COND = 'condition',
ATTR_FORECAST_PREC = 'precipitation',
ATTR_FORECAST_PREC_PROB = 'precipitation_probability',
ATTR_FORECAST_WIND_BEARING = 'wind_bearing',
ATTR_FORECAST_WIND_SPEED = 'wind_speed'

ATTR_MAPPINGS = {
	ATTR_LONGITUDE: 'lon',
	ATTR_LATITUDE: 'lat',
	ATTR_ELEVATION: 'alt',
	ATTR_STATION_NAME: 'ubi',
	ATTR_WEATHER_PRECIPITATION: 'prec',
	ATTR_WEATHER_PRESSURE: 'pres',
	ATTR_WEATHER_TEMPERATURE: 'ta',
	ATTR_WEATHER_HUMIDITY: 'hr',
	ATTR_LAST_UPDATE: 'fint',
	ATTR_WEATHER_VISIBILITY: 'vis',
	#ATTR_WEATHER_SNOW: 'nieve', NO NECESARIO
	ATTR_WEATHER_WIND_SPEED: 'vv',
	ATTR_WEATHER_WIND_MAX_SPEED: 'vmax',
	ATTR_WEATHER_WIND_BEARING: 'dv',
	
	#Hourly
	ATTR_FORECAST_TEMP: 'temperatura',
	ATTR_FORECAST_COND: 'estadoCielo',
	ATTR_FORECAST_PREC: 'precipitacion',
	ATTR_FORECAST_PREC_PROB: 'probPrecipitacion',
	ATTR_FORECAST_WIND_BEARING: 'vientoAndRachaMax'
	#ATTR_FORECAST_WIND_SPEED: 'vientoAndRachaMax'
	
}

class AemetApi:
	"""Get the lastest data and updates the states."""
	API_URL_BASE = 'https://opendata.aemet.es/opendata/api'
	API_STATION_ENDPOINT = '/observacion/convencional/datos/estacion/{}'
	API_HOURLY_FORECAST_ENDPOINT = '/prediccion/especifica/municipio/horaria/{}'
	API_DAILY_FORECAST_ENDPOINT = '/prediccion/especifica/municipio/diaria/{}'

	def __init__(self, api_key, station_id, neighborhood_id):
		"""Initialize the data object."""
		self._station_id = station_id
		self._neighborhood_id = neighborhood_id
		self._api_key = api_key
		self.data = {}

	#@Throttle(MIN_TIME_BETWEEN_UPDATES)
	def update(self):
		"""Fetch new state data for the sensor."""
		_LOGGER.debug("------- Updating AEMET sensor")
		endpoint_url = "{}{}".format(
							self.API_URL_BASE,
							self.API_STATION_ENDPOINT.format(self._station_id)
						)
		params = {'api_key': self._api_key}
		main_rsp = requests.get(endpoint_url, params=params, verify=False)
		if main_rsp.status_code != HTTP_OK:
			_LOGGER.error("Invalid response: %s", main_rsp.status_code)
			return

		main_result = main_rsp.json()
		if main_result['estado'] == HTTP_OK:
			hashed_endpoint = main_result["datos"]
			data_rsp = requests.get(hashed_endpoint, verify=False)
			if data_rsp.status_code != HTTP_OK:
				_LOGGER.error("Invalid response: %s", data_rsp.status_code)
			data_result = data_rsp.json()
			last_update = data_result[-1]
			self.set_data(last_update)
			#_LOGGER.debug(last_update)
		else:
			_LOGGER.error("Invalid response: %s", main_rsp.status_code)
			
		_LOGGER.debug("------- Updating AEMET Forecast")
		endpoint_url = "{}{}".format(
							self.API_URL_BASE,
							self.API_HOURLY_FORECAST_ENDPOINT.format(self._neighborhood_id)
						)
		params = {'api_key': self._api_key}
		main_rsp = requests.get(endpoint_url, params=params, verify=False)
		
		#_LOGGER.debug("Requested URL: "+endpoint_url)
		
		if main_rsp.status_code != HTTP_OK:
			_LOGGER.error("Invalid response from general Forecast API: %s", main_rsp.status_code)
			return

		main_result = main_rsp.json()
		
		if main_result['estado'] == HTTP_OK:
			hashed_endpoint = main_result["datos"]
			data_rsp = requests.get(hashed_endpoint, verify=False)
			if data_rsp.status_code != HTTP_OK:
				_LOGGER.error("Invalid response from Forecast Data call: %s", data_rsp.status_code)
			data_result = data_rsp.json()
			last_update = data_result[-1]
			self.set_forecast_data(last_update)
			#_LOGGER.debug(last_update)
		else:
			_LOGGER.error("Invalid response: %s", str(main_result['estado']))	
	
	def set_data(self, record):
		"""Set data using the last record from API."""
		state = {}
		for attr_name, attr_value in ATTR_MAPPINGS.items():
			if attr_value in record:
				state[attr_name] = record[attr_value]
		for attr in MS_TO_KMH_ATTRS:
			if attr in state:
				state[attr] = round(state[attr] * 3.6, 1) # m/s to km/h
		self.data = state
		
		_LOGGER.debug(state)
	
	def set_forecast_data(self, record):
		#Set data using the last record from API.
		forecast = [None] * 48
		
		for x in range(0,2):
		
			#_LOGGER.debug("Vuelta numero "+str(x+1))
			
			for i in range(0+(24*x),24+(24*x)):
					fecha = record["prediccion"]["dia"][x]["fecha"]
					hora = i;
					if hora > 23:
						hora = hora - 24
					if hora < 10:
						fecha = fecha.replace("00:00:00", "0%d:00:00" % hora)
					else:
						fecha = fecha.replace("00:00:00", "%d:00:00" % hora)
					forecast[i] = {"datetime" : fecha, "temperature": -99.0}
			
			for attr_name, attr_value in ATTR_MAPPINGS.items():
				forecastRecord = record["prediccion"]["dia"][x]
				
				
				if attr_value in forecastRecord:
					#_LOGGER.debug(forecastRecord[attr_value])
					for time in forecastRecord[attr_value]:
						
						if attr_value == "estadoCielo":					
							if 'n' in time['value'] and time['value'] != '11n':
								time['value'] = time['value'].replace("n", "")
							forecast[int(time['periodo'])+(0+(24*x))][attr_name[0]] = MAP_CONDITION[time['value']]
							
						elif attr_value == "temperatura" or attr_value == "precipitacion":
							#_LOGGER.debug(time['value'])
							value = time['value']
							#Por lo que sea a veces llega "Ip" en lugar de un cero
							if value == 'Ip':
								value = 0								
							forecast[int(time['periodo'])+(0+(24*x))][attr_name[0]] = float(value)
						
						elif attr_value == "probPrecipitacion":
							initHour = int(time['periodo'][0:2])
							finishHour = int(time['periodo'][2:4])
							
							for i in range(initHour,finishHour):
								if time['value'] != '':
									forecast[i][attr_name[0]] = int(time['value'])
								else:
									forecast[i][attr_name[0]] = time['value']
								
						elif attr_value == "vientoAndRachaMax":
							if "direccion" in time and "velocidad" in time:
								forecast[int(time['periodo'])+(0+(24*x))][ATTR_FORECAST_WIND_BEARING[0]] = WIND_DIRECTIONS[time['direccion'][0]]
								forecast[int(time['periodo'])+(0+(24*x))][ATTR_FORECAST_WIND_SPEED] = int(time['velocidad'][0])
						
						else:
							forecast[int(time['periodo'])+(0+(24*x))][attr_name[0]] = time['value']
						
					#_LOGGER.debug('----------------------')	
			
			
			#self.data["forecast"] = forecast
			
			#_LOGGER.debug(forecast)
			#_LOGGER.debug(self.data)
			
		self.data["forecast"] = self.empty_forecast_cleanup(forecast)
	
	def empty_forecast_cleanup(self, forecast):
		"""Cleanup for incomplete and past forecasts"""
		cleanList = []
		now = datetime.datetime.now()

		for i in range(0,len(forecast)):
			diff = datetime.datetime.strptime(forecast[i]["datetime"], '%Y-%m-%dT%H:%M:%S') - now;
			hours = diff.total_seconds() / 3600
			if hours > -1:
				cleanList.append(forecast[i])
		return cleanList

	def get_data(self, variable):
		"""Get the data."""
		return self.data.get(variable)
		
	def get_current_condition(self):
		"""Get the current condition from forecast"""
		forecast = self.data.get("forecast")
		_LOGGER.debug(forecast[0])		
		return forecast[0]["condition"]
		
		
def main():
	"""Set up the weather platform."""
	api_key = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJodW1hbmVzZm9ycHJlc2lkZW50QGdtYWlsLmNvbSIsImp0aSI6IjBiMTBkNGZiLTFjZjgtNDA2Ny1iNzdlLWRiZWE5NTVmYTg2ZCIsImlzcyI6IkFFTUVUIiwiaWF0IjoxNjEwNDk1MjQ3LCJ1c2VySWQiOiIwYjEwZDRmYi0xY2Y4LTQwNjctYjc3ZS1kYmVhOTU1ZmE4NmQiLCJyb2xlIjoiIn0.u_yN_8G3QDOS5KTkyLdq3E8dPSJKRXauwIdt9bzEZdk"
	station_id = "3129"
	neighborhood_id = "28123"

	aemetApi = AemetApi(api_key=api_key, station_id=station_id, neighborhood_id=neighborhood_id)
	aemetApi.update()
	
	print(str(aemetApi.get_data("forecast")))
	
	print(aemetApi.get_current_condition())


if __name__ == '__main__':
	main()