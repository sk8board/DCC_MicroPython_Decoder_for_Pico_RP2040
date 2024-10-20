# RP2040 signal block code with machine.irq() and timers
#
# Work in Progress
#
# RP2040 takes input from four IR sensors to sense when a train car has entered a block
# Red is triggered immediately upon entering the first block
# Yellow and Green are triggered after two seconds of not sensing a train car
# Note: IR sensors have many false triggers due to variation in reflectivity which overloads
# the scheduler with many interrupt requests. Must use polling with timers rather than machine.irq()

### imports
import machine
import time

#### Setup

# RGB LEDs
Rgb1 = machine.PWM(0, freq=100, duty_u16=65535)
rGb1 = machine.PWM(1, freq=100, duty_u16=65535)
rgB1 = machine.PWM(2, freq=100, duty_u16=65535)

# IR sensors
sense1 = machine.Pin(5, machine.Pin.IN, machine.Pin.PULL_UP)
sense2 = machine.Pin(12, machine.Pin.IN, machine.Pin.PULL_UP)
sense3 = machine.Pin(14, machine.Pin.IN, machine.Pin.PULL_UP)
sense4 = machine.Pin(15, machine.Pin.IN, machine.Pin.PULL_UP)

# Delay timer for each sensor
timer1 = machine.Timer()
timer2 = machine.Timer()
timer3 = machine.Timer()
timer4 = machine.Timer()

car_gap_time = 2000	# milliseconds, delay time for timer

### defining functions

def duty(x):
    y = x/100*65535
    return int(y)

def Red1(x):
    Rgb1.duty_u16(duty(0))
    rGb1.duty_u16(duty(100))
    rgB1.duty_u16(duty(100))

def Yellow1(x):
    Rgb1.duty_u16(duty(0))
    rGb1.duty_u16(duty(80))
    rgB1.duty_u16(duty(100))

def Green1(x):
    Rgb1.duty_u16(duty(100))
    rGb1.duty_u16(duty(20))
    rgB1.duty_u16(duty(100))    

def sense1_timer(x):
    if sense2.value() == 1:
        pass
        #Red(x)

def sense1_irq(x):
    timer1.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense1_timer)
    Red1(x)

def sense2_timer(x):
    if sense2.value() == 1:
        Yellow1(x)

def sense2_irq(x):
    timer2.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense2_timer)

def sense3_timer(x):
    if sense3.value() == 1:
        Green1(x)
        
def sense3_irq(x):
    timer3.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense3_timer)

def sense4_timer(x):
    if sense4.value() == 1:
        pass
        #Green1(x)
        
def sense4_irq(x):
    timer4.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense4_timer)

sense1.irq(sense1_irq,machine.Pin.IRQ_RISING)
sense2.irq(sense2_irq,machine.Pin.IRQ_RISING)
sense3.irq(sense3_irq,machine.Pin.IRQ_RISING)
sense4.irq(sense4_irq,machine.Pin.IRQ_RISING)
