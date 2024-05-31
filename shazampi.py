##################################
######## SHAZAMPI MACHINE ########
############# BY CK ##############
##################################

# --------------------------------
# --------Global settings---------
# Email data for shazam logs:
enable_email = "false"
email_origin = "asdfasdf@gmail.com"
email_password = "asdfasdf"
email_targets = ["asdfasdf@gmail.com", "qwerqwer@gmail.com"]
# File directories for new recordings, already analyzed recordings and log files:
newrec_path = "/var/shazampi/new_recordings/"
newrec_path_posteq = "/var/shazampi/new_recordings_posteq/"
oldrec_path_posteq = "/var/shazampi/old_recordings_posteq/"
log_path = "/var/shazampi/analysis_logs/"
# Recording preferences (length of recorded files in seconds and sampling rate in hz):
record_seconds = "16"
record_samplingrate = "96000"
record_format = "S32_LE"
extension = ".wav"
# Used GPIO pins for button and LED communication
BUTTON_PIN = 10
LED_PIN = 17
# --------------------------------

# Libraries and global variables for...
# ...internet connection check
import socket
# ...file identification/paths
import os, os.path
import fnmatch
# ...self-restart functionality
import sys
# ...time (logging & timestamps for files)
import time
import datetime
# ...shazam functionality
import asyncio
from shazamio import Shazam
# ...email reporting
import smtplib
import glob
# ...recording functionality
import subprocess
import re
# ...button functionality
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT)

# Switch off LED
GPIO.output(LED_PIN, GPIO.LOW)

# Check internet connection for two seconds
def is_internet_connected():
    try:
        socket.create_connection((socket.gethostbyname("www.google.com"), 80), 2)
        return True
    except OSError:
        pass
    return False

# Get device number of the USB microphone
def get_microphone_device():
    try:
        result = subprocess.run(['arecord', '-l'], capture_output=True, text=True)
        output = result.stdout

        # Look for the "USB Microphone" entry
        matches = re.findall(r'card (\d+): (.*)\[(.*)\], device (\d+):', output)
        for match in matches:
            card, name, long_name, device = match
            if 'USB Microphone' in long_name:
                return f"plughw:{card},{device}"
    except Exception as e:
        print(f"Error while looking for microphone: {e}")
    return None

# Make the button LED blink
async def blink_led(duration, interval):
    try:
        while True:
            GPIO.output(LED_PIN, GPIO.HIGH)
            await asyncio.sleep(duration)
            GPIO.output(LED_PIN, GPIO.LOW)
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        GPIO.output(LED_PIN, GPIO.LOW)

# Record and equalize audio
def record_and_process_audio(device):
    if not device:
        print("No microphone found.")
        return
    
    # LED einschalten
    GPIO.output(LED_PIN, GPIO.HIGH)
    print("LED has been switched on.")
    
    # Reset counters
    newrec_file_counter = 0
    
    # Iterate through files with audio extension in 'new_recordings' directory, count them, and set filename for new recording file + define in-/output variables
    for files in os.listdir(newrec_path):
        if files.endswith(extension):
            newrec_file_counter += 1     
    recoutput_filename = "track_" + str(newrec_file_counter + 1) + extension
    input_wav = newrec_path + recoutput_filename
    output_wav = newrec_path_posteq + recoutput_filename

    # Record audio  
    record_command = ["arecord", "-D", device, "-d", record_seconds, "-f", record_format, "-r", record_samplingrate, input_wav]
    subprocess.run(record_command)
    print(f"Recording has been saved to {newrec_path}.")
    
    # Reduce bass from the source file with sox
    sox_command = ["sox", input_wav, output_wav, "bass", "-24", "100"]
    subprocess.run(sox_command)
    print(f"Recording has been equalized and saved to {newrec_path_posteq}.")
    
    # Switch off LED
    GPIO.output(LED_PIN, GPIO.LOW)
    print("LED has been switched off.")
    
