# ambient_weather_curses
Simple app which polls the Ambient Weather API and displays data via ncurses. By simple, I mean it. 

Wind direction is converted from degrees to cardinal directions, and a rudimentary bit of logic is used to show whether or not the barometer is rising or falling since the last reading. I should probably save a few readings and check the current against the average and will probably add that soon.

I had originally wanted to use Ambient's realtime API but this was simpler, and I leaned heavily (read: _nearly completely_) on ChatGPT3 to produce it. 

One interesting bit - I had originally requested the ability to press `q` to quit. The AI dutifully added a `getch` clause, but then the program never refreshed. Do you know why? It turns out that `getch` blocks while waiting for input. I spent entirely too much time  troubleshooting the API and other things before figuring this out and asking the AI repeatedly "why isn't this working as expected." 

When I mentioned the `getch` behavior to the AI, it agreed! Yes, `getch` blocks and this is why the program wasn't refreshing as expected. Well...thanks I guess. It offered up an alternative solution which also did not work,  so just hit CTRL-C to quit.  In any event, the AI got me closer to complete than I would have gotten on my own.

You'll also notice that I'm not using any of the ambient-specific python packages; this is also by design. OpenAI only knows about the packages up to 2021, and the packages have progressed considerably since then. 

The data updates every 30 seconds and can handle minor cloudflare hiccups or API errors.

* Ambient's API docs: https://ambientweather.docs.apiary.io/#
* My pairs programming partner: https://chat.openai.com

![screenshot](screenshot.png)

 
