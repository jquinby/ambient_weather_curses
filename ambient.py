import requests
import curses
import time
import math

def display_data(window, data, pressures):

    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)

    window.clear()
    window.addstr(0,0, "Ambient Weather Station ", curses.A_BOLD)
    window.addstr(1,0, "-" * curses.COLS)
    window.addstr(f"Outside Temperature | {data['lastData']['tempf']}° F\n")
    window.addstr(f"Outside Humidity    | {data['lastData']['humidity']} %\n")
    window.addstr(f"Feels Like          | {data['lastData']['feelsLike']}° F\n")
    window.addstr(f"Dew Point           | {data['lastData']['dewPoint']}° F\n")
    window.addstr(f"UV Index            | {data['lastData']['uv']}\n")
    window.addstr(f"Solar radiation     | {data['lastData']['solarradiation']} W/m²\n")
    window.addstr(f"Downstairs          | {data['lastData']['tempinf']}° / {data['lastData']['humidityin']} %\n")
    window.addstr(f"Upstairs       :w
    | {data['lastData']['temp2f']}° / {data['lastData']['humidity2']} %\n")
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
    window.addstr(f", average {wind_direction(data['lastData']['winddir_avg10m'])}\n")
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
    # add your respective keys below; you can get generate them in the AmbientWeather dashboard.    
    api_key = ''
    app_key = ''
    url = f'https://rt.ambientweather.net/v1/devices?apiKey={api_key}&applicationKey={app_key}&limit=1'
    pressures = []

    while True:
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()[0]
            pressures.append(data['lastData']['baromrelin'])
            display_data(window, data, pressures)
            time.sleep(30)
        except (IndexError,KeyError,requests.exceptions.RequestException,requests.exceptions.HTTPError):
            print("\nLast request failed; retrying shortly.\n")
            time.sleep(10)
        continue

curses.wrapper(main)