async def analyze_and_email():
    # Start LED blinking
    blink_task = asyncio.create_task(blink_led(duration=0.2, interval=0.2))
    
    # Load shazam and reset counters
    shazam = Shazam()
    newrec_file_counter = 0
    current_id_counter = 0
    current_success_counter = 0
    
    # Delete all files in 'new_recordings'
    for files in os.listdir(newrec_path):
        del_filepath = os.path.join(newrec_path, files)
        if os.path.isfile(del_filepath):
            os.remove(del_filepath)
    
    # Iterate through files with audio extension in 'new_recordings_posteq' directory, count, and print the result
    for files in os.listdir(newrec_path_posteq):
        if files.endswith(extension):
            newrec_file_counter += 1

    if newrec_file_counter >= 2:
        print("Analyzing " + str(newrec_file_counter) + " Tracks. Be patient.")
    elif newrec_file_counter == 1:
        print("Analyzing " + str(newrec_file_counter) + " Track.")
    else:
        print("There are no files to be analyzed.")
        # Stop LED blinking
        blink_task.cancel()
        try:
            await blink_task
        except asyncio.CancelledError:
            pass
        return
        
    # Get current time
    current_date = datetime.datetime.now().strftime("%d.%m.%Y")
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    current_timestamp = current_date + ", " + current_time
    
    # Create log file
    file = open(log_path + "logfile [" + current_timestamp + "].txt", "w")
    file.write("SHAZAM ANALYSIS LOG\n\nDate: " + current_date + "\nTime: " + current_time + "\n\n\n")
    
    # Iterate through files with audio extension in 'new_recordings_posteq' directory for shazam analysis
    for files in os.listdir(newrec_path_posteq):
        if files.endswith(extension):
            # Count attempts
            current_id_counter += 1
            # Update current timestamp
            current_timestamp_with_ms = datetime.datetime.now().strftime("%d.%m.%Y") + ", " + datetime.datetime.now().strftime("%H:%M:%S.%f")[:-5]
            # Get shazam data
            alldata = await shazam.recognize(newrec_path_posteq + files)
            # Check if song has been identified
            if 'track' in alldata:
                # Get artist and track data
                trackdata = alldata['track']
                trackid = trackdata['subtitle'] + " - " + trackdata['title']
                # Move file from 'new_recordings_posteq' to 'old_recordings_posteq' directory and rename to Track ID
                os.replace(newrec_path_posteq + files, oldrec_path_posteq + trackid + " [Analyzed " + current_timestamp_with_ms + "]" + extension)
                # Count your successes
                current_success_counter += 1
                # Write to log file and print current analysis status
                file.write("Track " + str(current_id_counter) + "/" + str(newrec_file_counter) + ": " + trackid + "\n")
                print("Track " + str(current_id_counter) + "/" + str(newrec_file_counter) + " found: " + trackid)
            else:
                # Move file from 'new_recordings_posteq' to 'old_recordings_posteq' directory and rename to "Unidentified"
                os.replace(newrec_path_posteq + files, oldrec_path_posteq + "Unidentified Track [Analyzed " + current_timestamp_with_ms + "]" + extension)
                # Write to log file and print current analysis status
                file.write("Track " + str(current_id_counter) + "/" + str(newrec_file_counter) + ": Not found. \n")
                print("Track " + str(current_id_counter) + "/" + str(newrec_file_counter) + " not found.")
        else:
            continue
        
    # Write final status report to file and close it
    if current_id_counter >= 2:
        file.write("\n\nAnalysis Summary: " + str(current_success_counter) + " of " + str(current_id_counter) + " Tracks have been identified.")
        print("Analysis Summary: " + str(current_success_counter) + " of " + str(current_id_counter) + " Tracks have been identified.")
    else:
        file.write("\n\nAnalysis Summary: One Track has been identified.")
        print("Analysis Summary: One Track has been identified.")
    file.close()
    print(f"Log file has been saved to {log_path}.")
    
    # Send analysis log via email
    if enable_email == "true":
        # Get the textual content of the newest log file and paste it into a variable
        time.sleep(0.5)
        logfiles = list(filter(os.path.isfile, glob.glob(log_path + "*")))
        logfiles.sort(key=lambda x: os.path.getmtime(x))
        newest_logfile_path = logfiles[-1]
        with open(newest_logfile_path, "r") as file:
            filecontent = file.read()
            
        # Send the contents of the newly filled variable by email using a gmail account
        subject = "Shazam Analyse vom " + current_date + " um " + current_time
        service = smtplib.SMTP('smtp.gmail.com', 587)
        service.starttls()
        service.login(email_origin, email_password)
        service.sendmail(email_origin, email_targets, f"Subject: {subject}\n{filecontent}")
        service.quit
        print("Log file has been sent to " + email_targets + ".")
    else:
        print("Log file has not been sent via eMail.")
    
    # Stop LED blinking
    blink_task.cancel()
    try:
        await blink_task
    except asyncio.CancelledError:
        pass

async def main():
    try:
        print("Button is ready.")
        while True:
            button_state = GPIO.input(BUTTON_PIN)
            if button_state == GPIO.LOW:
                print("Button has been pressed.")
                if is_internet_connected():
                    print("Connected to the internet.")
                    await analyze_and_email()
                else:
                    print("Not connected to the internet.")
                    device = get_microphone_device()
                    record_and_process_audio(device)
                print("Button is ready.")
                # Prohibit button-mashing
                time.sleep(1)
            # Reduce CPU load
            time.sleep(0.1)  
    except KeyboardInterrupt:
        print("Program aborted.")
    finally:
        GPIO.cleanup()

# Start the async main function
if __name__ == "__main__":
    asyncio.run(main())
