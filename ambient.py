import requests
import curses
import time
import math
import logging

def display_data(window, data, pressures):

    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)

    window.clear()
    window.addstr(0,0, "Ambient Weather Station ", curses.A_BOLD)
    window.addstr(1, 0, "-" * curses.COLS)
    window.addstr(f"Outside Temperature | {data['lastData']['tempf']}° F\n")
    window.addstr(f"Outside Humidity    | {data['lastData']['humidity']} %\n")
    window.addstr(f"Feels Like          | {data['lastData']['feelsLike']}° F\n")
    window.addstr(f"Dew Point           | {data['lastData']['dewPoint']}° F\n")
    window.addstr(f"UV Index            | {data['lastData']['uv']}\n")
    window.addstr(f"Solar radiation     | {data['lastData']['solarradiation']} W/m²\n")
    window.addstr(f"Inside Temperature  | {data['lastData']['tempinf']}° F\n")
    window.addstr(f"Inside Humidity     | {data['lastData']['humidityin']} %\n")
    window.addstr(f"Barometer           | {data['lastData']['baromrelin']} inHg ")
    if len(pressures) >= 2:
        last_pressure = pressures[-2]
        current_pressure = pressures[-1]
        if current_pressure > last_pressure:
            window.addstr("▲\n",  curses.color_pair(2))
        elif current_pressure < last_pressure:
            window.addstr("▼\n",  curses.color_pair(4))
        else:
            window.addstr("▷\n", curses.color_pair(3))
    else:
        window.addstr("\n")
    window.addstr(f"Wind Speed          | {data['lastData']['windspeedmph']} mph")
    window.addstr(f", gust {data['lastData']['windgustmph']}")
    window.addstr(f", max {data['lastData']['maxdailygust']}\n")
    window.addstr(f"Wind Direction      | {wind_direction(data['lastData']['winddir'])}")
    window.addstr(f", averaging {wind_direction(data['lastData']['winddir_avg10m'])}\n")
    window.addstr(f"Daily Rain          | {data['lastData']['dailyrainin']} in\n")
    window.addstr(f"Station Battery     |")
    if data['lastData']['battout'] == 1:
        window.addstr(f" Good\n",  curses.color_pair(2))
    else:
        window.addstr(f" Low\n"),  curses.color_pair(4)
    window.addstr(f"Last Update         | {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
    window.refresh()

def wind_direction(degrees):
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    index = math.floor((degrees + 11.25) / 22.5)
    return directions[index % 16]

def main(window):
    api_key = 'f98244e5f44747e796521fc7287db95c7fa44bde35474b5298fca4c79a003025'
    app_key = 'f05a140c16724912b981f1a5f668a44a327bf91c40624e33b1ebe3f31dddba8d'
    url = f'https://rt.ambientweather.net/v1/devices?apiKey={api_key}&applicationKey={app_key}&limit=1'
    pressures = []

    while True:
        response = requests.get(url)
        if response.status_code ==  401: # ignore the occasional cloudflare hiccup
           pass
        if requests.exceptions.RequestException:
           pass  # ignore failed request, wait until next loop
        data = response.json()[0]
        pressures.append(data['lastData']['baromrelin'])
        display_data(window, data, pressures)
        time.sleep(30)

curses.wrapper(main)
