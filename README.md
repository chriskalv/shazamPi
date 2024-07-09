shazamPi
========================

### What is it?
+ In essence, shazamPi is a device to record, analyze and identify music, similar to the famous **Shazam** app for smartphones. 

+ The code is entirely python-based and the device is fairly easy to build. No soldering is required.

### Who is it for?
+ With its big red button, it is supposed to invite people to record snippets and tag tracks. All analysis results are sent out via eMail to as many people as you want.

+ In my opinion, the perfect application for this device is on a festival totem. You can paste all eMails of your crew members into `shazampi.py` before an event and everybody will be able to record snippets of a track they like by pressing the red button. At the end of the event, all analyzed track results are sent out to all eMail addresses, creating a shared experience for the whole group. Another fun idea would be to mount the device on one's desk in order to quickly tag a song whenever it comes up in a set, for example.

### Context
This device is the next iteration of my initial [shazamPi Zero Project](https://github.com/chriskalv/shazamPi_Zero). While the previous one was meant to be as small as possible to fit in a little bag and replace an app on a smartphone, I wanted this version to be about the community aspect of tagging tracks with your friends and sharing the results, so I enhanced the device by using a Raspberry Pi instead of a Pi Zero, equipped it with a bigger battery to last through a whole day, a USB microphone instead of a HAT, a small display for fun and a little bit of info, a huge red button with an LED and - on the software side of things - an audio equalizer in order to remove some of the unwanted bass in recordings to get better analysis results; I dare say better results than with my smartphone. In the end, I mounted the device onto a large pole that I took to various dancefloors on festivals and everybody could smash that big red button (which reads *geiler Track = awesome track* in German) to record a snippet and tag a track.


## Hardware
+ [Raspberry Pi 4](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/)
+ [Metal Case](https://geekworm.com/collections/raspberry-pi/products/raspberry-pi-4-model-b-armor-aluminum-alloy-case-protective-shell)
+ [Big Red Button with LED](https://www.berrybase.de/en/massive-arcade-button-100mm-beleuchtet-led-12v-dc?number=AB100L12-R)
+ [USB Microphone](https://www.amazon.de/gp/product/B0BZNJSMVM?psc=1) (any mic that works with linux will do)
+ [MicroSD Card](https://www.westerndigital.com/products/memory-cards/sandisk-extreme-uhs-i-microsd#SDSQXAF-032G-GN6MA) (pretty much any will do)
+ [Powerbank](https://www.amazon.de/gp/product/B0CGX6H8MQ?psc=1) (pretty much any 5V will do)
+ [Adafruit 128x32 OLED Display](https://learn.adafruit.com/adafruit-pioled-128x32-mini-oled-for-raspberry-pi/overview) (this is obviously not necessary and just a little additional gadget)
+ Four cables to connect GPIO pins with the big red button. Two for LED functionality and two for trigger functionality.

<br></br>
| The shazamPi in its natural habitat on a rainbow totem | Close-up of the assembled device |
| :-------------: | :-------------: |
| [![](https://i.imgur.com/Xtr6ozU.jpeg?raw=true)](https://i.imgur.com/Xtr6ozU.jpeg]) | [![](https://i.imgur.com/ufYXtpC.png?raw=true)](https://i.imgur.com/ufYXtpC.png])
| Assembled device in airtight case (ready to be mounted)  | Red means recording   |
| [![](https://i.imgur.com/bHJw52Y.jpeg?raw=true)](https://i.imgur.com/bHJw52Y.jpeg)   |   [![](https://i.imgur.com/9oyEOcI.jpeg?raw=true)](https://i.imgur.com/9oyEOcI.jpeg)   |

<br></br>

## Functionality

1. On **booting up** the device by switching on the power supply (in this case hooking up the powerbank):
   + Power-saving measures are activated.
   + The shazampi.py script is started. 
   + Once everything is operational, the green LED on the Pi's board starts to blink slowly, signaling the device is _'ready to be used'_.
   + The display either
     - a) reads "PUSH!" in case the device is not connected to the internet (= the user is away from home) or
     - b) shows your network IP, device name and how many tracks are ready to be analyzed in case the device is connected to the internet (= the user is home).

2. On **pushing the big red button**, the device checks for an internet connection again.
   + If there is no internet connection (= the user is away from home):
      - An audio clip is recorded while a red LED illuminates the big red button and the display reads "RECORDING!" (as seen on the picture above).
      - After recording, the new file is stored on the microSD card.
      - The newly recorded file gets sent through an equalizer software in order to remove most of the bass, which improves analysis results and is saved to another folder.
      - Once finished, the device reverts back to the _'ready to be used'_ status, the button LED is switched off and the green LED on the Pi's board starts to blink slowly again.
   + If there is an internet connection (= the user is home):
      - All previously recorded and equalized clips are analyzed for artist and track name data while the display reads "TAGGING!".
      - All analysis results are stored in a log file and are then sent via eMail, if this is enabled within the global settings of `shazampi.py`. 
      - All analyzed source clips are renamed to their respective tags and moved to a seperate directory on the microSD card, so they won't be analyzed a second time. 
      - Once finished, the devices reverts back to the _'ready to be used'_ status (green LED on the Pi's board slowly blinking again).

## Setup
1. Assemble the hardware:
   - Put the case onto the Raspberry Pi
   - Hook up the microphone via USB
   - Push the mini display onto the respective GPIO pins
   - Connect the big red arcade button to the GPIO pins you intend to use. Personally, I used GPIO10 (Pin 19) and GND (Pin 9) for the button's trigger functionality as well as GPIO17 (Pin 11) and GND (Pin 14) for the button's LED functionality. Here, a [GPIO Pin Map](https://www.bigmessowires.com/2018/05/26/raspberry-pi-gpio-programming-in-c/) can help with navigating.
1. Flash [Pi OS Legacy Lite](https://www.raspberrypi.com/software/) (the one that's based on Debian Bullseye) onto the microSD card (SSH enabled) and make the device connect to your WiFi.
2. Update/upgrade with `sudo apt-get update && sudo apt-get upgrade -y`
3. Install python3-pip via `sudo apt-get install python3-pip -y`
4. Install required applications for the display
```python
sudo apt install --upgrade python3-setuptools
sudo pip3 install adafruit-circuitpython-ssd1306
sudo apt-get install python3-pil
sudo apt-get install i2c-tools -y
```
5. Install required applications for shazam functionality
```python
sudo pip install shazamio
sudo apt-get install alsa-utils && sudo apt-get install libasound2-plugin-equal -y
sudo apt install ffmpeg -y
sudo apt-get install sox -y
```
6. Create necessary folders. You can choose to place these elsewhere and edit global settings within `shazampi.py` accordingly, but this is the default configuration:
```python
/var/shazampi
/var/shazampi/analysis_logs
/var/shazampi/old_recordings
/var/shazampi/old_recordings_posteq
/var/shazampi/new_recordings
/var/shazampi/new_recordings_posteq
```
7. Transfer the display font (`swift.ttf`) and my script (`shazampi.py`) into `/var/shazampi/`. I always use FileZilla SSH for this, but there are many ways to do this.
8. Edit access permissions for the shazampi folder and the system LED directory by entering:
```python
sudo chmod -R 777 /var/shazampi
sudo chmod -R 777 /sys/class/leds
```
9. Edit the global settings (like eMail configuration etc.) at the top of `shazampi.py` to your liking and save the file.
10. Adjust the microphone input signal by executing `sudo alsamixer` if you plan on using the device in a very high volume environment.
    - After executing the command, you can select your USB microphone from as dropdown menu by hitting F6 and then adjust the capture volume after hitting F5. I used a dB gain of 18, which delivered satisfactory results.
    - Restore your `alsamixer` configuration automatically after reboot. How this is done is described [here](https://dev.to/luisabianca/fix-alsactl-store-that-does-not-save-alsamixer-settings-130i).
11. Reduce power consumption of your device with these [Instructions](https://www.cnx-software.com/2021/12/09/raspberry-pi-zero-2-w-power-consumption/) in order to maximize your runtime on battery:
   - Disable HDMI input/output
   - Disable bluetooth
   - You can also throttle the CPU, but I personally think this is only necessary if you have hard battery constraints
12. Make `shazampi.py` execute on bootup. There are [many ways](https://www.dexterindustries.com/howto/run-a-program-on-your-raspberry-pi-at-startup/) to do this and one way can be achieved by creating a systemd service file:
   - Enter `sudo nano /etc/systemd/system/shazampi.service`.
   - Paste this:
     ```
     [Unit]
      Description=Shazampi Script
      After=network.target

      [Service]
      ExecStart=/usr/bin/python3 /var/shazampi/shazampi.py
      WorkingDirectory=/var/shazampi/
      StandardOutput=inherit
      StandardError=inherit
      Restart=always
      User=shazampi
      Environment=PYTHONUNBUFFERED=1

      [Install]
      WantedBy=multi-user.target```
   - Enable and start the service by executing
      ```
      sudo systemctl daemon-reload
      sudo systemctl enable shazampi.service
      sudo systemctl start shazampi.service
      ```
13. Reboot and verify. You're done.

