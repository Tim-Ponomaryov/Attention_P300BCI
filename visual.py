#NOTE: worse image resolution -> faster blinking; impossible to take unicode emoji instead images
#NOTE: color changes for que and choice replaced by flashing
#TODO: association of a stimulus and it's position / flash group

import multiprocessing
import logging
import time
import numpy as np
import random
# import psychopy.visual
from psychopy.monitors import Monitor
from psychopy.visual import Window
from psychopy.visual.circle import Circle
from psychopy.visual.rect import Rect
from psychopy.visual import TextStim, TextBox2, ImageStim
# from psychopy.visual import ImageStim # probably not needed anymore
from psychopy.event import Mouse, waitKeys, getKeys, clearEvents
from psychopy.core import wait
from pylsl import StreamInfo, StreamOutlet
from CONSTANTS import *



def merge_two_dicts(x, y):
    '''Merge two dictionaries in one.'''
    
    z = x.copy()   # start with keys and values of x
    z.update(y)    # modifies z with keys and values of y
    return z

class MyTextStim(TextStim):
    '''Extention of PsychoPy TextStim class.'''
    
    def __init__(self, display, index, text='', pos=None, units='deg',
                 height=None, opacity=0.5, show=True, stim_class=''):
        super().__init__(display, text=text, pos=pos, units=units,
                         height=height, opacity=opacity)
        self.index = index
        self.show = show
        self.stim_class = stim_class
        
class MyImageStim(ImageStim):
    '''Extention of PsychoPy ImageStim Class.'''
    
    def __init__(self, display, index, image='', pos=None, units='deg',
                 size=None, opacity=0.5, show=True, stim_class=None):
        super().__init__(display, image=image, pos=pos, units=units,
                         size=size, opacity=opacity)
        self.index = index
        self.show = show
        self.stim_class = stim_class

