# RP2040 DCC train decoder
# This is software decodes DCC model train serial communication to obtain the state of function buttons F1-F12.
# The intent is to use this code with a Raspberry Pi Pico or WaveShare RP2040-Zero to program and actuate signals and gates on a model train layout.
# MicroPython code of the parser functions is slow (700us), which consumes significant processor time (10%).
# Viper code with one long parcer function is faster (55us), resulting in a processor time (1%).
# Note: code was developed using MicroPython version v1.23

from rp2 import PIO, StateMachine, asm_pio
import uctypes
import array
import time

class DCC:
    def __init__(self,dccPin,dccAddress):
        from rp2 import PIO, StateMachine, asm_pio
        import uctypes
        import array
        import time
        self.dcc_pin_number = dccPin
        self.dcc_address_number = dccAddress    
        self.func_btn_number = 0

### Adjustable Variables
dcc_address_number = 82
dcc_pin_number = 16

### Definitions
semaphore = 0
func_btn_array = array.array('L',[0b0000000000000])
func_btn_array_addr = uctypes.addressof(func_btn_array)
data = array.array('L',[0xffffffff]) # memory location where proceed data will reside

### State Machine 0 Code
@rp2.asm_pio(set_init=rp2.PIO.IN_HIGH, in_shiftdir=0, out_shiftdir=0, autopull=True, pull_thresh=1, autopush=True, push_thresh=1) # set the bit order direction of OSR and ISR as well as autopull threshold to allow a single bit into the state machine while storing these bits in the ISR until full (32-bits) 
def determine_bit():
    wrap_target()

    wait(1, pin, 0)	    # wait for GPIO pin to go high
    nop()       [31]    # stall 32 microseconds
    nop()       [31]    # stall 32 microseconds
    nop()       [10]    # stall 10 microseconds
    jmp(pin, "set_0")   # if GPIO is remains high after 74 microseconds, then jump to set_0
    set(x, 1)           # if GPIO is low after 74 microseconds, then set scratch x to 1
    jmp("write_bit")    # since scratch x has been set to 1, skip set_0 and jump to write_bit

    label("set_0")
    set(x, 0)           # if GPIO is remains high after 74 microseconds, then set scratch x to 0

    label("write_bit")
    in_(x, 1)	        # move one bit from scratch x into the ISR
    wait(0, pin, 0)	    # wait for GPIO to go low before looping back to prevent recounting the same 0 bit

    irq(rel(0))			# set IRQ flag which will trigger the IRQ handler to get the 32-bit word from the RX FIFO
    wrap()

sm0 = rp2.StateMachine(0, determine_bit, freq=1000000, jmp_pin=dcc_pin_number, in_base=dcc_pin_number)	# sample pin as input at 2MHz or every 0.5 micro second
### End State Machine 0 Code

### State Machine 1 Code
@rp2.asm_pio(in_shiftdir=0, out_shiftdir=1, autopull=True, pull_thresh=1, autopush=False, push_thresh=32) # set the bit order direction of OSR and ISR as well as autopull threshold to allow a single bit into the state machine while storing these bits in the ISR until full (32-bits) 
def build_bitstream():
    wrap_target()

    # Search for preamble which is more than 9 consecutive ones    
    label("loop_1")
    set(y, 10)              # set scratch y to 10, this will be used for searching for the preamble
    label("pull")
    pull(block)			    # wait (block) for a 32-bit word to be added to the TX FIFO, then move the word to the OSR
    out(x, 1)			    # move one bit from OSR to scratch x    
    jmp(not_y, "find_addr_start_bit")    # if y is zero, then 10 consecutive ones were found which means the preamble was found, jump to find the address start bit
    jmp(not_x, "loop_1")    # if x is zero, then wrap to reset the y counter to 10
    jmp(y_dec, "pull")      # if y is 1 or more, then loop back to pull to get the next bit

    # Once preamble is found, then search for address start bit
    label("find_addr_start_bit")
    jmp(not_x, "send_bits") # if x is zero, then address start bit is found, jump to send bits to RX FIFO
    pull(block)			    # wait (block) for a 32-bit word to be added to the TX FIFO, then move the word to the OSR
    out(x, 1)               # move one bit from OSR to scratch x 
    jmp("find_addr_start_bit")

    # Once address start bit is found, then gather the next 32 bits into the RX FIFO
    label("send_bits")
    set(y, 31)			    # set scratch y to 31, this will count down for each bit to be added to ISR

    label("loop_2")
    pull(block)			    # wait (block) for a 32-bit word to be added to the TX FIFO, then move the word to the OSR
    out(x, 1)			    # move one bit from OSR to scratch x
    in_(x, 1)			    # move one bit from scratch x to ISR
    jmp(y_dec, "loop_2")	# loop back until 32 bits (bit stream) have filled the ISR
    
    push(noblock)		    # move the 32-bits from the ISR to the RX FIFO
    irq(rel(0))			    # set IRQ flag which will trigger the IRQ handler to get the 32-bit word from the RX FIFO
    wrap()

sm1 = rp2.StateMachine(1, build_bitstream)	# build array of bit at clock speed
### End State Machine 1 Code

