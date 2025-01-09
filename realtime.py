import curses
import time
import math
from collections import deque
from datetime import datetime, timedelta
import numpy as np
import socketio
import asyncio
import signal
import sys

class PressureTrendAnalyzer:
    def __init__(self, window_hours=3, min_samples=6):
        self.window_hours = window_hours
        self.min_samples = min_samples
        self.pressure_history = deque(maxlen=500)
        
    def add_reading(self, pressure):
        self.pressure_history.append((datetime.now(), pressure))
        
    def get_trend(self):
        cutoff_time = datetime.now() - timedelta(hours=self.window_hours)
        while self.pressure_history and self.pressure_history[0][0] < cutoff_time:
            self.pressure_history.popleft()
        
        if len(self.pressure_history) < self.min_samples:
            return "INSUFFICIENT_DATA", 0
        
        times = np.array([(t - cutoff_time).total_seconds() / 3600 
                         for t, _ in self.pressure_history])
        pressures = np.array([p for _, p in self.pressure_history])
        
        slope, _ = np.polyfit(times, pressures, 1)
        change_per_hour = slope
        
        if abs(change_per_hour) < 0.02:
            return "STEADY", change_per_hour
        elif change_per_hour > 0:
            return "RISING", change_per_hour
        else:
            return "FALLING", change_per_hour

class WeatherStation:
    def __init__(self, api_key, app_key):
        self.api_key = api_key
        self.app_key = app_key
        self.sio = socketio.AsyncClient()
        self.current_data = None
        self.window = None
        self.running = True
        self.connected = False
        self.pressure_analyzer = PressureTrendAnalyzer(window_hours=3, min_samples=6)

        @self.sio.on('connect')
        async def on_connect():
            self.connected = True
            await self.sio.emit('subscribe', {'apiKeys': [self.api_key]})

        @self.sio.on('disconnect')
        async def on_disconnect():
            self.connected = False

        @self.sio.on('data')
        async def on_data(data):
            self.current_data = {'lastData': data}
            if self.window and 'baromrelin' in data:
                self.pressure_analyzer.add_reading(data['baromrelin'])
                self.display_data()

    def display_data(self):
        if not self.window:
            return

        try:
            curses.start_color()
            curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
            
            self.window.clear()
            self.window.addstr(0, 0, "Ambient Weather Station ", curses.A_BOLD)
            self.window.addstr(1, 0, "-" * 50 + "\n")

            if not self.current_data:
                self.window.addstr(2, 0, "Waiting for data...", curses.A_BOLD)
                return

            data = self.current_data['lastData']
            
            # Display all weather data
            self.window.addstr(2, 0, f"Temperature | {data.get('tempf', 'N/A')}° F\n")
            self.window.addstr(f"Humidity    | {data.get('humidity', 'N/A')} %\n")
            self.window.addstr(f"Feels Like  | {data.get('feelsLike', 'N/A')}° F\n")
            self.window.addstr(f"Dew Point   | {data.get('dewPoint', 'N/A')}° F\n")
            if 'uv' in data:
                self.window.addstr(f"UV Index    | {data.get('uv', 'N/A')}\n")
            if 'solarradiation' in data:
                self.window.addstr(f"Solar Rad   | {data.get('solarradiation', 'N/A')} W/m²\n")
            self.window.addstr(f"Downstairs  | {data.get('tempinf', 'N/A')}° / {data.get('humidityin', 'N/A')} %\n")
            if 'temp2f' in data:
                self.window.addstr(f"Upstairs    | {data.get('temp2f', 'N/A')}° / {data.get('humidity2', 'N/A')} %\n")
            
            # Enhanced barometer display
            if 'baromrelin' in data:
                current_pressure = data['baromrelin']
                trend, change_rate = self.pressure_analyzer.get_trend()
                self.window.addstr(f"Barometer   | {current_pressure:.3f} inHg ")
                
                if trend == "INSUFFICIENT_DATA":
                    self.window.addstr("(collecting data...)\n", curses.color_pair(3))
                else:
                    if trend == "RISING":
                        if abs(change_rate) > 0.06:
                            self.window.addstr("▲▲", curses.color_pair(2))
                        else:
                            self.window.addstr("▲", curses.color_pair(2))
                    elif trend == "FALLING":
                        if abs(change_rate) > 0.06:
                            self.window.addstr("▼▼", curses.color_pair(4))
                        else:
                            self.window.addstr("▼", curses.color_pair(4))
                    else:
                        self.window.addstr("▷", curses.color_pair(3))
                        
                    self.window.addstr(f" ({change_rate:+.3f}/hr)\n", curses.color_pair(1))
            
            # Wind data
            self.window.addstr(f"Wind Speed  | {data.get('windspeedmph', 'N/A')} mph")
            if 'windgustmph' in data:
                self.window.addstr(f", gust {data.get('windgustmph', 'N/A')}")
            if 'maxdailygust' in data:
                self.window.addstr(f", max {data.get('maxdailygust', 'N/A')}")
            self.window.addstr("\n")
            
            if 'winddir' in data:
                self.window.addstr(f"Wind Dir    | {wind_direction(data['winddir'])}")
                if 'winddir_avg10m' in data:
                    self.window.addstr(f", average {wind_direction(data['winddir_avg10m'])}")
                self.window.addstr("\n")
            
            self.window.addstr(f"Daily Rain  | {data.get('dailyrainin', 'N/A')} in\n")
            
            # Battery status
            if 'battout' in data:
                self.window.addstr(f"Battery     |")
                if data['battout'] == 1:
                    self.window.addstr(f" Good\n", curses.color_pair(2))
                else:
                    self.window.addstr(f" Low\n", curses.color_pair(4))
            
            self.window.addstr(f"Last Update | {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
            self.window.addstr(f"Connection  | {'Connected' if self.connected else 'Disconnected'}\n")
            
            self.window.refresh()

        except Exception as e:
            self.window.addstr(f"\nDisplay error: {str(e)}\n")
            self.window.refresh()

    async def run(self, window):
        self.window = window
        curses.curs_set(0)  # Hide cursor

        try:
            await self.sio.connect(
                f'https://rt2.ambientweather.net/?api=1&applicationKey={self.app_key}',
                transports=['websocket']
            )

            while self.running:
                self.display_data()
                await asyncio.sleep(1)

        except Exception as e:
            self.window.clear()
            self.window.addstr(0, 0, f"Error: {str(e)}")
            self.window.refresh()
            await asyncio.sleep(5)
        finally:
            if self.sio.connected:
                await self.sio.disconnect()

def wind_direction(degrees):
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 
                 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    index = math.floor((degrees + 11.25) / 22.5)
    return directions[index % 16]

async def main(window):
    api_key = ''
    app_key = ''

    station = WeatherStation(api_key, app_key)
    
    try:
        await station.run(window)
    except Exception as e:
        window.clear()
        window.addstr(0, 0, f"Error: {str(e)}")
        window.addstr(2, 0, "Press any key to exit...")
        window.refresh()
        window.getch()

def run():
    curses.wrapper(lambda w: asyncio.run(main(w)))

if __name__ == "__main__":
    run()
