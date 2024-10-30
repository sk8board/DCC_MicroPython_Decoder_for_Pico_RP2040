# RP2040 DCC train decoder
#
# Work In Progress
#
# This software decodes DCC model train serial communication to obtain the state of function buttons F1-F12.
# The intent is to use this code with a Raspberry Pi Pico or WaveShare RP2040-Zero to program and actuate signals and gates on a model train layout.
# Note: appropriate circuitry is needed between the Pico and the railroad tracks to protect the Pico from damage.
# Note: code was developed using MicroPython version v1.23

import uctypes
import array
import rp2

### Definitions
semaphore = 0	# used to control access to buffered variables for prevention of conflict
short_address = 127	# maximum threshold of a short address
func_btn_array = array.array('L',[0b0000000000000])
func_btn_array_addr = uctypes.addressof(func_btn_array)
data = array.array('L',[0xffffffff,0xffffffff]) 

class pin_addr: 							# retrieve GPIO pin number that connect to the railroad tracks
    def __init__(self,dccPin,dccAddress):	# and retrieve the short DCC address for this decoder
        global dcc_address_number			# Note: the address must be between 1 to 127
        self.dccPin = dccPin
        dcc_address_number = dccAddress
        sm1_config()
        dma_config()

        ### State Machine 0 Code
        @rp2.asm_pio(set_init=rp2.PIO.IN_HIGH, in_shiftdir=0, out_shiftdir=0, autopull=True, pull_thresh=1, autopush=True, push_thresh=1) # set the bit order direction of OSR and ISR as well as autopull threshold to allow a single bit into the state machine while storing these bits in the ISR until full (32-bits) 
        def determine_bit():
            wrap_target()

            wait(1, pin, 0)	[31]    # wait for GPIO pin to go high
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

            wrap()

        sm0 = rp2.StateMachine(0, determine_bit, freq=1000000, jmp_pin=self.dccPin, in_base=self.dccPin)	# sample pin as input at 2MHz or every 0.5 micro second
        sm0.active(1)   # set state machine active
        ### End State Machine 0 Code

### State Machine 1 Code
def sm1_config():
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

        # Once address start bit is found, then gather the next 3 bits into the RX FIFO
        #label("send_bits")
        set(y, 2)			    # set scratch y to 2, this will count down for each bit to be added to ISR
    
        label("loop_3")
        pull(block)			    # wait (block) for a 3-bit word to be added to the TX FIFO, then move the word to the OSR
        out(x, 1)			    # move one bit from OSR to scratch x
        in_(x, 1)			    # move one bit from scratch x to ISR
        jmp(y_dec, "loop_3")	# loop back until 3 bits (bit stream) have filled the ISR
        
        push(noblock)		    # move the 32-bits from the ISR to the RX FIFO

        #irq(rel(0))			    # set IRQ flag which will trigger the IRQ handler to get the 32-bit word from the RX FIFO
        wrap()

    sm1 = rp2.StateMachine(1, build_bitstream)	# build array of bit at clock speed
    #sm1.irq(handler=dma23_irq_handler, hard=False)
    sm1.active(1)   # set state machine active
### End State Machine 1 Code

### DMA Code
def dma_config():
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
        ring_sel = False,       # not used since ring_sel is zero
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
        ring_sel = False,       # not used since ring_sel is zero
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
        inc_write = True,      	# increment the write address
        ring_size = 0,          # increment size is zero
        ring_sel = True,       	# not used since ring_sel is zero
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
        ring_sel = True,       	# not used since ring_sel is zero
        treq_sel = 0x3f,        # select transfer rate of system full speed to restart DMA2
        irq_quiet = True,      	# do not generate an interrupt after transfer is complete
        bswap = False,          # do not reverse the order of the word
        sniff_en = False,       # do not allow access to debug
        chain_to = dma3.channel # chain to self
    )

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
    dma2_config = dma2.config(read=RXF1_addr, write=uctypes.addressof(data), count=2, ctrl=dma2_ctrl, trigger=True)
    dma3_config = dma3.config(read=dma2_ctrl, write=dma2.registers[15:15], count=2, ctrl=dma3_ctrl, trigger=True)

    # Note: dma2 and dma3 are configured to alternate their transfer of bits from state machine 1 to the variable "data"
    dma2.irq(handler=dma23_irq_handler, hard=False)  # call dma23_irq_handler() when dma2 completes transfer of data
    dma3.irq(handler=dma23_irq_handler, hard=False)  # call dma23_irq_handler() when dma3 completes transfer of data
