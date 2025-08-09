# RP2040 signal block code with polling and timers
# Work in progress
# RP2040 takes input from four IR sensors to sense when a train car has entered a block
# Red is triggered immediately upon entering the first block
# Yellow and Green are triggered after two seconds of not sensing a train car
# Code is duplicated to support four RGB LED signals

### imports
import machine
import time

#### Setup

# RGB LEDs
Rgb1 = machine.PWM(1, freq=100, duty_u16=65535)
rGb1 = machine.PWM(0, freq=100, duty_u16=65535)
rgB1 = machine.PWM(2, freq=100, duty_u16=65535)

Rgb2 = machine.PWM(4, freq=100, duty_u16=65535)
rGb2 = machine.PWM(3, freq=100, duty_u16=65535)
rgB2 = machine.PWM(5, freq=100, duty_u16=65535)

Rgb3 = machine.PWM(7, freq=100, duty_u16=65535)
rGb3 = machine.PWM(6, freq=100, duty_u16=65535)
rgB3 = machine.PWM(8, freq=100, duty_u16=65535)

Rgb4 = machine.PWM(10, freq=100, duty_u16=65535)
rGb4 = machine.PWM(9, freq=100, duty_u16=65535)
rgB4 = machine.PWM(11, freq=100, duty_u16=65535)

# IR sensors
sense1 = machine.Pin(26, machine.Pin.IN, machine.Pin.PULL_UP)
sense2 = machine.Pin(27, machine.Pin.IN, machine.Pin.PULL_UP)
sense3 = machine.Pin(28, machine.Pin.IN, machine.Pin.PULL_UP)
sense4 = machine.Pin(29, machine.Pin.IN, machine.Pin.PULL_UP)

# Delay timer for each sensor
timer1 = machine.Timer()
timer2 = machine.Timer()
timer3 = machine.Timer()
timer4 = machine.Timer()

car_gap_time = 2000	# milliseconds, delay time for timer

sense1_state = sense2_state = sense3_state = sense4_state = 0
Red1_state = Yellow1_state = Red2_state = Yellow2_state = Red3_state = Yellow3_state = Red4_state = Yellow4_state = 0

### function definitions

def duty(x):
    y = x/100*65535
    return int(y)

def Red1():
    Rgb1.duty_u16(duty(0))
    rGb1.duty_u16(duty(100))
    rgB1.duty_u16(duty(100))

def Yellow1():
    Rgb1.duty_u16(duty(0))
    rGb1.duty_u16(duty(80))
    rgB1.duty_u16(duty(100))

def Green1():
    Rgb1.duty_u16(duty(100))
    rGb1.duty_u16(duty(20))
    rgB1.duty_u16(duty(100))

def Red2():
    Rgb2.duty_u16(duty(0))
    rGb2.duty_u16(duty(100))
    rgB2.duty_u16(duty(100))

def Yellow2():
    Rgb2.duty_u16(duty(0))
    rGb2.duty_u16(duty(80))
    rgB2.duty_u16(duty(100))

def Green2():
    Rgb2.duty_u16(duty(100))
    rGb2.duty_u16(duty(20))
    rgB2.duty_u16(duty(100))
    
def Red3():
    Rgb3.duty_u16(duty(0))
    rGb3.duty_u16(duty(100))
    rgB3.duty_u16(duty(100))

def Yellow3():
    Rgb3.duty_u16(duty(0))
    rGb3.duty_u16(duty(80))
    rgB3.duty_u16(duty(100))

def Green3():
    Rgb3.duty_u16(duty(100))
    rGb3.duty_u16(duty(20))
    rgB3.duty_u16(duty(100))

def Red4():
    Rgb4.duty_u16(duty(0))
    rGb4.duty_u16(duty(100))
    rgB4.duty_u16(duty(100))

def Yellow4():
    Rgb4.duty_u16(duty(0))
    rGb4.duty_u16(duty(80))
    rgB4.duty_u16(duty(100))

def Green4():
    Rgb4.duty_u16(duty(100))
    rGb4.duty_u16(duty(20))
    rgB4.duty_u16(duty(100)) 

def sense1_timer(x):
    sense1_state_at_timer = sense1.value()
        ### RGB3 Code    
    if (sense1_state_at_timer == 1) & (Red3_state == 0) & (Yellow3_state == 1):
        Green3()
        ### RGB4 Code
    if sense1_state_at_timer == 1:
        Yellow4()
        global Red4_state, Yellow4_state
        Red4_state = 0
        Yellow4_state = 1

def sense2_timer(x):
    sense2_state_at_timer = sense2.value()
        ### RGB1 Code
    if sense2_state_at_timer == 1:
        Yellow1()
        global Red1_state, Yellow1_state
        Red1_state = 0
        Yellow1_state = 1
        ### RGB4 Code
    if (sense2_state_at_timer == 1) & (Red4_state == 0) & (Yellow4_state == 1):
        Green4()

def sense3_timer(x):
    sense3_state_at_timer = sense3.value()
        ### RGB1 Code
    if (sense3_state_at_timer == 1) & (Red1_state == 0) & (Yellow1_state == 1):
        Green1()
        ### RGB2 Code
    if sense3_state_at_timer == 1:
        Yellow2()
        global Red2_state, Yellow2_state
        Red2_state = 0
        Yellow2_state = 1

def sense4_timer(x):
    sense4_state_at_timer = sense4.value()
        ### RGB2 Code
    if (sense4_state_at_timer == 1) & (Red2_state == 0) & (Yellow2_state == 1):
        Green2()
        ### RGB3 Code
    if sense4_state_at_timer == 1:
        Yellow3()
        global Red3_state, Yellow3_state
        Red3_state = 0
        Yellow3_state = 1

while True:
    sense1_state = sense1.value()
    sense2_state = sense2.value()
    sense3_state = sense3.value()    
    sense4_state = sense4.value()

### Code for RGB1

    if sense1_state == 0:
        Red1()
        Red1_state = 1
        Yellow1_state = 0
        timer1.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense1_timer)
        
    if (sense2_state == 0) & (Red1_state == 1):
        timer2.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense2_timer)
        
    if (sense3_state == 0) & (Red1_state == 0) & (Yellow1_state == 1):
        timer3.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense3_timer)

### Code for RGB2

    if sense2_state == 0:
        Red2()
        Red2_state = 1
        Yellow2_state = 0
        timer2.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense2_timer)
        
    if (sense3_state == 0) & (Red2_state == 1):
        timer3.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense3_timer)

    if (sense4_state == 0) & (Red2_state == 0) & (Yellow2_state == 1):
        timer4.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense4_timer)

### Code for RGB3

    if sense3_state == 0:
        Red3()
        Red3_state = 1
        Yellow3_state = 0
        timer3.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense3_timer)
        
    if (sense4_state == 0) & (Red3_state == 1):
        timer4.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense4_timer)

    if (sense1_state == 0) & (Red3_state == 0) & (Yellow3_state == 1):
        timer1.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense1_timer)

### Code for RGB4

    if sense4_state == 0:
        Red4()
        Red4_state = 1
        Yellow4_state = 0
        timer4.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense4_timer)
        
    if (sense1_state == 0) & (Red4_state == 1):
        timer1.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense1_timer)

    if (sense2_state == 0) & (Red4_state == 0) & (Yellow4_state == 1):
        timer2.init(mode=machine.Timer.ONE_SHOT, period=car_gap_time, callback=sense2_timer)


