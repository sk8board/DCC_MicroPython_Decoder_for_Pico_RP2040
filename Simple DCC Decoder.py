# Work in progress
import time
from rp2 import PIO, asm_pio, StateMachine
from machine import Pin, PWM

# measure pulse width of each squarewave high time to determine a 0 or 1 for decoding DCC per NMRA standard S-9.1
@rp2.asm_pio(set_init=rp2.PIO.IN_LOW) 
def pulse_width():
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
    print(0xFFFFFFFF - RX_FIFO)
#    if RX_FIFO in range(50, 65, 1):
#        Byte_Array = ByteArray << 1
#        Byte_Array[] = 1
#    elif RX_FIFO in range(90, 10000, 1):
#        Byte_Array = ByteArray << 1
#        Byte_Array[] = 1
#    else: 
#        Print("error")

pin22 = PWM(Pin(22), freq=5000, duty_u16=32768)	# PWM signal at 5kHz with 50% duty cycle (high for 100 micro seconds per cycle)

sm0 = rp2.StateMachine(0, pulse_width, freq=2000000, jmp_pin=Pin(16))	# sample pin as input at 2MHz or every 0.5 micro second
sm0.irq(handler, trigger=0 | 1, hard=False)
sm0.active(1)

# Connect a jumper wire between GPIO 16 and GPIO 22 to test the accuracy of the pulse width time measurement
# The result should print 100, which is the high time in microseconds of a 5kHz squarewave
