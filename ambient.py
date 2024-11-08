import requests
import curses
import time
import math
from collections import deque
from datetime import datetime, timedelta
import numpy as np

class PressureTrendAnalyzer:
    def __init__(self, window_hours=3, min_samples=6):
        self.window_hours = window_hours
        self.min_samples = min_samples
        self.pressure_history = deque(maxlen=500)  # Store (timestamp, pressure) tuples
        
    def add_reading(self, pressure):
        self.pressure_history.append((datetime.now(), pressure))
        
    def get_trend(self):
        # Remove readings older than window_hours
        cutoff_time = datetime.now() - timedelta(hours=self.window_hours)
        while self.pressure_history and self.pressure_history[0][0] < cutoff_time:
            self.pressure_history.popleft()
        
        if len(self.pressure_history) < self.min_samples:
            return "INSUFFICIENT_DATA", 0
        
        # Convert to numpy arrays for analysis
        times = np.array([(t - cutoff_time).total_seconds() / 3600 
                         for t, _ in self.pressure_history])
        pressures = np.array([p for _, p in self.pressure_history])
        
        # Calculate linear regression
        slope, _ = np.polyfit(times, pressures, 1)
        
        # Convert slope to change per hour
        change_per_hour = slope
        
        # Categorize the trend
        if abs(change_per_hour) < 0.02:
            return "STEADY", change_per_hour
        elif change_per_hour > 0:
            return "RISING", change_per_hour
        else:
            return "FALLING", change_per_hour

def display_data(window, data, pressure_analyzer):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
    
    window.clear()
    window.addstr(0, 0, "Ambient Weather Station ", curses.A_BOLD)
    window.addstr(1, 0, "-" * curses.COLS)
    window.addstr(f"Temperature | {data['lastData']['tempf']}° F\n")
    window.addstr(f"Humidity    | {data['lastData']['humidity']} %\n")
    window.addstr(f"Feels Like  | {data['lastData']['feelsLike']}° F\n")
    window.addstr(f"Dew Point   | {data['lastData']['dewPoint']}° F\n")
    window.addstr(f"UV Index    | {data['lastData']['uv']}\n")
    window.addstr(f"Solar Rad   | {data['lastData']['solarradiation']} W/m²\n")
    window.addstr(f"Downstairs  | {data['lastData']['tempinf']}° / {data['lastData']['humidityin']} %\n")
    window.addstr(f"Upstairs    | {data['lastData']['temp2f']}° / {data['lastData']['humidity2']} %\n")
    
    # Enhanced barometer display
    current_pressure = data['lastData']['baromrelin']
    trend, change_rate = pressure_analyzer.get_trend()
    window.addstr(f"Barometer   | {current_pressure:.3f} inHg ")
    
    if trend == "INSUFFICIENT_DATA":
        window.addstr("(collecting data...)\n", curses.color_pair(3))
    else:
        # Display trend arrow
        if trend == "RISING":
            if abs(change_rate) > 0.06:
                window.addstr("▲▲", curses.color_pair(2))  # Fast rise
            else:
                window.addstr("▲", curses.color_pair(2))   # Slow rise
        elif trend == "FALLING":
            if abs(change_rate) > 0.06:
                window.addstr("▼▼", curses.color_pair(4))  # Fast fall
            else:
                window.addstr("▼", curses.color_pair(4))   # Slow fall
        else:
            window.addstr("▷", curses.color_pair(3))      # Steady
            
        # Display numeric trend
        window.addstr(f" ({change_rate:+.3f}/hr)\n", curses.color_pair(1))
    
    window.addstr(f"Wind Speed  | {data['lastData']['windspeedmph']} mph")
    window.addstr(f", gust {data['lastData']['windgustmph']}")
    window.addstr(f", max {data['lastData']['maxdailygust']}\n")
    window.addstr(f"Wind Dir    | {wind_direction(data['lastData']['winddir'])}")
    window.addstr(f", average {wind_direction(data['lastData']['winddir_avg10m'])}\n")
    window.addstr(f"Daily Rain  | {data['lastData']['dailyrainin']} in\n")
    window.addstr(f"Battery     |")
    if data['lastData']['battout'] == 1:
        window.addstr(f" Good\n", curses.color_pair(2))
    else:
        window.addstr(f" Low\n", curses.color_pair(4))
    window.addstr(f"Last Update | {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
    window.refresh()

def wind_direction(degrees):
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 
                 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    index = math.floor((degrees + 11.25) / 22.5)
    return directions[index % 16]

def main(window):
    api_key = ''
    app_key = ''
    url = f'https://rt.ambientweather.net/v1/devices?apiKey={api_key}&applicationKey={app_key}&limit=1'
    
    pressure_analyzer = PressureTrendAnalyzer(window_hours=3, min_samples=6)
    
    while True:
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()[0]
            
            current_pressure = data['lastData']['baromrelin']
            pressure_analyzer.add_reading(current_pressure)
            display_data(window, data, pressure_analyzer)
            
            time.sleep(30)
        except (IndexError, KeyError, requests.exceptions.RequestException, 
                requests.exceptions.HTTPError) as e:
            window.addstr("\nLast request failed; retrying shortly.\n")
            window.refresh()
            time.sleep(10)
        continue

curses.wrapper(main)
