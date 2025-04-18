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
import math
from machine import Pin, I2C, SPI, ADC, reset
#from rp2 import PIO, StateMachine, asm_pio
import sys
import math
import gc
from drivers.ssd1351.ssd1351_16bit import SSD1351 as SSD
import uasyncio as asyncio
from primitives.pushbutton import Pushbutton
from drivers import MPU6050
from ir_rx.nec import NEC_16  # NEC remote, 16 bit addresses
import max7219

def save(level1, level2, level3, level4):
    file = open("level.csv", "w")
    file.write(str(level1)+","+str(level2)+","+str(level3)+","+str(level4))
    file.close()
def load():
    file = open("level.csv", "r")
    data = file.readline()
    file.close()
    return data

def splash(product, company):
    wri = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
        50, 50, 0), bgcolor=0, verbose=False)
    CWriter.set_textpos(ssd, 90, 25)
    wri.printstring(company)
    ssd.show()
    utime.sleep(.3)
    for x in range(10):
        wri = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
            25*x, 25*x, 25*x), bgcolor=0, verbose=False)
        CWriter.set_textpos(ssd, 55, 25)
        wri.printstring(product)
        wri = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
            50-x, 50-x, 0), bgcolor=0, verbose=False)
        CWriter.set_textpos(ssd, 90, 25)
        wri.printstring(company)
        ssd.show()
    utime.sleep(2)
    for x in range(10, 0, -1):
        wri = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
            25*x, 25*x, 25*x), bgcolor=0, verbose=False)
        CWriter.set_textpos(ssd, 55, 25)
        wri.printstring(product)
        wri = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
            50-x, 50-x, 0), bgcolor=0, verbose=False)
        CWriter.set_textpos(ssd, 90, 25)
        wri.printstring(company)
        ssd.show()
    wri = CWriter(ssd, freesans20, fgcolor=SSD.rgb(
        50, 50, 0), bgcolor=0, verbose=False)
    CWriter.set_textpos(ssd, 90, 25)
    wri.printstring(company)
    ssd.show()
    utime.sleep(.3)
    return


# Screen to display on OLED during heating


def displaynum(course, minutes, seconds, timer, value, angle):
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
    wrimem.printstring(course)

    CWriter.set_textpos(ssd, 22, 0)
    wrimem.printstring("roll: " + str("{:.0f}".format(angle)))


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

splash("Sail IT", "Innograft")

# Define relay and LED pins

# Onboard led on GPIO 25, not currently used, but who doesnt love a controllable led?
ledPin = Pin(25, mode=Pin.OUT, value=1)
remotekey = ""
course = ""
# Method to process received data
def callback(data, addr, ctrl):
    global remotekey
    global course
    # Validate whether the data can be processed
    if data < 0:  
        print(hex(addr))
    else:
        # Output received data
        print("Received: \t Address:", hex(addr), "\tData:", data)
        if data == 2:
            remotekey = "reset"
        elif data == 96 or data == 7 or data == 96:
            remotekey = "up"
        elif data == 97 or data == 11 or data == 16:
            remotekey = "down"
        elif data == 4:
            course += "1"
        elif data == 5:
            course += "2"
        elif data == 6:
            course += "3"
        elif data == 8:
            course += "4"
        elif data == 9:
            course += "5"
        elif data == 10:
            course += "6"
        elif data == 12:
            course += "7"
        elif data == 13:
            course += "8"
        elif data == 17:
            course += "G"
        elif data == 45:
            course = ""
# Class for managing Encoder

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

# function for short button press - currently just a placeholder
def button():
    print('Button short press: Boop')
    return

# function for long button press - currently just a placeholder


def buttonlong():
    print('Button long press: Reset')
    return

# Main Logic

