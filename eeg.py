'''
Tools for working with EEG, photocell and markers streams.

Includes tools to read streams from encephalograph, photocell
and markers in EEG class. 

'''

import logging
import multiprocessing
from pylsl import StreamInlet, resolve_byprop, resolve_stream
from CONSTANTS import *
import time, os 

class EEG:
    '''Tools for working with EEG and photocell.

    A class that contains functions to read streams from EEG and
    photocell.

    '''

    def __init__(self, queue):
        '''Initiate EEG class.
        
        Keyword arguments:
        queue -- Queue object to put data in and get it (used to
                 send and detect the end mark to stop all processes)
        
        '''
        self.queue = queue

    def create_inlet(self, stream_type):
        '''Create inlet to read a stream.
        
        Keyword arguments:
        stream_type -- name of a stream to read (see CONSTANTS)
        
        Variables:
        streams -- all streams in the environment corresponds to demand
        
        Returns:
        inlet -- StreamInlet object to listen to particular stream

        '''
        streams = resolve_byprop('name', stream_type)
        inlet = StreamInlet(streams[0])
        return inlet 
    
    def write_data(self, filename, inlet):
        '''Read data from stream and write it to file.
        
        Keyword arguments:
        filename -- string with path and name of file to write
        inlet -- StreamInlet object derived from create_inlet function
        
        Variables:
        sample -- sample of data obtained from the stream
        timestamp -- timecode in Unix Time format (seconds since epoch)

        '''
        with open(filename, 'w') as f:
            name = multiprocessing.current_process().name
            while self.queue.empty(): 
                sample, timestamp = inlet.pull_sample(timeout=5)
                if sample != None:
                    f.write('{}: {} {}\n'.format(name, timestamp, sample))
                             
    def eeg_process(self, filename=''):
        '''Working with EEG.'''
        
        logging.info('looking for an EEG stream...')
        inlet = self.create_inlet(EEG_STREAM)
        self.write_data(r'F:\\Timofey\\test_write_eeg.txt', inlet)
        print('eeg process ended')
       
    def marker_process(self, filename=''):
        '''Working with visual process marker stream.'''

        logging.info('looking for a marker stream')
        inlet = self.create_inlet(VISUAL_STREAM_NAME)
        self.write_data(r'F:\\Timofey\\test_write_marker.txt', inlet)
        print('marker process ended')
        
    def photocell_process(self, filename=''):
        '''Working with photocell.'''

        logging.info('looking for a photosensor stream...')
        inlet = self.create_inlet(PHOTOSENSOR_STREAM)
        self.write_data(r'F:\\Timofey\\test_write_photocell.txt', inlet)
        print('photocell process ended')

if __name__ == '__main__':
    # test timing
    streams = resolve_byprop('name', EEG_STREAM)
    inlet = StreamInlet(streams[0])
    with open(r'F:\\Timofey\\test_write_eeg_timing.txt', 'w') as f:
        t1 = float(time.time())
        data = []
        while (float(time.time())-t1) <= 2: 
            # sample, timestamp = inlet.pull_chunk()
            sample, timestamp = inlet.pull_sample()
            if timestamp:
                f.write('{} {}\n'.format(timestamp, sample))
                data.append(timestamp)
        print(len(data))

            

