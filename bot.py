import slack
import os
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask
from slackeventsapi import SlackEventAdapter
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import difflib
import csv
import requests
import json
import nltk
nltk.download('punkt')


env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'],'/slack/events',app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call("auth.test")['user_id']
#client.chat_postMessage(channel='#test', text="Hello World!")

api_key = "e8e3a8c1f50056504e4758dfdf655457"
base_url = "http://api.openweathermap.org/data/2.5/weather?"

def readCities():

    """ This function loads a database of cities in a separate csv file stored in the same directory"""

    cities = []

    with open('cities.csv', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            city = row[0]
            cities.append(city)

    return cities

def sanitize(sentence):

    """This function accepts a text string and return a
    list of strings with common stopwords removed"""

    stop_words = set(stopwords.words('english'))
    word_tokens = word_tokenize(sentence)
    filtered_sentence = [w for w in word_tokens if not w in stop_words]

    return filtered_sentence

def checkCity(filtered_sentence):

    """ This function checks whether a list contains cities using close matching"""

    cities = readCities()
    cities_found = []

    for word in filtered_sentence:
        matches = difflib.get_close_matches(word.capitalize(), cities, 1, cutoff=0.85)
        if len(matches) == 0:
            pass
        else:
            cities_found.append(matches[0])

    if len(cities_found) == 0:
        return False
    else:
        return cities_found

def getWeather(city, api_key):

    """ This function uses the OpenWeatherData api to retrieve JSON organized weather data by city_name"""

    complete_url = base_url + "&q=" + city +"&units=metric" + "&appid=" + api_key
    response = requests.get(complete_url)
    data = json.loads(response.text)
    return data

def parseSlackReply(city, data):

    """This function builds a reply string to post to Slack"""

    reply = "The weather in " \
            + city \
            + " is currently " \
            + str(data['main']['temp']) \
            + "°C, but feels like " \
            + str(data['main']['feels_like']) \
            + "°C, and " \
            + str(data['weather'][0]['description'])

    return reply


@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')

    if BOT_ID != user_id:

        client.chat_postMessage(channel=channel_id, text=text)

        sanSentence = sanitize(text)

        if checkCity(sanSentence):
            print(sanSentence)
            for city in checkCity(sanSentence):
                data = getWeather(city, api_key)
                client.chat_postMessage(channel=channel_id, text=parseSlackReply(city, data))


if __name__ == "__main__":
    app.run(debug=True)