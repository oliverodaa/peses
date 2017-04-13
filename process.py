"""
Filters data
Processes filtered data
Send final displacements website
"""
# works except for conversion of timestamps to floats

import csv
import winsound
from scipy.signal import butter, lfilter
from scipy.fftpack import fft
import argparse

def readcsv(DATA_FILENAME):
	# read a data file
	with open(DATA_FILENAME,'r') as mycsvfile:
		data = csv.reader(mycsvfile)
		x = []; timestamp = []
		for row in data:
			x.append(float(row[1]))
			timestamp.append(float(row[0]))
	return x, timestamp

def writecsv(RESULTS_FILENAME,results):
	# save results
	with open(RESULTS_FILENAME,'w') as file:
		writer = csv.writer(file,lineterminator='\n')
		for row in results:
			writer.writerow(row)
	print ('saved results to: ' + RESULTS_FILENAME)
	return

def butter_filter(data):
	# uses butterworth (low/high pass) filter to filter data
	def butter_bandpass(lowcut, highcut, fs, order):
		nyq = 0.5*fs
		low = lowcut/nyq;
		high = highcut/nyq;
		b,a = butter(order, [low,high], btype='bandpass')
		DC = b[0]/a[0]
		return b,a,DC

	def butter_bandpass_filter(data, lowcut, highcut, fs, order,butter_bandpass):
		b,a,DC = butter_bandpass(lowcut, highcut, fs, order)
		y_f = lfilter (b, a, data)
		y = y_f#*(1/DC) # Account for DC Gain [We currently do not do this-->cheating]
		return (y)

	# filter
	l = len(data) # number of data points
	fs = l / (data[-1] - data[0]) # sampling rate
	print (data[0], data[-1])
	print ('sampling rate (HZ):', fs)
	x_fft = fft(data)
	T = np.linspace(0.0, fs/2, l/2)
	x_FFT_1 = 2.0/l * np.abs(x_fft[0:(l/2)])
	ind = [i for i,v in enumerate(x_FFT_1) if v == max(x_FFT_1)]
	Tb = T[ind]
	print ('Tb', Tb)
	filtered_data = butter_bandpass_filter(data, .3*Tb, 8*Tb, fs, 2, butter_bandpass) # filtered values
	return (filtered_data)

def integrate(data,timestamps):
	# integrate data
	int_data = []; int_data.appaned(0)
	for i in range(1,len(data)):
		delta = timestamps[i] - timestamps[i-1]
		int_data.append((delta/2)*(data[i-1]+data[i])+int_data[i-1])
	return (int_data)

def post(ENDPOINT, data):
	# send final results to website
	return (0)

def main():
	# ~~~~~~~ OPTIONS TO CONFIGURE ~~~~~~~~~
	endpoint = '' # web address for posting
	data_filename = 'test_data.csv' # data file
	results_filename = 'results.csv' # file for displacement results
	# ~~~~~~~ ==================== ~~~~~~~~~
	parser = argparse.ArgumentParser(description='Processes Data')
	parser.add_argument('-e','--endpoint', help='web address for posting', required=False)
	parser.add_argument('-df','--data_filename', help='file with raw data', required=False)
	parser.add_argument('-rf','--results_filename', help='file for results', required=False)
	args = vars(parser.parse_args())
	if args['endpoint']:
		endpoint = str(args['endpoint'])
	if args['data_filename']:
		endpoint = str(args['data_filename'])
	if args['results_filename']:
		endpoint = str(args['results_filename'])
	# ~~~~~~~ ==================== ~~~~~~~~~
	a, timestamp = readcsv(data_filename) # read data csv
	af = butter_filter(a)
	v = integrate(af,timestamps)
	vf = butter_filter(v)
	d = integrate(vf,timestamps)
	writecsv(results_filename,d)

	print ('final displacement', d[-1])
	return

if __name__ == "__main__":
	main()