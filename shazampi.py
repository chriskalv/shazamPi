##################################
######## SHAZAMPI MACHINE ########
############# BY CK ##############
##################################

# GLOBAL SETTINGS
# --> EMAIL
EMAIL_ENABLED = False
EMAIL_ORIGIN = "asdfasdf@gmail.com"
EMAIL_PASSWORD = "asdfasdf"
EMAIL_TARGETS = ["asdfasdf@gmail.com", "qwerqwer@gmail.com"]
# --> DIRECTORIES
NEWREC_PATH = "/var/shazampi/new_recordings/"
NEWREC_PATH_POSTEQ = "/var/shazampi/new_recordings_posteq/"
OLDREC_PATH = "/var/shazampi/old_recordings/"
OLDREC_PATH_POSTEQ = "/var/shazampi/old_recordings_posteq/"
LOG_PATH = "/var/shazampi/analysis_logs/"
FONT_PATH = "/var/shazampi/swift.ttf"
# --> RECORDING PARAMETERS (check linux.die.net/man/1/sox for syntax)
RECORD_SECONDS = 16
RECORD_SAMPLING_RATE = 96000
RECORD_FORMAT = "S32_LE"
EXTENSION = ".wav"
# --> GPIO PINS
BUTTON_PIN = 10
LED_PIN = 17
# --> ONBOARD LED PATH (check /sys/class/leds/ and see if the folder for your ACT LED is named ACT, led0, led1 or act_led)
LED_PATH = "/sys/class/leds/ACT"

# Libraries
import os
import socket
import sys
import time
import datetime
import asyncio
import subprocess
import re
import smtplib
import glob
from shazamio import Shazam
from RPi import GPIO
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
from board import SCL, SDA

# Handle button and LED
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, GPIO.LOW)

# Create the I2C interface and OLED display
i2c = busio.I2C(SCL, SDA)
disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)
disp.fill(0)
disp.show()
disp.contrast(0)

width, height = disp.width, disp.height
image = Image.new("1", (width, height))
draw = ImageDraw.Draw(image)

def update_display(line1="", line2="", line3="", line4="", line5=""):
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((0, -5), line1, font=ImageFont.truetype(FONT_PATH, 9), fill=255)
    draw.text((0, 11), line2, font=ImageFont.truetype(FONT_PATH, 8), fill=255)
    draw.text((0, 21), line3, font=ImageFont.truetype(FONT_PATH, 8), fill=255)
    draw.text((3, -14), line4, font=ImageFont.truetype(FONT_PATH, 33), fill=255)
    draw.text((-1, 0), line5, font=ImageFont.truetype(FONT_PATH, 17), fill=255)
    disp.image(image)
    disp.show()

def is_internet_connected():
    try:
        socket.create_connection((socket.gethostbyname("www.google.com"), 80), 2)
        return True
    except OSError:
        return False
    
