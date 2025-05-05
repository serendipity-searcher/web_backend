MOON = r"""                   .--------------.
                .---'  o        .    `---.
             .-'    .    O  .         .   `-.
          .-'     @@@@@@       .             `-.
        .'@@   @@@@@@@@@@@       @@@@@@@   .    `.
      .'@@@  @@@@@@@@@@@@@@     @@@@@@@@@         `.
     /@@@  o @@@@@@@@@@@@@@     @@@@@@@@@     O     \
    /        @@@@@@@@@@@@@@  @   @@@@@@@@@ @@     .  \
   /@  o      @@@@@@@@@@@   .  @@  @@@@@@@@@@@     @@ \
  /@@@      .   @@@@@@ o       @  @@@@@@@@@@@@@ o @@@@ \
 /@@@@@                  @ .      @@@@@@@@@@@@@@  @@@@@ \
 |@@@@@    O    `.-./  .        .  @@@@@@@@@@@@@   @@@  |
/ @@@@@        --`-'       o        @@@@@@@@@@@ @@@    . \
|@ @@@@ .  @  @    `    @            @@      . @@@@@@    |
|   @@                         o    @@   .     @@@@@@    |
|  .     @   @ @       o              @@   o   @@@@@@.   |
\     @    @       @       .-.       @@@@       @@@      /
 |  @    @  @              `-'     . @@@@     .    .    |
 \ .  o       @  @@@@  .              @@  .           . /
  \      @@@    @@@@@@       .                   o     /
   \    @@@@@   @@\@@    /        O          .        /
    \ o  @@@       \ \  /  __        .   .     .--.  /
     \      .     . \.-.---                   `--'  /
      `.             `-'      .                   .'
        `.    o     / | `           O     .     .'
          `-.      /  |        o             .-'
             `-.          .         .     .-'
                `---.        .       .---'
                     `--------------'"""






NEW_MOON = """    _..._     
     .:::::::.    
    :::::::::::
    ::::::::::: 
    `:::::::::'  
      `':::''""" 
WAXING_CRESCENT = """       _..._     
     .::::. `.    
    :::::::.  :
    ::::::::  :  
    `::::::' .'  
      `'::'-'""" 

FIRST_QUARTER = """       _..._     
     .::::  `.    
    ::::::    :    
    ::::::    :  
    `:::::   .'  
      `'::.-'""" 

WAXING_GIBBOUS = """       _..._     
     .::'   `.    
    :::       :
    :::       :  
    `::.     .'  
      `':..-'"""

FULL_MOON="""       _..._     
     .'     `.    
    :         :
    :         :  
    `.       .'  
      `-...-'"""

WANING_GIBBOUS = """       _..._     
     .'   `::.    
    :       :::    
    :       :::  
    `.     .::'  
      `-..:''"""

LAST_QUARTER = """       _..._     
     .'  ::::.    
    :    ::::::
    :    ::::::  
    `.   :::::'  
      `-.::''"""   
WANING_CRESCENT = """       _..._     
     .' .::::.    
    :  ::::::::
    :  ::::::::  
    `. '::::::'  
      `-.::''"""

NEW_MOON = """       _..._     
     .:::::::.    
    :::::::::::
    :::::::::::  
    `:::::::::'  
      `':::''"""



import numpy as np

from skyfield.api import load

import datetime

def hourrange(start_datetime, end_datetime):
    td = end_datetime - start_datetime
    num_hours = td.days*24 + td.seconds/3600
    
    for n in range(int(num_hours)):
        yield start_datetime + datetime.timedelta(hours=n)


class Moon:
    def __init__(self):
        print(MOON, flush=True)
        self.ts = load.timescale()
        eph = load('de421.bsp')    
        self.sun, self.moon, self.earth = eph['sun'], eph['moon'], eph['earth']

        # self.rescale_epsilon, self.rescale_tau = 1e-9, 3


    def get_phase(self, dt):
        e = self.moon.at(self.ts.utc(dt.year, dt.month, dt.day))
        m = e.observe(self.earth).apparent()
        return m.fraction_illuminated(self.sun)

    def get_tide(self, dt, loc):
        b = 2*np.pi/13
        return (np.sin(dt.hour*b)+1)/2

    # in [0, 2]
    def __call__(self, dt, loc, rescale=True):
        cur = (self.get_phase(dt) + self.get_tide(dt, loc))/2
        # print("=================================================\n",
        #       f"raw force={cur}\n",
        #       "=================================================\n")
        if rescale:
            a, b = 0.005, 1.0
            return cur**4*(b-a)+a

        return cur
