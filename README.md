 ![Screenshot](https://github.com/zyphlar/pinger/raw/master/pinger.png)

Pinger.py
=========
A ping tool that sits in your system tray
---------

- Saves your sanity when the wifi sucks
- Doesn't clutter up your screen with ping windows
- Lets you know when pings fail instead of silently failing
- **Currently for Ubuntu only**
 - (Requires Python, GTK, and AppIndicator3)
 - Startup Automatically option creates a `~/.config/autostart/pinger.desktop` file
 - **Contributions welcome to expand to other OSes!**

**Usage (in Ubuntu):**

Open the Terminal program and enter the following commands:

    cd ~
    git clone https://github.com/zyphlar/pinger.git
    python pinger/pinger.py &

Pinger should open in your system tray. To set Pinger to start automatically (in Ubuntu) click it and choose Start Automatically.

Report bugs or feature requests at https://github.com/zyphlar/pinger/issues