def get_ip_address():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(('10.254.254.254', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = 'No IP'
    finally:
        s.close()
    return IP

def get_device_name():
    return socket.gethostname()

def get_microphone_device():
    try:
        result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
        output = result.stdout
        matches = re.findall(r'card (\d+): (.*)\[(.*)\], device (\d+):', output)
        for match in matches:
            card, name, long_name, device = match
            if 'USB Microphone' in long_name:
                return f"plughw:{card},{device}"
    except Exception as e:
        print(f"Error while looking for microphone: {e}")
    return None

async def blink_led(frequency=1):
    try:
        while True:
            with open(os.path.join(LED_PATH, "brightness"), "w") as led:
                led.write("1")
            await asyncio.sleep(frequency)
            with open(os.path.join(LED_PATH, "brightness"), "w") as led:
                led.write("0")
            await asyncio.sleep(frequency)
    except KeyboardInterrupt:
        with open(os.path.join(LED_PATH, "trigger"), "w") as led:
            led.write("mmc0")
            
def restart_script():
    print("Restarting script...")
    os.execv(sys.executable, ['python3'] + sys.argv)

def record_and_process_audio(device):
    if not device:
        print("No microphone found.")
        return

    GPIO.output(LED_PIN, GPIO.HIGH)
    newrec_file_counter = len([f for f in os.listdir(NEWREC_PATH) if f.endswith(EXTENSION)])
    recoutput_filename = f"track_{newrec_file_counter + 1}{EXTENSION}"
    input_wav = os.path.join(NEWREC_PATH, recoutput_filename)
    output_wav = os.path.join(NEWREC_PATH_POSTEQ, recoutput_filename)

    record_command = ["arecord", "-D", device, "-d", str(RECORD_SECONDS), "-f", RECORD_FORMAT, "-r", str(RECORD_SAMPLING_RATE), input_wav]
    subprocess.run(record_command)
    print(f"Recording has been saved to {NEWREC_PATH}.")

    sox_command = ["sox", input_wav, output_wav, "bass", "-24", "100"]
    subprocess.run(sox_command)
    print(f"Recording has been equalized and saved to {NEWREC_PATH_POSTEQ}.")

    GPIO.output(LED_PIN, GPIO.LOW)

def extract_track_number(filename):
    match = re.search(r'track_(\d+)', filename)
    return int(match.group(1)) if match else float('inf')

async def analyze_and_email():
    GPIO.output(LED_PIN, GPIO.HIGH)
    shazam = Shazam()
    files_to_analyze = sorted([f for f in os.listdir(NEWREC_PATH_POSTEQ) if f.endswith(EXTENSION)], key=extract_track_number)
    newrec_file_counter = len(files_to_analyze)

    if newrec_file_counter == 0:
        print("There are no files to be analyzed.")
        GPIO.output(LED_PIN, GPIO.LOW)
        return

    print(f"Analyzing {newrec_file_counter} Track{'s' if newrec_file_counter > 1 else ''}. Be patient.")
    current_date = datetime.datetime.now().strftime("%d.%m.%Y")
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    current_timestamp = f"{current_date}, {current_time}"

    log_file_path = os.path.join(LOG_PATH, f"logfile [{current_timestamp}].txt")
    with open(log_file_path, "w") as file:
        file.write(f"SHAZAM ANALYSIS LOG\n\nDate: {current_date}\nTime: {current_time}\n\n\n")

        current_id_counter = 0
        current_success_counter = 0

        for filename in files_to_analyze:
            current_id_counter += 1
            creation_time = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(NEWREC_PATH_POSTEQ, filename))).strftime("%d.%m.%Y, %H:%M")
            alldata = await shazam.recognize(os.path.join(NEWREC_PATH_POSTEQ, filename))

            if 'track' in alldata:
                trackdata = alldata['track']
                trackid = f"{trackdata['subtitle']} - {trackdata['title']}"
                os.replace(os.path.join(NEWREC_PATH_POSTEQ, filename), os.path.join(OLDREC_PATH_POSTEQ, f"{trackid} [Analyzed {creation_time}]{EXTENSION}"))
                os.replace(os.path.join(NEWREC_PATH, filename), os.path.join(OLDREC_PATH, f"{trackid} [Analyzed {creation_time}]{EXTENSION}"))
                current_success_counter += 1
                file.write(f"Track {current_id_counter} [{creation_time} - {filename}] has been tagged: \n{trackid}\n\n")
                print(f"Track {current_id_counter} of {newrec_file_counter} analyzed: \n{trackid}\n")
            else:
                os.replace(os.path.join(NEWREC_PATH_POSTEQ, filename), os.path.join(OLDREC_PATH_POSTEQ, f"{filename} [unidentified]"))
                os.replace(os.path.join(NEWREC_PATH, filename), os.path.join(OLDREC_PATH, f"{filename} [unidentified]"))
                file.write(f"Track {current_id_counter} [{creation_time} - {filename}] could not be identified.\n\n")
                print(f"Track {current_id_counter} of {newrec_file_counter} could not be identified.\n")
                
                    
        file.write(f"\n\nThe analysis has been completed.\n\n{current_success_counter} of {newrec_file_counter} tracks have been identified.")
        print(f"The analysis has been completed.\n\n{current_success_counter} of {newrec_file_counter} tracks have been identified.")

    if EMAIL_ENABLED:
        await asyncio.sleep(0.5)
        logfiles = sorted(glob.glob(os.path.join(LOG_PATH, "*")), key=os.path.getmtime)
        newest_logfile_path = logfiles[-1]

        with open(newest_logfile_path, "r") as file:
            filecontent = file.read()

        subject = f"Shazam Analysis from {current_date} at {current_time}"
        service = smtplib.SMTP('smtp.gmail.com', 587)
        service.starttls()
        service.login(EMAIL_ORIGIN, EMAIL_PASSWORD)
        message = f"Subject: {subject}\n\n{filecontent}"
        service.sendmail(EMAIL_ORIGIN, EMAIL_TARGETS, message)
        service.quit()
        print(f"Log file has been sent to {EMAIL_TARGETS}.")

    GPIO.output(LED_PIN, GPIO.LOW)
    restart_script()

async def main():
    led_task = asyncio.create_task(blink_led())
    
    if is_internet_connected():
        ip_address = get_ip_address()
        device_name = get_device_name()
        files_number = len([f for f in os.listdir(NEWREC_PATH_POSTEQ) if os.path.isfile(os.path.join(NEWREC_PATH_POSTEQ, f))])
        trackspelling = "TRACKS" if files_number != 1 else "TRACK"
        smiley = ":)" if files_number > 0 else ":("
        update_display(line1=f"{files_number if files_number > 0 else 'NO'} NEW {trackspelling} {smiley}", line2=f"IP: {ip_address}", line3=f"Name: {device_name}")
    else:
        update_display(line4="PUSH!")

    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            if is_internet_connected():
                if files_number < 1:
                    update_display(line1="NOTHING TO TAG!", line2=f"IP: {ip_address}", line3=f"Name: {device_name}")
                    await asyncio.sleep(5)
                    restart_script()
                else:
                    update_display(line5="TAGGING!")
                    await analyze_and_email()
                    restart_script()
            else:
                update_display(line5="RECORDING!")
                device = get_microphone_device()
                record_and_process_audio(device)
                update_display(line4="PUSH!")
        await asyncio.sleep(0.1)

if __name__ == "__main__":
    asyncio.run(main())
