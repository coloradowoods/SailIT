# main.py - a script for making a plant watering thing, running using a Raspberry Pi Pico
# First prototype is using an OLED, rotary encoder and a relay switch (linked to water pump device of some sort)
# The display uses drivers made by Peter Hinch [link](https://github.com/peterhinch/micropython-nano-gui)

# Released under the GPL 3.0

# Fonts for Writer (generated using https://github.com/peterhinch/micropython-font-to-py)
import gui.fonts.freesans20 as freesans20
import gui.fonts.quantico40 as quantico40
import gui.fonts.arial35 as arial35
from gui.core.writer import CWriter
from gui.core.nanogui import refresh
import utime
from machine import Pin, I2C, SPI, ADC, reset
#from rp2 import PIO, StateMachine, asm_pio
import sys
import math
import gc
from drivers.ssd1351.ssd1351_16bit import SSD1351 as SSD
import uasyncio as asyncio
from primitives.pushbutton import Pushbutton


def save(level1, level2, level3, level4):
    file = open("level.csv", "w")
    file.write(str(level1)+","+str(level2)+","+str(level3)+","+str(level4))
    file.close()
def load():
    file = open("level.csv", "r")
    data = file.readline()
    file.close()
    return data

def splash(string):
    wri = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
        50, 50, 0), bgcolor=0, verbose=False)
    CWriter.set_textpos(ssd, 90, 25)
    wri.printstring('InnoGraft')
    ssd.show()
    utime.sleep(.3)
    for x in range(10):
        wri = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
            25*x, 25*x, 25*x), bgcolor=0, verbose=False)
        CWriter.set_textpos(ssd, 55, 25)
        wri.printstring(string)
        wri = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
            50-x, 50-x, 0), bgcolor=0, verbose=False)
        CWriter.set_textpos(ssd, 90, 25)
        wri.printstring('InnoGraft')
        ssd.show()
    utime.sleep(2)
    for x in range(10, 0, -1):
        wri = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
            25*x, 25*x, 25*x), bgcolor=0, verbose=False)
        CWriter.set_textpos(ssd, 55, 25)
        wri.printstring(string)
        wri = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
            50-x, 50-x, 0), bgcolor=0, verbose=False)
        CWriter.set_textpos(ssd, 90, 25)
        wri.printstring('InnoGraft')
        ssd.show()
    wri = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
        50, 50, 0), bgcolor=0, verbose=False)
    CWriter.set_textpos(ssd, 90, 25)
    wri.printstring('InnoGraft')
    ssd.show()
    utime.sleep(.3)
    return
# function for short button press - currently just a placeholder
def button():
    print('Button short press: Boop')
    return

# function for long button press - currently just a placeholder


def buttonlong():
    print('Button long press: Reset')
    return

# Screen to display on OLED during heating


def displaynum(mode, minutes, seconds, timer, value):
    # This needs to be fast for nice responsive increments
    # 100 increments?
    ssd.fill(0)
    text = SSD.rgb(0, 255, 0)
    if minutes <= 1:
        text = SSD.rgb(165, 42, 42)
    if minutes <= 2:
        text = SSD.rgb(0, 255, 255)
    wri = CWriter(ssd, arial35, fgcolor=text, bgcolor=0, verbose=False)
    # verbose = False to suppress console output
    CWriter.set_textpos(ssd, 0, 0)
    wrimem = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
        155, 155, 155), bgcolor=0)
    wrimem.printstring('Mode: '+ mode)

    CWriter.set_textpos(ssd, 22, 0)
    wrimem.printstring('Time Til Start:')


    CWriter.set_textpos(ssd, 60, 0)
    wri.printstring(timer)
    wrimem = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
        255, 255, 255), bgcolor=0, verbose=False)
    CWriter.set_textpos(ssd, 65, 85)
    wrimem.printstring(str("{:.0f}".format(value)))
    ssd.show()
    return


def beanaproblem(string):
    refresh(ssd, True)  # Clear any prior image
    wri = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
        250, 250, 250), bgcolor=0, verbose=False)
    CWriter.set_textpos(ssd, 55, 25)
    wri.printstring(string)
    ssd.show()
    relaypin = Pin(15, mode=Pin.OUT, value=0)
    utime.sleep(2)


# Setup display
height = 128
pdc = Pin(20, Pin.OUT, value=0)
pcs = Pin(17, Pin.OUT, value=1)
prst = Pin(21, Pin.OUT, value=1)
spi = SPI(0,
          baudrate=10000000,
          polarity=1,
          phase=1,
          bits=8,
          firstbit=SPI.MSB,
          sck=Pin(18),
          mosi=Pin(19),
          miso=Pin(16))
gc.collect()  # Precaution before instantiating framebuf

