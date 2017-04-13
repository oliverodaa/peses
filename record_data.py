import time
from datetime import datetime
import os
import csv
import random
import argparse
import RPi.GPIO as GPIO

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

CURRENT_ROW = 0

def read_from_csv(fname):
    global CURRENT_ROW
    with open(fname, 'rb') as csvfile:
        CURRENT_ROW = CURRENT_ROW + 1
        if (CURRENT_ROW % 100 == 0):
            print("now reading: "+str(CURRENT_ROW))
        return float(list(csv.reader(csvfile, delimiter=' ', quotechar='|'))[CURRENT_ROW-1][0].split(",")[1])

def readadc_with_settings():
    # change these as desired - they're the pins connected from the
    # SPI port on the ADC to the pins on the Raspberry Pi
    SPICLK = 18
    SPIMISO = 23
    SPIMOSI = 24
    SPICS = 25
    # # set up the SPI interface pins
    GPIO.setup(SPIMOSI, GPIO.OUT)
    GPIO.setup(SPIMISO, GPIO.IN)
    GPIO.setup(SPICLK, GPIO.OUT)
    GPIO.setup(SPICS, GPIO.OUT)
    # # 10k trim pot connected to adc #0
    adcnum = 0
    return readadc(adcnum, SPICLK, SPIMOSI, SPIMISO, SPICS)

# ~~~~~~~ Time Helpers ~~~~~~~~~~~~~

def time_until_now(start_time):
    return (datetime.now() - start_time).total_seconds()

def timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")

# ~~~~~~~ Helpers related to the buffer ~~~~~~~~~~~~~
# Buffer works as follows:
#   - It's a 2 item array where
#       - Item 0 is an array of fixed length (say, 100 items)
#       - Item 1 is a number representing the index where we last pushed.

def create_buffer(size):
    return [[None]*size, 0]

def add_to_buffer(my_buffer, item):
    my_list, buf_index = my_buffer
    my_buffer[0][buf_index] = item
    my_buffer[1] = (buf_index+1)%len(my_list)
    return my_buffer

def read_from_buffer(my_buffer, item_index):
    my_list, buf_index = my_buffer
    return my_list[ (buf_index+item_index)%len(my_list) ]

def save_buf_to_file(my_buffer, SAVE_FILE_NAME):
    """
    Assumes that each element of the enclosed array is
    already in the form (timestamp, value).
    Not necessary for the data structure in general.
    """
    writer = csv.writer(open(SAVE_FILE_NAME, "w")) # overwrite the whole file
    for i in range(len(my_buffer[0])): # Go through length of whole buffer
        buffer_item = read_from_buffer(my_buffer, i)
        if buffer_item is not None:
            writer.writerow(buffer_item)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def establish_mean(num_samples):
    total = 0.0
    for i in range(num_samples):
        total += readadc_with_settings()
    return total / float(num_samples)

def run_until_threshold(NUM_BEFORE, TOLERANCE, SLEEP_TIME, MEAN):
    """
    Runs until we have a difference from the mean of more than TOLERANCE
    """
    change_threshold_met = False
    buffer_before_threshold = create_buffer(NUM_BEFORE)
    while not change_threshold_met:
        acc_read = readadc_with_settings() # read the analog pin
        buffer_before_threshold = add_to_buffer(buffer_before_threshold, [timestamp(), acc_read - MEAN])
        change = abs(acc_read - MEAN) # how different is it from the mean?
        if (change > TOLERANCE):
            print("Change threshold met!")
            change_threshold_met = True
        time.sleep(SLEEP_TIME) # hang out and do nothing for x seconds
    return buffer_before_threshold