### DMA Code
dma0 = rp2.DMA()    # initialize DMA channel, note: this is listed as DMA 0, but the actual DMA channel number can be any channel from 0 to 11 
dma1 = rp2.DMA()    # initialize DMA channel
dma2 = rp2.DMA()    # initialize DMA channel
dma3 = rp2.DMA()    # initialize DMA channel

dma0_ctrl = dma0.pack_ctrl(
    enable = True,          # enable DMA channel
    high_pri = True,        # set DMA bus traffic priority as high
    size = 2,               # Transfer size: 0=byte, 1=half word, 2=word (default: 2)
    inc_read = False,       # do not increment to read address
    inc_write = False,      # do not increment the write address
    ring_size = 0,          # increment size is zero
    ring_sel = False,       # use ring_size
    treq_sel = 4,           # select transfer rate of PIO0 RX FIFO, DREQ_PIO0_RX0
    irq_quiet = True,       # do not generate an interrupt after transfer is complete
    bswap = False,          # do not reverse the order of the word
    sniff_en = False,       # do not allow access to debug
    chain_to = dma1.channel # chain to dma1
)

dma1_ctrl = dma1.pack_ctrl(
    enable = True,          # enable DMA channel
    high_pri = True,        # set DMA bus traffic priority as high
    size = 2,               # Transfer size: 0=byte, 1=half word, 2=word (default: 2)
    inc_read = False,       # do not increment to read address
    inc_write = False,      # do not increment the write address
    ring_size = 0,          # increment size is zero
    ring_sel = False,       # use ring_size
    treq_sel = 4,           # select transfer rate of PIO0 RX FIFO, DREQ_PIO0_RX1
    irq_quiet = True,       # do not generate an interrupt after transfer is complete
    bswap = False,          # do not reverse the order of the word
    sniff_en = False,       # do not allow access to debug
    chain_to = dma0.channel # chain to dma0
)

dma2_ctrl = dma2.pack_ctrl(
    enable = True,          # enable DMA channel
    high_pri = True,        # set DMA bus traffic priority as high
    size = 2,               # Transfer size: 0=byte, 1=half word, 2=word (default: 2)
    inc_read = False,       # do not increment to read address
    inc_write = False,      # do not increment the write address
    ring_size = 0,          # increment size is zero
    ring_sel = False,       # use ring_size
    treq_sel = 5,           # select transfer rate of PIO0 RX FIFO, DREQ_PIO0_RX1
    irq_quiet = False,      # generate an interrupt after transfer is complete
    bswap = False,          # do not reverse the order of the word
    sniff_en = False,       # do not allow access to debug
    chain_to = dma3.channel # chain to dma3
)

dma3_ctrl = dma3.pack_ctrl(
    enable = True,          # enable DMA channel
    high_pri = True,        # set DMA bus traffic priority as high
    size = 2,               # Transfer size: 0=byte, 1=half word, 2=word (default: 2)
    inc_read = False,       # do not increment to read address
    inc_write = False,      # do not increment the write address
    ring_size = 0,          # increment size is zero
    ring_sel = False,       # use ring_size
    treq_sel = 5,           # select transfer rate of PIO0 RX FIFO, DREQ_PIO0_RX1
    irq_quiet = False,      # generate an interrupt after transfer is complete
    bswap = False,          # do not reverse the order of the word
    sniff_en = False,       # do not allow access to debug
    chain_to = dma2.channel # chain to dma2
)

sm0.active(1)   # set state machine active
sm1.active(1)   # set state machine active
dma0.active(1)  # set DMA channel active
dma1.active(1)  # set DMA channel active
dma2.active(1)  # set DMA channel active
dma3.active(1)  # set DMA channel active

RXF0_addr = const(0x50200020)   # address of RX FIFO register for State Machine 0, see RP2040 datasheet
TXF1_addr = const(0x50200014)   # address of TX FIFO register for State Machine 1
RXF1_addr = const(0x50200024)   # address of RX FIFO register for State Machine 1

# configure dma channels
dma0_config = dma0.config(read=RXF0_addr, write=TXF1_addr, count=1, ctrl=dma0_ctrl, trigger=True)
dma1_config = dma1.config(read=RXF0_addr, write=TXF1_addr, count=1, ctrl=dma1_ctrl, trigger=True)
dma2_config = dma2.config(read=RXF1_addr, write=uctypes.addressof(data), count=1, ctrl=dma2_ctrl, trigger=True)
dma3_config = dma3.config(read=RXF1_addr, write=uctypes.addressof(data), count=1, ctrl=dma3_ctrl, trigger=True)
### End DMA Code

