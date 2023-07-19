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

class Record:
    '''Tools for working with EEG, photocell and marker streams.

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

    def create_inlet(self, stream_type, repeat=3):
        '''Create inlet to read a stream.

        Creates inlet to recieve data from a stream. Tries to reconnect
        n times and print an error if cannot find the stream.
        
        Keyword arguments:
        stream_type -- name of a stream to read (see CONSTANTS)
        
        Variables:
        streams -- all streams in the environment corresponds to demand
        
        Returns:
        inlet -- StreamInlet object to listen to particular stream

        '''
        if repeat==0:
            logging.error('Cannot find stream: {}'.format(stream_type))
            raise(RuntimeError('Cannot find stream: {}'.format(stream_type)))

        streams = resolve_byprop('name', stream_type, timeout=1)

        if streams:
            inlet = StreamInlet(streams[0])
            self.inlet = inlet
            logging.info('{} found'.format(stream_type))
            return
        else:
            self.create_inlet(stream_type, repeat-1)
    
    def write_data(self, filename):
        '''Read data from stream and write it to file.
        
        Keyword arguments:
        filename -- string with path and name of file to write
        inlet -- StreamInlet object derived from create_inlet function
        
        Variables:
        sample -- sample of data obtained from the stream
        timestamp -- timecode in Unix Time format (seconds since epoch)
        path -- directory of particular filecode FILEPATH/FILECODE

        '''
        # Check for directory, create if it doesn`t exist
        path = os.path.join(FILEPATH, FILECODE)
        if not os.path.exists(path):
            os.mkdir(path)
        
        # To avoid rewriting data    
        if os.path.exists(filename):
            filename = filename.split('.txt')[0]+'1'+'.txt'

        # Record data    
        
        with open(filename, 'w') as f:
            while self.queue.empty():
                sample, timestamp = self.inlet.pull_sample(timeout=5)
                if sample!=None:
                    f.write(','.join(map(str, [timestamp]+sample))+'\n')
        
        '''
        Better writing approach, just like simple csv: timestamp,Fp1,Fp2...
        Creates one list from timestamp and samples, then turns it to a string
        and write to the file with comma separator. Much easier to read with pandas,
        makes possible to avoid parsing.

        old:
        with open(filename, 'w') as f:
            while self.queue.empty():     
                sample, timestamp = inlet.pull_sample(timeout=5)
                if sample != None:
                    f.write('{} {}\n'.format(timestamp, sample))
        
        new:
        with open('filename', 'w') as f:
            while self.queue.empty():
                sample, timestamp = inlet.pull_sample(timeout=5)
                f.write(','.join(map(str, [timestamp]+sample))+'\n')
        '''
    
    def eeg_process(self, filename=''):
        '''Working with EEG.'''
        
        logging.info('looking for an EEG stream...')
        self.create_inlet(EEG_STREAM)
        self.write_data(os.path.join(FILEPATH, FILECODE, FILECODE+'_eeg.txt'))
        logging.info('eeg process ended')
       
    def marker_process(self, filename=''):
        '''Working with visual process marker stream.'''

        logging.info('looking for a marker stream')
        self.create_inlet(VISUAL_STREAM)
        self.write_data(os.path.join(FILEPATH, FILECODE, FILECODE+'_marker.txt'))
        logging.info('marker process ended')
        
    def photocell_process(self, filename=''):
        '''Working with photocell.'''

        logging.info('looking for a photosensor stream...')
        self.create_inlet(PHOTOSENSOR_STREAM)
        self.write_data(os.path.join(FILEPATH, FILECODE, FILECODE+'_photocell.txt'))
        logging.info('photocell process ended')

if __name__ == '__main__':
    # For testing stuff
   a=Record(None)
   a.create_inlet(PHOTOSENSOR_STREAM)

            