class Visual:
    '''
    Visual stimulation class. Contains methods and attributes needed for
    stimulation purposes, between-process communication and lsl streaming.

    Attributes:
        mode -- which visual environment should be used, can be 'spiral'
                or 'sqare'
        screen_units -- which screen units need to be used to create a
                        visual environment, can be 'pix' or 'deg'
        monitor -- instance of psychopy Monitor object
                   setting up monitor for stimulation 
        display -- instance of psychopy Window object
                   setting up psychopy stimulation window 
        mouse -- instance of psychopy Mouse object
        fixation_mark -- instance of psychopy Monitor object
        photosensor_stim -- instance of psychopy Circle object
        lsl -- instance of lsl Stream outlet object
        lock, queue, pipe_in, pipe_out -- instances of multiprocessing objects
        groups -- groups of stimuli to flash simultaniously
        stimuli -- all stimuli as separate objects

    Methods:
        visual_environment:
        visual_stimulation:
        take_screenshot:
        visual_process:
    '''
    def __init__(self, queue, pipe_in, pipe_out, lock, mode='spiral', stimulation_mode='speller',
                 circles='all'):
        '''Initialize Visual class.
        
        Keyword arguments:
        queue -- Queue object to put data in and get it (used to
                 send and detect the end mark to stop all processes)
        pipe_in -- Pipe object to send messages (used to send a mark
                   and unlock Visual process)
        pipe_out -- Pipe object to recieve messages (used to receive a 
                    mark and unlock Visual process)
        lock -- Lock object to lock the process until another process
                unlocks it
        mode -- which visual environment should be used, can be 'spiral'
                or 'sqare' 
        stimulation_mode -- how to translate the feedback, can be 'speller' or
                         trainer
        circles -- a list of how many circles of stimuli should be placed on 
                   the screen, can be 'all' for all circles, or any combination
                   of  'inner', 'middle' and 'outer'
        '''
        
        # Multiprocessing tools
        self.lock = lock
        self.queue = queue
        self.pipe_in = pipe_in
        self.pipe_out = pipe_out
        # Data streaming tools
        self.LSL = self.create_lsl_outlet()
        # Stimulation protocols
        self.mode = mode
        self.stimulation_mode = stimulation_mode
        self.circles = circles
        self.psychopy_initialization()
        self.set_difficulty()
        if self.stimulation_mode=='trainer':
            self.get_images()
            self.chosen_dict = dict.fromkeys(self.images.keys(), 0) # for images
        self.get_stimuli() # make a list of stimuli for current session
        self.get_groups() # create groups attribute
        self.colors = {'flash':STIMCOL, 'que':QUECOL, 'choose':CHCOL}
        # For choosing algorithms
        self.chosen_ids = [] # to store what stimuli was chosen
        self.chosen_letters = '' # for spellers
        self.new_choice = True # flag for updating information box
        
        # wait(5) # Preventing the psychopy window from opening too early

    def get_groups(self):
        '''Create dictionary with groups of stimuli.'''
        
        if self.mode == 'spiral':
            self.groups = merge_two_dicts(GROUP1, GROUP2)
        else:
            self.groups = merge_two_dicts(ROWS, COLS)
    
    def get_images(self):
        imgdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')
        self.images = {'apple':os.path.join(imgdir, 'apple.png'),
                       'tomato':os.path.join(imgdir, 'tomato.png'),
                       'grape':os.path.join(imgdir, 'grape.png')}
        
    def create_lsl_outlet(self):
        '''Create stream outlet for sending markers.
        
        Returns:
        outlet -- StreamOutlet object to stream markers
        
        '''
        # Create info with necessary information about the stream
        info = StreamInfo(VISUAL_STREAM, 'Markers', 1, 0, 'int32',
                          '10106CA9-8564-4400-AB07-FFD2B668B86E') 
        # Create outlet
        outlet = StreamOutlet(info)
        return outlet
    
    def psychopy_initialization(self):
        '''Create all necessary PsychoPy instances'''
        
        self.screen_units = SCREEN_UNITS[self.mode]
        self.stim_pos = STIM_POS[self.mode]
        self.monitor = Monitor(MONITOR, WIDTH, DISTANCE)
        self.monitor.setSizePix(SIZE)
        self.display = Window(size=SIZE, monitor=self.monitor, units=self.screen_units,
                              color=BACKCOL, screen=MONITOR_N, fullscr=True)
        self.mouse = Mouse()
        self.fixation_mark = Circle(self.display, radius=0.05 ,edges=32,
                                    pos=CENTER, lineColor=FIXCOL)
        self.photosensor_stim = Rect(self.display, size = (5.5,5.5), fillColor = FIXCOL,
                                     lineWidth = 0, pos = PHOTOSENSOR_POS[self.mode]) # TODO: size for square mode
        self.pause_mark = TextStim(self.display, text='PAUSE', pos=PAUSE_POS,
                                   units=self.screen_units, height=STIM_SIZE[1]) # TODO: height and pos for square mode
        self.box = TextBox2(self.display, text='', pos=(-7, 14.4), units=self.screen_units) # Information box to show progress
        
    def set_difficulty(self):
        '''Tune circles that will be shown.
        
        Only for spiral mode!
        
        '''

        circles = ['inner', 'middle', 'outer'] if self.circles=='all' else self.circles

        circles_coords = {
            'outer': self.stim_pos[:9],
            'middle': self.stim_pos[9:18],
            'inner': self.stim_pos[18:]
        }
        
        self.available_positions = []
        for k, pos in circles_coords.items():
            if k in circles:
                self.available_positions.extend(pos)
        
        
    def get_stimuli(self):
        '''Creates list of stimuli.
        
        '''
        
        self.stimuli = []
        for position in self.stim_pos:
            index, stim_size = self.get_stim_size(position)
            
            if self.stimulation_mode=='speller':
                stim = MyTextStim(self.display, index, text=STIM_NAMES[index], pos=position,
                                    units=self.screen_units, height=stim_size, opacity=0.5)
            else:
                stim_class = random.choice(list(self.images.keys()))
                image = self.images[stim_class]
                stim = MyImageStim(self.display, index, image=image, pos=position,
                                   units=self.screen_units, size=stim_size, opacity=0.5,
                                   stim_class=stim_class)
            
            if position not in self.available_positions:
                stim.show = False
            
            self.stimuli.append(stim)
            
    def visual_environment(self, flash_group:tuple=(), state=''):
        '''Draw a frame of visual environment depending on state.
        
        Keyword arguments:
        flash_group -- tuple with indecies of stimuli that should be
                       higlighted
        state -- string contains the mode of visual environment frame
                 can be '' for basic environment, 'flash' for stimulation,
                 'que' or 'choose'
        
        '''
        
        # Draw proper stimuli configuration
        for stim in self.stimuli:
            
            if state in ('flash', 'que', 'choose') and stim.index in flash_group:
                # stim.color = self.colors[state]
                stim.setOpacity(1)   
            else:
                # stim.color = STIMCOL
                stim.setOpacity(0.5)
                
            if stim.show:
                stim.draw()
                
        # Drawing other stimuli
        if self.mode == 'spiral':
            self.fixation_mark.draw()
        # Photosensor stim
        if state == 'flash':
            self.photosensor_stim.draw()
        # Pause screen
        if state == 'pause':
            self.pause_mark.draw()
        # Summary or text
        self.draw_stats()
        
        self.display.flip()
            
    def choose(self, stim):
        '''Choose a stimulus'''
        
        self.show_target(stim.index)
        
        if self.stimulation_mode == 'trainer':
            stim.show = False
            self.chosen_dict[stim.stim_class] += 1
        else:
            self.chosen_letters += stim.text
        
        self.chosen_ids.append(stim.index)
        self.new_choice = True
        
    def get_stim_size(self, position):
        '''Give proper size to stimulus.
        
        Keyword arguments:
        position -- position of a stimulus on the screen
        
        Returns:
        stim_size -- size of a stimulus
        index -- index of a stimulus in STIM_NAMES (see CONSTANTS) 
        
        '''
        index = self.stim_pos.index(position)
        if self.mode == 'spiral':
            group_size = len(self.stim_pos)/len(STIM_SIZE)

            if index+1 <= group_size:
                stim_size = STIM_SIZE[0] 
            elif group_size < index+1 <= 2*group_size:
                stim_size = STIM_SIZE[1]
            else: 
                stim_size = STIM_SIZE[2]
        else:
            stim_size = 75
        return(index, stim_size)
    
    def visual_stimulation(self, flash_group, group_number):
        '''Run stimulation.
        
        Keyword arguments:
        flash_group -- tuple with coordinates of stimuli
        group_number -- key of a group in groups dicts (see CONSTANTS)

        '''
        self.visual_environment(flash_group = flash_group, state='flash')
        self.LSL.push_sample([group_number], float(time.time()))
        wait(FLASH)
        self.visual_environment(flash_group)
        wait(ISI)
    
    def show_target(self, index:int):
        '''Show target stimulus with multiple flashes.
        
        Keyword arguments:
        index -- index of the target stimulus

        '''
        wait(1)
        for _ in range(5):
            self.visual_environment((index,), state='que')
            wait(0.1)
            self.visual_environment()
            wait(0.1)
        wait(1)

    def draw_stats(self):
        '''Draw the counter of collected stimuli'''
        if not self.new_choice:
            self.box.draw()
            return
        if self.stimulation_mode=='speller':
            text = self.chosen_letters
        else:   
            text = f'''Collected items:\nApple - {self.chosen_dict['apple']}\nTomato - {self.chosen_dict['tomato']}\nGrape - {self.chosen_dict['grape']}'''
        self.box.setText(text)
        self.box.draw()
        self.new_choice = False

    def take_screenshot(self, filepath):
        '''Draw the visual environment and take a screenshot.'''

        self.visual_environment()
        self.display.getMovieFrame(buffer='front')
        self.display.saveMovieFrames(filepath)
        self.display.close()

    def create_sequence(self, seed=None):
        '''Create sequence of words to be used in the experiment.
        
        Returns:
        sequence -- list of words
        
        '''
        filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), '5_letter_words.txt')
        with open(filename, 'r') as f:
            lines=f.readlines()
        words=[]
        for line in lines:
            words.extend(line.split())
        list_of_words=[]
        for word in words:
            list_of_words.append(word)

        if seed:
            random.seed(seed)            
        sequence=random.sample(list_of_words, 4)

        target_file = os.path.join(FILEPATH, FILECODE, FILECODE+'_aims.txt')

        with open(target_file, 'w') as f:
             f.write(str(sequence))

        return sequence
        
    def pause(self):
        '''Pause the stimulation.'''
        
        # Track pause start in logging and send marker
        logging.info('Pause. Press space to continue.')
        self.LSL.push_sample([PAUSE_START], float(time.time()))
        # Draw pause screen
        self.visual_environment(state='pause')
        # Wait until user release pause
        waitKeys(maxWait=60, keyList=['space'])
        clearEvents()
        # Track pause end in logging and send marker
        logging.info('Continue stimulation...')
        self.LSL.push_sample([PAUSE_END], float(time.time()))
    
    
    def training_process(self):
        '''For online session to train classifier
        
        Need to include stimulation and data recording
        to train the classifier
        
        '''
        #TODO
        pass
    
    def user_process(self):
        '''For online session.
        
        Need to include stimulation and classification
        
        '''
        #TODO
        pass
    
    def visual_process(self, sequence=[], lockable=False, timer=False):
        '''
        Run visual process.
        
        Stimulation for scientific purposes.
        
        Keyword arguments:
        sequence -- list of lists or similar containers with indeces of target stimuli
        lockable -- bool, True if need to wait for another process to unlock it

        '''
        
        order=[i for i in range(len(self.groups))] # define order of flashes
        
        if not sequence:
            sequence=self.create_sequence()
        try:
            
            # Lock Visual process if necessary 
            if lockable:
                self.lock.acquire()
                logging.info("Visual process locked")

                while self.lock:
                    if self.pipe_out.recv() == int('1'):
                        self.lock.release()
                        break
                
            logging.info("Visual process started")
            self.visual_environment()
            
            waitKeys() # pressing any key starts the stimulation
            if timer:
                st = time.time()
            self.choose(self.stimuli[0])
            # self.choose(self.stimuli[11])
            # self.choose(self.stimuli[22])
            
            # Loop over all target words 
            for word in sequence:
                self.LSL.push_sample([WORD_START], float(time.time()))
                # Loop over all target letters
                for letter in word:
                    index = STIM_NAMES.index(letter.upper()) if isinstance(letter, str) else letter
                    logging.info('Letter {} in word {}'.format(letter, word))
                    # Show target stimulus
                    self.show_target(index)
                    # Loop over random flashes
                    self.LSL.push_sample([TRIAL_START], float(time.time()))
                    for i in range(TRIAL_LEN):
                        random.shuffle(order) # randomize flash order
                        for j in order:
                            self.visual_stimulation(self.groups[j], j)
                            # Gentle break of stimulation instead keyboard interrupt
                            if 's' in getKeys(['s']):
                                self.display.close()
                                return
                        # Check if need to pause stimulation
                        if 'p' in getKeys(['p']):
                            self.pause()
                            self.show_target(index) # Remind target letter                        
                    self.LSL.push_sample([TRIAL_END], float(time.time()))
                self.LSL.push_sample([WORD_END], float(time.time()))
                if timer:
                    et = time.time()
                    print(et-st)
                waitKeys() # Wait key press before going to next word
                
            self.display.close()
            
            self.queue.put(int(1))
                
        finally:
            self.display.close()



if __name__ == '__main__':

    logging.basicConfig(format='%(levelname)s	%(processName)s	%(message)s',
                        level=logging.INFO)
    logging.getLogger()
    queue = multiprocessing.Queue()
    pipe_in, pipe_out = multiprocessing.Pipe()
    lock = multiprocessing.Lock()
    
    a=Visual(queue, pipe_in, pipe_out, lock, stimulation_mode='speller')
    a.visual_process(sequence=[[15,]], timer=False)
    # a.visual_environment()
    # wait(3)
    # a.display.close()