### Data Parser Code
@micropython.viper
def parser(data_:int, DCC_address_:int, func_btn_array_:int, func_btn_array_address_:int):
    global semaphore
    semaphore = 1
    addr_bit0 = ((int(data_) >> 24 & 1) != 0)
    addr_bit1 = ((int(data_) >> 25 & 1) != 0)
    addr_bit2 = ((int(data_) >> 26 & 1) != 0)
    addr_bit3 = ((int(data_) >> 27 & 1) != 0)
    addr_bit4 = ((int(data_) >> 28 & 1) != 0)
    addr_bit5 = ((int(data_) >> 29 & 1) != 0)
    addr_bit6 = ((int(data_) >> 30 & 1) != 0)
    address_ = int(addr_bit6) << 6 | int(addr_bit5) << 5 | int(addr_bit4) << 4 | int(addr_bit3) << 3 | int(addr_bit2) << 2 | int(addr_bit1) << 1 | int(addr_bit0) << 0   
    if address_ == int(DCC_address_):
        grp_bit0 = ((int(data_) >> 19 & 1) != 0)
        grp_bit1 = ((int(data_) >> 20 & 1) != 0)
        grp_bit2 = ((int(data_) >> 21 & 1) != 0)
        grp_bit3 = ((int(data_) >> 22 & 1) != 0)
        func_grp_ = int(grp_bit3) << 3 | int(grp_bit2) << 2 | int(grp_bit1) << 1 | int(grp_bit0) << 0
        if func_grp_ == 0b1000: # F1-F4
            btn_bit0 = ((int(data_) >> 15 & 1) != 0)
            btn_bit1 = ((int(data_) >> 16 & 1) != 0)
            btn_bit2 = ((int(data_) >> 17 & 1) != 0)
            btn_bit3 = ((int(data_) >> 18 & 1) != 0)
            btn_bits = int(btn_bit3) << 3 | int(btn_bit2) << 2 | int(btn_bit1) << 1 | int(btn_bit0) << 0
            func_btn_array_ = int(func_btn_array_) & 0b1111111100001
            func_btn_array_ = int(func_btn_array_) | btn_bits << 1
        elif func_grp_ == 0b1001: # F1-F4
            btn_bit0 = ((int(data_) >> 15 & 1) != 0)
            btn_bit1 = ((int(data_) >> 16 & 1) != 0)
            btn_bit2 = ((int(data_) >> 17 & 1) != 0)
            btn_bit3 = ((int(data_) >> 18 & 1) != 0)
            btn_bits = int(btn_bit3) << 3 | int(btn_bit2) << 2 | int(btn_bit1) << 1 | int(btn_bit0) << 0
            func_btn_array_ = int(func_btn_array_) & 0b1111111100001
            func_btn_array_ = int(func_btn_array_) | btn_bits << 1        
        elif func_grp_ == 0b1011: # F5-F8
            btn_bit0 = ((int(data_) >> 15 & 1) != 0)
            btn_bit1 = ((int(data_) >> 16 & 1) != 0)
            btn_bit2 = ((int(data_) >> 17 & 1) != 0)
            btn_bit3 = ((int(data_) >> 18 & 1) != 0)
            btn_bits = int(btn_bit3) << 3 | int(btn_bit2) << 2 | int(btn_bit1) << 1 | int(btn_bit0) << 0
            func_btn_array_ = int(func_btn_array_) & 0b1111000011111
            func_btn_array_ = int(func_btn_array_) | btn_bits << 5
        elif func_grp_ == 0b1010: # F9-F12
            btn_bit0 = ((int(data_) >> 15 & 1) != 0)
            btn_bit1 = ((int(data_) >> 16 & 1) != 0)
            btn_bit2 = ((int(data_) >> 17 & 1) != 0)
            btn_bit3 = ((int(data_) >> 18 & 1) != 0)
            btn_bits = int(btn_bit3) << 3 | int(btn_bit2) << 2 | int(btn_bit1) << 1 | int(btn_bit0) << 0
            func_btn_array_ = int(func_btn_array_) & 0b0000111111111
            func_btn_array_ = int(func_btn_array_) | btn_bits << 9
        ptr32(func_btn_array_address_)[0] = int(func_btn_array_)
    semaphore = 0
    
def f_btn(func_btn_number): # return the boolean value of the x'th bit from the function button array
    if semaphore == 0:  # do not access the func_btn_array variable, if dma23_irq_handler() is manipulating the variable
        print("DCC", f"{func_btn_array[0]:013b}") 
        return ((func_btn_array[0] >> func_btn_number & 1) != 0) 

def dma23_irq_handler(dma1):
    if semaphore == 0:  # do not access the func_btn_array variable, if DCC() is manipulating the variable
        t0 = time.ticks_us()
        parser(data[0], dcc_address_number, func_btn_array[0], func_btn_array_addr)
        t1 = time.ticks_us()
        print(t1-t0)

# Note: dma2 and dma3 are configured to alternate their transfer of bits from state machine 1 to the variable "data"
dma2.irq(handler=dma23_irq_handler, hard=False)  # call dma23_irq_handler() when dma2 completes transfer of data
dma3.irq(handler=dma23_irq_handler, hard=False)  # call dma23_irq_handler() when dma3 completes transfer of data
### End Data Parser

# Test using while loop
from machine import Pin
LED = machine.Pin(25, Pin.OUT)
time_ = 0
while time_ < 10:
    #f_btn(7)
    LED.value(f_btn(7))
    time.sleep(1)
    time_ = time_ + 1
machine.soft_reset()