def record_data(NUM_MEASUREMENTS, TOLERANCE, END_TOLERANCE, SLEEP_TIME, SAVE_FILE_NAME, MAX_TIME, MEAN):
    """
    Records data to save into <SAVE_FILE_NAME>.csv
    Starts recording after RUN_UNTIL_THRESHOLD() finishes executing
    Stops recording after 100 measurements in a row change less than END_TOLERANCE.
    """
    start_time = datetime.now()
    last_read = readadc_with_settings() # initial reading
    writer = csv.writer(open(SAVE_FILE_NAME, "a"))
    num_without_change = 0
    i = 0
    while (i < NUM_MEASUREMENTS) and (time_until_now(start_time) < MAX_TIME):
        acc_read = readadc_with_settings() # read the analog pin
    	writer.writerow([timestamp(), acc_read - MEAN])
        change = abs(acc_read - last_read)
        if (change < TOLERANCE):
            num_without_change += 1
        else:
            num_without_change = 0
        last_read = acc_read
        i += 1
        if (num_without_change > END_TOLERANCE):
            print("End threshold met at: "+str(i)+" measurements!")
            break
        time.sleep(SLEEP_TIME) # hang out and do nothing for x seconds
    return (time_until_now(start_time), i)


def main():
    GPIO.setmode(GPIO.BCM)
    # ~~~~~~~ OPTIONS TO CONFIGURE ~~~~~~~~~
    num_before_threshold = 20
    tolerance = 5
    end_tolerance = 5
    sleep_time = 0.001
    save_file_name =  "saved_CSVs/our_data.csv"
    max_time = float("inf")
    num_measurements = float("inf")
    # ~~~~~~~ ==================== ~~~~~~~~~
    parser = argparse.ArgumentParser(description='Records data from an ADC')
    parser.add_argument('-b','--before', help='Number of samples that will be saved from just before we hit the threshold.', required=False)
    parser.add_argument('-n','--num', help='Number of samples that will be saved. Defaults to infinity.', required=False)
    parser.add_argument('-t','--tolerance', help='The amount that the table needs to shake before recording will start.', required=False)
    parser.add_argument('-s','--sleeptime', help='How much to sleep in between measurements.', required=False)
    parser.add_argument('-f','--filename', help='Filename to save to. Looks like "saved_CSVs/<FILENAME>.csv"', required=False)
    parser.add_argument('-m','--maxtime', help='Upper limit on the recording time. Starts *after* you hit threshold. Default time infinity.', required=False)
    parser.add_argument('-e','--endtolerance', help='Stops recording after ENDTOLERANCE measurements in a row change less than TOLERANCE.', required=False)
    args = vars(parser.parse_args())
    if args['before']:
        num_before_threshold = int(args['before'])
    if args['num']:
        num_measurements = int(args['num'])
    if args['tolerance']:
        tolerance = float(args['tolerance'])
    if args['sleeptime']:
        sleep_time = float(args['sleeptime'])
    if args['filename']:
        save_file_name =  "saved_CSVs/"+args['filename']+".csv"
    if args['maxtime']:
        max_time = float(args['maxtime'])
    if args['endtolerance']:
        end_tolerance = float(args['endtolerance'])
    # ~~~~~~~ ==================== ~~~~~~~~~
    mean = establish_mean(100)
    # Run until earthquake detected
    buffer_before_threshold = run_until_threshold(num_before_threshold, tolerance, sleep_time, mean)
    save_buf_to_file(buffer_before_threshold, save_file_name)
    # Runs from start of earthquake until end as defined by end_tolerance
    time_taken, actual_num_measurements = record_data(num_measurements, tolerance, end_tolerance, sleep_time, save_file_name, max_time, mean)
    # ~~~~~~~   HELPFUL MESSAGES   ~~~~~~~~~
    print("\nData Recording Complete.")
    print("  Num Measurements: "+str(actual_num_measurements))
    print("  Time Taken      : "+str(time_taken)+" seconds")
    print("  Measures/second : "+str(actual_num_measurements/time_taken))
    print("  Saved To        : "+save_file_name)
    print("  Tolerance       : "+str(tolerance))
    print("  EndTolerance    : "+str(end_tolerance))

if __name__ == "__main__":
    main()
