# Work in progress
import time
from rp2 import PIO, asm_pio, StateMachine
from machine import Pin, PWM

Train_Address = 82	#between 1 to 127, 82 = 0x1010010 = 52
Preamble = 0x111111111	# 9 ones

pulse_width = 1
RX_FIFO = 0xFFFFFFFF				# 32-bit
bit_array = 0xFFFFFFFF				# 32-bit

# measure pulse width of each squarewave high time to determine a 0 or 1 for decoding DCC per NMRA standard S-9.1
@rp2.asm_pio(set_init=rp2.PIO.IN_LOW) 
def pulse_width_measure():
    wrap_target()
    
    mov(x, invert(null))# set scratch x to 0xFFFFFFFF
    wait(1, gpio, 16)	# wait for GPIO pin to go high
    
    label("timer")
    jmp(x_dec, "test")	# if x not zero, then jump to test, count down x
    wrap()				# if x is zero, then timed out, therefore wrap to start over
    
    label("test")
    jmp(pin, "timer")	# test if the pin is still 1, if so, continue counting down
    
    mov(isr, x)			# if pin is 0, move the value in x to the ISR
    push(noblock)		# push the ISR into the RX FIFO
    irq(rel(0))			# set IRQ flag for program to retreive data (get) from RX FIFO
    wrap()

def handler(sm0):
    RX_FIFO = sm0.get()
    pulse_width = (0xFFFFFFFF - RX_FIFO)
    if pulse_width in range(50, 65, 1):
#        bit_array = bit_array << 1
#        bit_array |= (1 << 0)
        print("1")
    elif pulse_width in range(90, 10000, 1):
#        bit_array = bit_array << 1
#        bit_array &= (0 << 0)
        print("0")
    else: 
        print("pulse width size error, pulse width is",pulse_width,"microseconds")

pin22 = PWM(Pin(22), freq=9000, duty_u16=32768)	# PWM signal at 5kHz with 50% duty cycle (high for 100 micro seconds per cycle)

sm0 = rp2.StateMachine(0, pulse_width_measure, freq=2000000, jmp_pin=Pin(16))	# sample pin as input at 2MHz or every 0.5 micro second
sm0.irq(handler, trigger=0 | 1, hard=False)
sm0.active(1)
#time.sleep(1)
#sm0.active(0)

while True:
    if True:
        pin22.freq(5000)
#        print(0xFFFFFFFF - sm0.get())
        time.sleep(1)
#        print(0xFFFFFFFF - sm0.get())
        pin22.freq(10000)
        time.sleep(1)
#        print(0xFFFFFFFF - sm0.get())
        pin22.freq(2500)
        time.sleep(1)
#        print(0xFFFFFFFF - sm0.get())
        pin22.freq(20000)
        time.sleep(1)
#        print(0xFFFFFFFF - sm0.get())


# Connect a jumper wire between GPIO 16 and GPIO 22 to test the accuracy of the pulse width time measurement
# The result should print 100, which is the high time in microseconds of a 5kHz squarewave
