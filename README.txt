Pinger.py -- A ping tool that sits in your system tray

+ Currently for Ubuntu only
  - (Requires Python, GTK, and AppIndicator3)
  - Contributions welcome to implement cross-platform!
+ Saves your sanity when the wifi sucks
+ Doesn't clutter up your screen with ping windows
+ Lets you know when pings fail instead of silently failing

Usage (in Ubuntu):

Open the Terminal program and enter the following commands:
  cd ~
  git clone https://github.com/zyphlar/pinger.git

Open the Startup Applications program and click Add

Name: Pinger
Command: python ~/pinger/pinger.py

Click Save, and Close. Pinger should now start automatically in your system tray when you login next. (It just says "xx.x ms"). You can test it manually by typing python ~/pinger/pinger.py in your terminal and pressing enter. 

Report bugs or feature requests at https://github.com/zyphlar/pinger/issues
