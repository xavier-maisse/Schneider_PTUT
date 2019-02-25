#!/usr/bin/python

from datetime import datetime
import json
import time

import Adafruit_DHT
import requests

class Sharepoint:
    CONFIG_FILE = 'config.json'

    config = {}

    def __init__(self):
        self.readConfig()

    def getList(self, title):
        headers = {
            'Authorization': 'Bearer {}'.format(self.config['access_token']),
            'Accept': 'application/json'
        }

        r = requests.get(self.config['sharepoint_url'] + "lists/GetByTitle('{}')".format(title), headers=headers)

        if r.status_code == 401:
            if not self.refreshToken():
                raise RuntimeError('Cannot refresh access token')

            return self.getList(title)
        elif r.status_code == 404:
            raise RuntimeError('List "{}" does not exist'.format(title))
        elif r.status_code != 200:
            raise RuntimeError('List "{}" returned status code {}'.format(title, r.status_code))

        return json.loads(r.text)
    
    def addInformation(self, humidity, temperature):
        list_info = self.getList('Environnement')

        list_url = list_info['odata.id']

        headers = {
            'Authorization': 'Bearer {}'.format(self.config['access_token']),
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        date = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ') # UTC date format

        data = {
            'Date_x002f_Heure': date,
            'Capteur_x0020_1': str(humidity),
            'Capteur_x0020_2': str(temperature)
        }

        r = requests.post('{}/items'.format(list_url), json=data, headers=headers)

        if r.status_code == 401:
            if not self.refreshToken():
                raise RuntimeError('Cannot refresh access token')

            return self.addInformation(humidity, temperature)
        elif r.status_code != 201:
            raise RuntimeError('Cannot add list item, returned status code {}'.format(r.status_code))

        return True
    
    # OAuth

    def refreshToken(self):
        print('[?] Refreshing access token...')

        r = requests.post('https://login.microsoftonline.com/common/oauth2/token', data={
            'grant_type': 'refresh_token',
            'refresh_token': self.config['refresh_token'],
            'client_id': self.config['client_id'],
            'client_secret': self.config['client_secret']
        })

        if r.status_code != 200:
            print('[-] Failed to refresh access token!')

            return False

        response = json.loads(r.text)

        self.config['access_token'] = response['access_token']
        self.config['refresh_token'] = response['refresh_token']

        self.saveConfig()

        print('[+] Access token refreshed!')

        return True

    # Config

    def readConfig(self):
        with open(self.CONFIG_FILE) as f:
            self.config = json.load(f)
        
        return self.config
    
    def saveConfig(self):
        with open(self.CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)

sharepoint = Sharepoint()

while True:
    humidity, temperature = Adafruit_DHT.read_retry(11, 4)

    print('[?] Reading probe...')
    print('[?] Temp: {0:0.1f} C  Humidity: {1:0.1f} %'.format(temperature, humidity))

    try:
        if sharepoint.addInformation(humidity, temperature):
            print('[+] Saved probe values to Sharepoint!')
        else:
            print('[!] Cannot save probe values to Sharepoint!')
    except RuntimeError as e:
        print('[!] Cannot save probe values to Sharepoint: {}'.format(e))

    time.sleep(5)

    print()
