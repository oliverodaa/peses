import time
from datetime import datetime
import os
import RPi.GPIO as GPIO
import csv

# read SPI data from MCP3008 chip, 8 possible adc's (0 thru 7)
def readadc(adcnum, clockpin, mosipin, misopin, cspin):
    if ((adcnum > 7) or (adcnum < 0)):
            return -1
    GPIO.output(cspin, True)
    GPIO.output(clockpin, False)  # start clock low
    GPIO.output(cspin, False)     # bring CS low
    commandout = adcnum
    commandout |= 0x18  # start bit + single-ended bit
    commandout <<= 3    # we only need to send 5 bits here
    for i in range(5):
            if (commandout & 0x80):
                    GPIO.output(mosipin, True)
            else:
                    GPIO.output(mosipin, False)
            commandout <<= 1
            GPIO.output(clockpin, True)
            GPIO.output(clockpin, False)
    adcout = 0
    # read in one empty bit, one null bit and 10 ADC bits
    for i in range(12):
            GPIO.output(clockpin, True)
            GPIO.output(clockpin, False)
            adcout <<= 1
            if (GPIO.input(misopin)):
                    adcout |= 0x1
    GPIO.output(cspin, True)
    adcout >>= 1       # first bit is 'null' so drop it
    return adcout

def readadc_with_settings():
    # change these as desired - they're the pins connected from the
    # SPI port on the ADC to the pins on the Raspberry Pi
    SPICLK = 18
    SPIMISO = 23
    SPIMOSI = 24
    SPICS = 25
    # set up the SPI interface pins
    GPIO.setup(SPIMOSI, GPIO.OUT)
    GPIO.setup(SPIMISO, GPIO.IN)
    GPIO.setup(SPICLK, GPIO.OUT)
    GPIO.setup(SPICS, GPIO.OUT)
    # 10k trim pot connected to adc #0
    adcnum = 0
    return readadc(adcnum, SPICLK, SPIMOSI, SPIMISO, SPICS)

def run_until_threshold(TOLERANCE, SLEEP_TIME):
    """
    """
    last_read = 0 # nothing was read so initialize to 0
    change_threshold_met = False
    while not change_threshold_met:
        acc_read = readadc_with_settings() # read the analog pin
        change = abs(acc_read - last_read) # how much has it changed since the last read?
        if ( (not last_read == 0) and (not change_threshold_met) and change > TOLERANCE ):
            print("Change threshold met!")
            change_threshold_met = True
        time.sleep(SLEEP_TIME) # hang out and do nothing for x seconds
    return last_read

def record_data(NUM_MEASUREMENTS, SLEEP_TIME, SAVE_FILE_NAME):
    """
    Records data to save into <SAVE_FILE_NAME>.csv
    Starts recording after RUN_UNTIL_THRESHOLD() finishes executing
    """
    writer = csv.writer(open(SAVE_FILE_NAME, "w"))
    for i in range(NUM_MEASUREMENTS):
        acc_read = readadc_with_settings() # read the analog pin
    	writer.writerow([time.strftime("%H:%M:%S", time.gmtime()), acc_read])
        time.sleep(SLEEP_TIME) # hang out and do nothing for x seconds

def main():
    GPIO.setmode(GPIO.BCM)
    start_time = datetime.datetime.now()
    # ~~~~~~~ OPTIONS TO CONFIGURE ~~~~~~~~~
    num_measurements = 30000
    tolerance = 2
    sleep_time = 0.001
    save_file_name =  "saved_CSVs/"+"our_data.csv"
    # ~~~~~~~ ==================== ~~~~~~~~~
    run_until_threshold(tolerance, sleep_time)
    record_data(num_measurements, sleep_time, save_file_name)
    # ~~~~~~~   HELPFUL MESSAGES   ~~~~~~~~~
    print("Data Recording Complete!")
    print("  Num Measurements: "+str(num_measurements))
    print("        Time Taken: "+str(time_taken))
    print("          Saved To: "+save_file_name)
    print("         Tolerance: "+str(tolerance))

if __name__ == "__main__":
    main()
