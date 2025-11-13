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
import ephem
from zoneinfo import ZoneInfo

class AlmanacCalculator:
    def __init__(self, lat, lon, timezone='America/Chicago'):
        self.observer = ephem.Observer()
        self.observer.lat = str(lat)
        self.observer.lon = str(lon)
        self.observer.elevation = 0
        self.timezone = ZoneInfo(timezone)
        
    def get_almanac_data(self):
        """Calculate sunrise, sunset, day length, moon phase, and Az/El data"""
        # Use current time in UTC for ephem calculations
        now_utc = datetime.now(ZoneInfo('UTC'))
        self.observer.date = now_utc
        
        sun = ephem.Sun()
        moon = ephem.Moon()
        
        # Compute current positions
        sun.compute(self.observer)
        moon.compute(self.observer)
        
        # Initialize variables
        sunrise_local = None
        sunset_local = None
        solar_noon_local = None
        moonrise_local = None
        moonset_local = None
        hours = 0
        minutes = 0
        
        # Calculate sun times for today
       
        sun = ephem.Sun()

        try:
            # Use local midnight as the start of "today" (matches USNO)
            local_now = now_utc.astimezone(self.timezone)
            local_today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

            today_start_utc = local_today_start.astimezone(ZoneInfo("UTC"))
            tomorrow_start_utc = (local_today_start + timedelta(days=1)).astimezone(ZoneInfo("UTC"))

            self.observer.date = ephem.Date(today_start_utc)
            next_sunrise_utc = self.observer.next_rising(sun).datetime()

            if next_sunrise_utc < tomorrow_start_utc.replace(tzinfo=None):
                sunrise_local = next_sunrise_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(self.timezone)
            else:
                sunrise_local = None

        except (ephem.AlwaysUpError, ephem.NeverUpError):
            sunrise_local = None

        try:
            # Same logic for sunset
            local_now = now_utc.astimezone(self.timezone)
            local_today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

            today_start_utc = local_today_start.astimezone(ZoneInfo("UTC"))
            tomorrow_start_utc = (local_today_start + timedelta(days=1)).astimezone(ZoneInfo("UTC"))

            self.observer.date = ephem.Date(today_start_utc)
            next_sunset_utc = self.observer.next_setting(sun).datetime()

            if next_sunset_utc < tomorrow_start_utc.replace(tzinfo=None):
                sunset_local = next_sunset_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(self.timezone)
            else:
                sunset_local = None

        except (ephem.AlwaysUpError, ephem.NeverUpError):
            sunset_local = None

        # --- Solar noon and day length ---
        try:
            # Calculate solar noon as the Sun's upper transit
            self.observer.date = ephem.Date(today_start_utc)
            solar_noon_utc = self.observer.next_transit(sun).datetime()
            solar_noon_local = solar_noon_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(self.timezone)
        except (ephem.AlwaysUpError, ephem.NeverUpError):
            solar_noon_local = None

        if sunrise_local and sunset_local:
            day_length_td = sunset_local - sunrise_local
            hours, remainder = divmod(int(day_length_td.total_seconds()), 3600)
            minutes = remainder // 60
            day_length_str = f"{hours}h {minutes}m"
        else:
            day_length_str = "N/A"
        
        # Get moon rise and set times for today
        # --- Moon rise and set times ---
        moon = ephem.Moon()

        try:
            # Use local midnight as the start of "today" (matches USNO)
            local_now = now_utc.astimezone(self.timezone)
            local_today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

            today_start_utc = local_today_start.astimezone(ZoneInfo("UTC"))
            tomorrow_start_utc = (local_today_start + timedelta(days=1)).astimezone(ZoneInfo("UTC"))

            self.observer.date = ephem.Date(today_start_utc)
            next_moonrise_utc = self.observer.next_rising(moon).datetime()

            if next_moonrise_utc < tomorrow_start_utc.replace(tzinfo=None):
                moonrise_local = next_moonrise_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(self.timezone)
            else:
                moonrise_local = None

        except (ephem.AlwaysUpError, ephem.NeverUpError):
            moonrise_local = None

        try:
            # Same logic for moonset
            local_now = now_utc.astimezone(self.timezone)
            local_today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)

            today_start_utc = local_today_start.astimezone(ZoneInfo("UTC"))
            tomorrow_start_utc = (local_today_start + timedelta(days=1)).astimezone(ZoneInfo("UTC"))

            self.observer.date = ephem.Date(today_start_utc)
            next_moonset_utc = self.observer.next_setting(moon).datetime()

            if next_moonset_utc < tomorrow_start_utc.replace(tzinfo=None):
                moonset_local = next_moonset_utc.replace(tzinfo=ZoneInfo("UTC")).astimezone(self.timezone)
            else:
                moonset_local = None

        except (ephem.AlwaysUpError, ephem.NeverUpError):
            moonset_local = None

        
        # Reset observer date to now for current Az/El calculations
        self.observer.date = now_utc
        sun.compute(self.observer)
        moon.compute(self.observer)
        
        # Calculate moon phase
        moon_phase = moon.phase  # 0-100, percentage illuminated
        
        # Get previous new moon to calculate moon age
        previous_new = ephem.previous_new_moon(self.observer.date)
        # Calculate days since new moon
        moon_age_days = self.observer.date - previous_new
        
        # Calculate phase angle (0-360 degrees through lunar cycle)
        # Lunar cycle is approximately 29.53 days
        phase_angle = (float(moon_age_days) / 29.53) * 360
        
        # Determine phase name based on phase angle with tighter ranges
        # The four primary phases are narrow, the intermediate phases are wider
        if phase_angle < 11.25 or phase_angle >= 348.75:
            phase_name = "🌑"
        elif phase_angle < 78.75:
            phase_name = "🌒"
        elif phase_angle < 101.25:
            phase_name = "🌓"
        elif phase_angle < 168.75:
            phase_name = "🌔"
        elif phase_angle < 191.25:
            phase_name = "🌕"
        elif phase_angle < 258.75:
            phase_name = "🌖"
        elif phase_angle < 281.25:
            phase_name = "🌗"
        else:
            phase_name = "🌘"
        
        # Convert azimuth and altitude from radians to degrees
        sun_az = math.degrees(sun.az)
        sun_alt = math.degrees(sun.alt)
        moon_az = math.degrees(moon.az)
        moon_alt = math.degrees(moon.alt)
        
        return {
            'sunrise': sunrise_local,
            'sunset': sunset_local,
            'solar_noon': solar_noon_local,
            'day_length_hours': hours,
            'day_length_minutes': minutes,
            'moon_phase': moon_phase,
            'moon_phase_name': phase_name,
            'sun_azimuth': sun_az,
            'sun_altitude': sun_alt,
            'moon_azimuth': moon_az,
            'moon_altitude': moon_alt,
            'moonrise': moonrise_local,
            'moonset': moonset_local
        }

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
    def __init__(self, api_key, app_key, latitude, longitude, timezone='America/Chicago'):
        self.api_key = api_key
        self.app_key = app_key
        self.sio = socketio.AsyncClient()
        self.current_data = None
        self.screen = None
        self.running = True
        self.connected = False
        self.pressure_analyzer = PressureTrendAnalyzer(window_hours=3, min_samples=6)
        self.almanac = AlmanacCalculator(latitude, longitude, timezone)
        self.pad = None

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
            if 'baromrelin' in data:
                self.pressure_analyzer.add_reading(data['baromrelin'])
            if self.screen:
                self.display_data()

    def init_display(self, screen):
        self.screen = screen
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_GREEN, -1)
        curses.init_pair(3, curses.COLOR_YELLOW, -1)
        curses.init_pair(4, curses.COLOR_RED, -1)
        # Create pad with extra space for almanac data
        self.pad = curses.newpad(40, 100)

    def display_data(self):
        if not self.screen or not self.pad:
            return

        try:
            self.pad.clear()
            self.pad.addstr(0, 0, "Ambient Weather Station ", curses.A_BOLD)
            self.pad.addstr(1, 0, "-" * 50 + "\n")

            if not self.current_data:
                self.pad.addstr(2, 0, "Waiting for data...", curses.A_BOLD)
                self.refresh_display()
                return

            data = self.current_data
            last_data = data['lastData']
            current_line = 2

            self.pad.addstr(current_line, 0, f"Temperature | {last_data['tempf']}° F\n")
            current_line += 1
            self.pad.addstr(current_line, 0, f"Humidity    | {last_data['humidity']} %\n")
            current_line += 1
            self.pad.addstr(current_line, 0, f"Feels Like  | {last_data['feelsLike']}° F\n")
            current_line += 1
            self.pad.addstr(current_line, 0, f"Dew Point   | {last_data['dewPoint']}° F\n")
            current_line += 1
            
            if 'baromrelin' in last_data:
                current_pressure = last_data['baromrelin']
                trend, change_rate = self.pressure_analyzer.get_trend()
                self.pad.addstr(current_line, 0, f"Barometer   | {current_pressure:.3f} inHg ")
                
                if trend == "INSUFFICIENT_DATA":
                    self.pad.addstr("(collecting data...)\n", curses.color_pair(3))
                else:
                    if trend == "RISING":
                        if abs(change_rate) > 0.06:
                            self.pad.addstr("▲▲", curses.color_pair(2))
                        else:
                            self.pad.addstr("▲", curses.color_pair(2))
                    elif trend == "FALLING":
                        if abs(change_rate) > 0.06:
                            self.pad.addstr("▼▼", curses.color_pair(4))
                        else:
                            self.pad.addstr("▼", curses.color_pair(4))
                    else:
                        self.pad.addstr("▷", curses.color_pair(3))
                        
                    self.pad.addstr(f" ({change_rate:+.3f}/hr)\n", curses.color_pair(1))
                current_line += 1

            if 'uv' in last_data:
                self.pad.addstr(current_line, 0, f"UV Index    | {last_data['uv']}\n")
                current_line += 1
            if 'solarradiation' in last_data:
                self.pad.addstr(current_line, 0, f"Solar Rad   | {last_data['solarradiation']} W/m²\n")
                current_line += 1

            self.pad.addstr(current_line, 0, f"Downstairs  | {last_data['tempinf']}° / {last_data['humidityin']} %\n")
            current_line += 1
            self.pad.addstr(current_line, 0, f"Upstairs    | {last_data['temp2f']}° / {last_data['humidity2']} %\n")
            current_line += 1

            self.pad.addstr(current_line, 0, f"Wind Speed  | {last_data['windspeedmph']} mph")
            if 'windgustmph' in last_data:
                self.pad.addstr(f", gust {last_data['windgustmph']}")
            if 'maxdailygust' in last_data:
                self.pad.addstr(f", max {last_data['maxdailygust']}")
            self.pad.addstr("\n")
            current_line += 1

            if 'winddir' in last_data:
                self.pad.addstr(current_line, 0, f"Wind Dir    | {wind_direction(last_data['winddir'])}")
                if 'winddir_avg10m' in last_data:
                    self.pad.addstr(f", average {wind_direction(last_data['winddir_avg10m'])}")
                self.pad.addstr("\n")
                current_line += 1

            self.pad.addstr(current_line, 0, f"Daily Rain  | {last_data['dailyrainin']} in\n")
            current_line += 1
            
            if 'battout' in last_data:
                self.pad.addstr(current_line, 0, f"Battery     |")
                if last_data['battout'] == 1:
                    self.pad.addstr(f" Good\n", curses.color_pair(2))
                else:
                    self.pad.addstr(f" Low\n", curses.color_pair(4))
                current_line += 1
            
            # Add almanac information
            self.pad.addstr(current_line, 0, "-" * 50 + "\n")
            current_line += 1
            
            almanac_data = self.almanac.get_almanac_data()
            
            if almanac_data['sunrise']:
                self.pad.addstr(current_line, 0, 
                    f"Sunrise     | {almanac_data['sunrise'].strftime('%I:%M %p')}\n")
                current_line += 1
            
            if almanac_data['solar_noon']:
                self.pad.addstr(current_line, 0, 
                    f"Solar Noon  | {almanac_data['solar_noon'].strftime('%I:%M %p')}\n")
                current_line += 1
            
            if almanac_data['sunset']:
                self.pad.addstr(current_line, 0, 
                    f"Sunset      | {almanac_data['sunset'].strftime('%I:%M %p')}\n")
                current_line += 1
            
            self.pad.addstr(current_line, 0, 
                f"Day Length  | {almanac_data['day_length_hours']}h {almanac_data['day_length_minutes']}m\n")
            current_line += 1
            
            # Sun position
            self.pad.addstr(current_line, 0, 
                f"Sun         | Az: {almanac_data['sun_azimuth']:.1f}° El: {almanac_data['sun_altitude']:.1f}°\n")
            current_line += 1
            
            # Moon phase and position
            self.pad.addstr(current_line, 0, 
                f"Moon Phase  | {almanac_data['moon_phase_name']} ({almanac_data['moon_phase']:.1f}%)\n")
            current_line += 1
            
            self.pad.addstr(current_line, 0, 
                f"Moon        | Az: {almanac_data['moon_azimuth']:.1f}° El: {almanac_data['moon_altitude']:.1f}°\n")
            current_line += 1
            
            if almanac_data['moonrise']:
                self.pad.addstr(current_line, 0, 
                    f"Moonrise    | {almanac_data['moonrise'].strftime('%I:%M %p')}\n")
                current_line += 1
            
            if almanac_data['moonset']:
                self.pad.addstr(current_line, 0, 
                    f"Moonset     | {almanac_data['moonset'].strftime('%I:%M %p')}\n")
                current_line += 1
            
            self.pad.addstr(current_line, 0, "-" * 50 + "\n")
            current_line += 1
            
            self.pad.addstr(current_line, 0, f"Last Update | {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
            current_line += 1
            self.pad.addstr(current_line, 0, f"Connection  | {'Connected' if self.connected else 'Disconnected'}\n")

            self.refresh_display()
            
        except Exception as e:
            self.pad.addstr(current_line + 1, 0, f"\nDisplay error: {str(e)}\n")
            self.refresh_display()

    def refresh_display(self):
        # Get the current screen dimensions
        max_y, max_x = self.screen.getmaxyx()
        # Refresh the pad, showing as much as will fit in the terminal
        self.pad.refresh(0, 0, 0, 0, max_y-1, max_x-1)

    async def run(self, screen):
        self.init_display(screen)
        curses.curs_set(0)  # Hide cursor

        try:
            await self.sio.connect(
                f'https://rt2.ambientweather.net/?api=1&applicationKey={self.app_key}',
                transports=['websocket']
            )

            while self.running:
                await asyncio.sleep(1)

        except Exception as e:
            self.pad.clear()
            self.pad.addstr(0, 0, f"Error: {str(e)}")
            self.refresh_display()
            await asyncio.sleep(5)
        finally:
            if self.sio.connected:
                await self.sio.disconnect()

def wind_direction(degrees):
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    index = math.floor((degrees + 11.25) / 22.5)
    return directions[index % 16]

async def main(screen):

    # add your ambientweather keys here
    api_key = ''
    app_key = ''
   
    # edit to reflect your location (NN.NNNNNN) and local timezone
    latitude = 35.772846
    longitude = -86.46821
    timezone = 'America/Chicago'  # Central Time with automatic DST

    station = WeatherStation(api_key, app_key, latitude, longitude, timezone)
    
    try:
        await station.run(screen)
    except Exception as e:
        screen.clear()
        screen.addstr(0, 0, f"Error: {str(e)}")
        screen.addstr(2, 0, "Press any key to exit...")
        screen.refresh()
        screen.getch()

def run():
    curses.wrapper(lambda w: asyncio.run(main(w)))

if __name__ == "__main__":
    run()
