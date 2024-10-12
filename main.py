from machine import Pin
import time
import DCC

LED = Pin(25, Pin.OUT)

# Enter the GPIO pin that is connected to the railroad tracks
# and enter the desired DCC address for this decoder
# Note: appropriate circuitry is needed between the Pico
# and the railroad tracks to protect the Pico from damage.
# Note: the address must be between 1 and 127
my_dcc_decoder = DCC.pin_addr(16,1) # (pin, addr)

while True:					# DCC.f_btn(n) returns True or False of button number 'n'
    LED.value(DCC.f_btn(3))	# Works for function buttons 1 to 12
    print("DCC", f"{DCC.func_btn_array[0]:013b}") # print the array of function buttons
    time.sleep(0.5)
    
    