### End DMA Code

### Data Parser Code
@micropython.viper
def addr_parser(data_:uint,dcc_address_number_:uint)->bool: # parse bits from data to obtain the address
    if uint(dcc_address_number_) > uint(short_address):
        data_addr_MSByte = (uint(data_) >> 24) & ~(0xFFFFFF0)
        data_addr_LSByte = (uint(data_) >> 15) & ~(0xFFFFF00)
        data_addr = (uint(data_addr_MSByte) << 8) + uint(data_addr_LSByte)	# parse long address
        return uint(data_addr) == uint(dcc_address_number_)
    else:
        data_addr = (uint(data_) >> 24) & ~(0b10000000)		# parse short address
        return uint(data_addr) == uint(dcc_address_number_)

@micropython.viper
def func_grp_parser(data_:uint)->uint: # parse bits from data to obtain the function group number
    if uint(dcc_address_number) > uint(short_address):
        return (uint(data_) >> 10) & ~(0xFFFFFF0)
    else:
        return (uint(data_) >> 19) & ~(0xFFFFFF0)

@micropython.viper
def func_btn_parser(data_:uint)->uint: # parse bits from data to obtain the state of the function buttons
    if uint(dcc_address_number) > uint(short_address):
        return (uint(data_) >> 6) & ~(0xFFFFFF0)
    else:
        return (uint(data_) >> 15) & ~(0xFFFFFF0)

@micropython.viper
def func_btn_array_build(data_:int,func_btn_array_:int):    # Update and build the function button array from data
    global semaphore
    semaphore = 1   # Prevent other functions from accessing func_btn_array while manipulating this variables
    #print(addr_parser_)
    if int(addr_parser(data_,dcc_address_number)):
        func_grp_parser_ = int(func_grp_parser(data_))
        if func_grp_parser_ == 0b1000: # F1-F4
            func_btn_array_ = int(func_btn_array_) & 0b1111111100001
            func_btn_array_ = int(func_btn_array_) | int(func_btn_parser(data_)) << 1
        elif func_grp_parser_ == 0b1001: # F1-F4
            func_btn_array_ = int(func_btn_array_) & 0b1111111100001
            func_btn_array_ = int(func_btn_array_) | int(func_btn_parser(data_)) << 1
        elif func_grp_parser_ == 0b1011: # F5-F8
            func_btn_array_ = int(func_btn_array_) & 0b1111000011111
            func_btn_array_ = int(func_btn_array_) | int(func_btn_parser(data_)) << 5
        elif func_grp_parser_ == 0b1010: # F9-F12
            func_btn_array_ = int(func_btn_array_) & 0b0000111111111
            func_btn_array_ = int(func_btn_array_) | int(func_btn_parser(data_)) << 9
        elif func_grp_parser_ == 0b0011: # 126 step speed
            pass # TBD
        elif func_grp_parser_ == (0b0100 or 0b0101): # 28 step reverse speed
            pass # TBD
        elif func_grp_parser_ == (0b0110 or 0b0111): # 28 step forward speed
            pass # TBD
        ptr32(func_btn_array_addr)[0] = int(func_btn_array_)
    semaphore = 0 # Allow access of func_btn_array to other functions

def f_btn(func_btn_number): # return the boolean value of the x'th bit from the function button array
    if semaphore == 0:  # do not access the func_btn_array variable, if dma23_irq_handler() is manipulating the variable
        return ((func_btn_array[0] >> func_btn_number & 1) != 0) 
### End Data Parser

### Interrupt Handler
def dma23_irq_handler(dma1):
    if semaphore == 0:  # do not access the func_btn_array variable, if DCC() is manipulating the variable
        func_btn_array_build(data[0],func_btn_array[0])