ssd = SSD(spi, pcs, pdc, prst, height)  # Create a display instance

splash("Sail IT")

# Define relay and LED pins

# Onboard led on GPIO 25, not currently used, but who doesnt love a controllable led?
ledPin = Pin(25, mode=Pin.OUT, value=0)


class Encoder:
    def __init__(self, clk, dt, sw, min, max):
        self.clk = clk
        self.dt = dt
        self.sw = sw
        self.min = min
        self.max = max
        # define class variables
        self.counter = 0   # counter updates when encoder rotates
        self.direction = ""  # empty string for registering direction change
        self.outA_last = 0  # registers the last state of outA pin / CLK pin
        self.outA_current = 0  # registers the current state of outA pin / CLK pin
        # define encoder pins
        self.btn = Pin(self.sw, Pin.IN, Pin.PULL_UP)  # Adapt for your hardware
        self.pb = Pushbutton(self.btn, suppress=True)
        self.outA = Pin(self.clk, mode=Pin.IN)  # Pin CLK of encoder
        self.outB = Pin(self.dt, mode=Pin.IN)  # Pin DT of encoder
        # attach interrupt to the outA pin ( CLK pin of encoder module )
        self.outA.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING,
         handler=self.encoder)
        # attach interrupt to the outB pin ( DT pin of encoder module )
        self.outB.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING,
                 handler=self.encoder)
    def down(cls):
        cls.counter -= .5
    def up(cls):
        cls.counter += .5
    def reset(cls):
        cls.counter = 0
    def encoder(cls, pin):
        # read the value of current state of outA pin / CLK pin
        try:
            cls.outA = Pin(cls.clk, mode=Pin.IN)  # Pin CLK of encoder
            cls.outA_current = cls.outA.value()
        except:
            print('outA not defined')
            cls.outA_current = 0
            cls.outA_last = 0
        # if current state is not same as the last stare , encoder has rotated
        if cls.outA_current != cls.outA_last:
            # read outB pin/ DT pin
            # if DT value is not equal to CLK value
            # rotation is clockwise [or Counterclockwise ---> sensor dependent]
            if cls.outB.value() != cls.outA_current:
                cls.counter += 1
            else:
                cls.counter -= 1

            # print the data on screen
            print("Class Counter : ", cls.counter, "     |   Direction : ",cls.direction)
            print("\n")

        # update the last state of outA pin / CLK pin with the current state
        cls.outA_last = cls.outA_current
        cls.counter = min(cls.max, cls.counter)
        cls.counter = max(cls.min, cls.counter)
        return(cls.counter)


# Main Logic

async def main():
    # The Tweakable values that will help tune for our use case. TODO: Make accessible via menu on OLED
    checkin = 5
    started = False
    # Setup Level Encoder
    level = Encoder(2,3,4,-30,30)
    
    short_press = level.pb.release_func(button, ())
    long_press = level.pb.long_func(buttonlong, ())
    
    # define buttons
    down = Pin(0, Pin.IN, Pin.PULL_DOWN)
    up = Pin(1, Pin.IN, Pin.PULL_DOWN)
    reset = Pin(5, Pin.IN, Pin.PULL_DOWN)
    
    #local variables
    pin = 0
    ##integral = 0
    lastupdate = utime.time()
    refresh(ssd, True)  # Initialise and clear display.
    # Load levels for file
    data = str.split(load(), ',')
    
    data = str.split(load(), ',')
    print(data)
    
    start_time = 300
    m=5
    s=0
    displaytime=""
    start = utime.time()
    refresh(ssd, True)
    # PID loop - Default behaviour
    powerup = True
    while True:
        if powerup:
            if started == True:
                now = start_time - (utime.time()-start) + level.counter
                # Calculate hour min seconds
                m,s = divmod(now,60)
                h,m = divmod(m,60)
                displaytime = "%01d:%02d" % (m,s)
            #print(displaytime)
            try:
                if started == True and m <= 0 and s <=0:
                    started = False
                    displaytime = "Started"
                if down.value() == 1:
                    level.down()
                if up.value() == 1:
                    level.up()
                if reset.value() == 1:
                    level.reset()
                    start = utime.time()
                    started = True
                displaynum("RACE", m, s, displaytime, level.counter)
                now = utime.time()
                dt = now-lastupdate
                if dt > checkin:
                    utime.sleep(.1)
                    lastupdate = now

            except Exception as e:
                # Put something to output to OLED screen
                beanaproblem('error.')
                print('error encountered:'+str(e))
                utime.sleep(checkin)
        else:
            refresh(ssd, True)  # Clear any prior image
            relaypin = Pin(15, mode=Pin.OUT, value=0)
        await asyncio.sleep(.01)

asyncio.run(main())