async def main():
    global remotekey
    global course
    # The Tweakable values that will help tune for our use case. TODO: Make accessible via menu on OLED
    checkin = 5
    started = False
    course = ""
    # Setup Level Encoder
    level = Encoder(22,26,27,-30,30)
    short_press = level.pb.release_func(button, ())
    long_press = level.pb.long_func(buttonlong, ())
        
    #local variables
    lastupdate = utime.time()
    lasttempupdate = utime.time()
    refresh(ssd, True)  # Initialise and clear display.
    start_time = 300
    m=5
    s=0
    displaytime=""
    start = utime.time()
 
    # PID loop - Default behaviour
    powerup = True

    # Create a map between keypad buttons and characters
    matrix_keys = [['1', '2', '3', 'A'],
               ['4', '5', '6', 'B'],
               ['7', '8', '9', 'C'],
               ['*', 'G', '#', 'D']]
    # PINs according to schematic - Change the pins to match with your connections
    keypad_rows = [15,14,13,12]
    keypad_columns = [11,10,9,8]
    # Create two empty lists to set up pins ( Rows output and columns input )
    col_pins = []
    row_pins = []
    # Loop to assign GPIO pins and setup input and outputs
    for x in range(0,4):
        row_pins.append(Pin(keypad_rows[x], Pin.OUT))
        row_pins[x].value(1)
        col_pins.append(Pin(keypad_columns[x], Pin.IN, Pin.PULL_DOWN))
        col_pins[x].value(0)
    
    # Setup the Gyro
    # Set up the I2C interface
    i2c = machine.I2C(1, sda=machine.Pin(2), scl=machine.Pin(3))
    # Set up the MPU6050 class 
    mpu = MPU6050.MPU6050(i2c)
    # wake up the MPU6050 from sleep
    mpu.wake()

    # define IR Receiver
    ir = NEC_16(Pin(5, Pin.IN), callback)

    #Intialize the SPI
    #matrix_spi = SPI(1, baudrate=10000000, polarity=1, phase=0, sck=Pin(18), mosi=Pin(7))
    if 0 ==1 :
        matrix_ss = Pin(21, Pin.OUT)
        # Create matrix display instant, which has four MAX7219 devices.
        matrix = max7219.Matrix8x8(matrix_spi, matrix_ss, 4)
        #Set the display brightness. Value is 1 to 15.
        matrix.brightness(10)
        matrix_message = "RASPBERRY PI PICO AND MAX7219 -- 8x8 DOT MATRIX SCROLLING DISPLAY"
        matrix_message_length = len(matrix_message)
        #Calculate number of columns of the message
        matrix_column = (matrix_message_length * 8)
        #Clear the display.
        matrix.fill(1)
        matrix.show()
    while True:
        if powerup:

            if started == True:
                now = start_time - (utime.time()-start) + level.counter
                # Calculate hour min seconds
                m,s = divmod(now,60)
                h,m = divmod(m,60)
                displaytime = "%01d:%02d" % (m,s)

            if 1 == 0:
                for x in range(32, -matrix_column, -1):     
                    #Clear the display
                    matrix.fill(1)
                    # Write the scrolling text in to frame buffer
                    matrix.text(matrix_message ,x,0,1)
                    #Show the display
                    matrix.show()
                    #Set the Scrolling speed. Here it is 50mS.
                    utime.sleep(0.05)

            try:
                gyro = mpu.read_gyro_data()
                accel = mpu.read_accel_data()
                print(accel, gyro)

                keypress = ""
                # Scan Keys
                for row in range(4):
                    for col in range(4):
                        row_pins[row].high()
                        key = None
                        
                        if col_pins[col].value() == 1:
                            keypress = matrix_keys[row][col]
                            print("You have pressed:", keypress)
                            key_press = matrix_keys[row][col]
                            utime.sleep(0.3)
                                
                    row_pins[row].low()
                if  keypress == "*":
                    course = ""
                elif  keypress == "A" or remotekey == "up":
                    level.up()
                    remotekey = ""
                elif  keypress == "B" or remotekey == "down":
                    level.down()
                    remotekey = ""
                elif  keypress == "#" or remotekey == "reset":
                    level.reset()
                    start = utime.time()
                    started = True
                    m=5
                    s=0
                    remotekey = ""
                else:
                    course += keypress
                if started == True and m <= 0 and s <=0:
                    started = False
                    displaytime = "Race"
                displaynum(course, m, s, displaytime, level.counter, mpu.roll)
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