# RP2040 DMA Chain Example with PIO
# 
# 1) For loop will feed state machine 0 one bit at a time.
# 2) State machine 0 will pass the bit from TX FIFO to RX FIFO then autopush will trigger DMA 0 or DMA 1
# 3) DMA 0 and DMA 1 will move the bit from state machine 0 TX FIFO to state machine 1 RX FIFO
#    Note: DMA 0 and DMA 1 are "chained" together, which means after DMA 0 completes the transfer, 
#    then DMA 0 will triggers DMA 1, then DMA 1 will do the same to DMA 0 after completion
#    of data transfer, the RP2040 datasheet calls this "ping-pong" DMA transfer.
# 4) State machine 1 will accumulate 32 bits then autopush will trigger DMA 2 or DMA 3
# 5) DMA 2 and DMA 3 will move the bit from state machine 1 TX FIFO to the address of "output_data".
#    DMA 2 and DMA 3 are chained together and perform "ping-pong" like DMA 0 and DMA 1.
#

from rp2 import PIO, asm_pio, StateMachine
import uctypes
import random
import array
import time

output_data = array.array('L',[0xffffffff]) # establish a memory location where final data will reside

### State Machine 0
@rp2.asm_pio(in_shiftdir=0, out_shiftdir=1, autopull=True, pull_thresh=1, autopush=True, push_thresh=1)
def bounce():       # move a single bit from TX FIFO to RX FIFO
    wrap_target()

    out(x, 1)       # shift in one bit from OSR to scratch x
    in_(x, 1)       # shift out one bit from scratch x to ISR
    
    wrap()

sm0 = rp2.StateMachine(0, bounce)
### End State Machine 0 Code

### State Machine 1
@rp2.asm_pio(in_shiftdir=0, out_shiftdir=1, autopull=True, pull_thresh=1, autopush=True, push_thresh=32) # set the bit order direction of OSR and ISR as well as autopull threshold to allow a single bit into the state machine while storing these bits in the ISR until full (32-bits) 
def build_bitstream():  # accumulate 32-bits to the RX FIFO one bit at a time from the TX FIFO
    wrap_target()

    set(y, 31)			# set scratch y to 31, this will count down for each bit to be added to ISR

    label("loop")
    pull(block)			# wait (block) for a 32-bit word to be added to the TX FIFO, then move the word to the OSR
    out(x, 1)			# move one bit from OSR to scratch x
    in_(x, 1)			# move one bit from scratch x to OSR
    jmp(y_dec, "loop")	# loop back until 32 bits (bit stream) have filled the ISR
    
    wrap()

sm1 = rp2.StateMachine(1, build_bitstream)	# build array of bit at clock speed
### End State Machine 1 Code

### DMA code
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
dma2_config = dma2.config(read=RXF1_addr, write=uctypes.addressof(output_data), count=1, ctrl=dma2_ctrl, trigger=True)
dma3_config = dma3.config(read=RXF1_addr, write=uctypes.addressof(output_data), count=1, ctrl=dma3_ctrl, trigger=True)

def test(x):
    print("DMA irq test, output_data =", f"{output_data[0]:032b}")   # print output_data to show the end result

dma2.irq(handler=test, hard=False)  # call test() function when dma2 completes transfer of data
dma3.irq(handler=test, hard=False)  # call test() function when dma3 completes transfer of data
### End DMA Code

# bit shift function
def get_bit(value, n):
    return ((value >> n & 1) != 0)

# write input_data one bit at a time to state machine 0
for k in range(0, 4):
    input_data = random.getrandbits(32) # create random 32-bit number
    for i in range(31,-1,-1):
        j = get_bit(input_data, i)
        if j == 1:
            sm0.put(0b1)
        if j == 0:
            sm0.put(0b0)
        time.sleep_us(100)
        #print("write bit to sm0", i)
    #print("write loop", k)
    #print(hex(data1))

#print(hex(uctypes.addressof(output_data)))
#print(bin(output_data[0]))
time.sleep(1)
machine.soft_reset()
