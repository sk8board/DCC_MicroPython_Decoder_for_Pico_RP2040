# RP2040 DMA Example with PIO
# 
# 1) For loop will feed state machine 0 one bit at a time.
# 2) State machine 0 will pass the bit from TX FIFO to RX FIFO then set the IRQ 0 flag
# 3) State machine 0 interrupt will trigger DMA 0
# 4) DMA 0 will move the bit from state machine 0 TX FIFO to state machine RX FIFO
# 5) State machine 1 will accumulate 32 bits then set the IRQ 1 flag
# 6) State machine 1 interrupt will trigger DMA 1
# 7) DMA 1 will move the 32-bit array to the variable "data"
#
# NOTE: if additional speed is required, then you can change the functions to use Viper code rather than MicroPython code

from rp2 import PIO, asm_pio, StateMachine
import uctypes
import array
import time

data = array.array('L',[0xffffffff]) # memory location where proceced data will reside

### State Machine 0
@rp2.asm_pio(in_shiftdir=0, out_shiftdir=1, autopull=True, pull_thresh=1, autopush=True, push_thresh=1)
def bounce():       # move a single bit from TX FIFO to RX FIFO
    wrap_target()

    out(x, 1)       # shift in one bit from OSR to scratch x
    in_(x, 1)       # shift out one bit from scratch x to ISR
    irq(rel(0))
    
    wrap()

sm0 = rp2.StateMachine(0, bounce)
### End State Machine 0 Code

### State Machine 1
@rp2.asm_pio(in_shiftdir=0, out_shiftdir=1, autopull=True, pull_thresh=1, autopush=False, push_thresh=32) # set the bit order direction of OSR and ISR as well as autopull threshold to allow a single bit into the state machine while storing these bits in the ISR until full (32-bits) 
def build_bitstream():  # accumulate 32-bits to the RX FIFO one bit at a time from the TX FIFO
    wrap_target()

    set(y, 31)			# set scratch y to 31, this will count down for each bit to be added to ISR

    label("loop")
    pull(block)			# wait (block) for a 32-bit word to be added to the TX FIFO, then move the word to the OSR
    out(x, 1)			# move one bit from OSR to scratch x
    in_(x, 1)			# move one bit from scratch x to OSR
    jmp(y_dec, "loop")	# loop back unill 32 bits (bit stream) have filled the ISR
    
    push(noblock)		# move the 32-bits from the ISR to the RX FIFO
    irq(rel(0))			# set IRQ flag which will trigger the IRQ handler to get the 32-bit word from the RX FIFO
    wrap()

sm1 = rp2.StateMachine(1, build_bitstream)	# build array of bit at clock speed
### End State Machine 1 Code

### DMA code
dma0 = rp2.DMA()    # initialize DMA channel, note: this is listed as DMA 0, but the actual DMA channel number can be any channel from 0 to 11 
dma1 = rp2.DMA()    # initialize DMA channel

dma0_ctrl = dma0.pack_ctrl(
    enable = True,      # enable DMA channel
    high_pri = True,    # set DMA bus traffic priority as high
    size = 2,           # Transfer size: 0=byte, 1=half word, 2=word (default: 2)
    inc_read = False,   # do not increment to read address
    inc_write = False,  # do not increment the write address
    ring_size = 0,      # increment size is zero
    ring_sel = False,   # use ring_size
    treq_sel = 4,       # select transfer rate of PIO0 RX FIFO, DREQ_PIO0_RX0
    irq_quiet = True,   # do not generate an interrupt after transfer is complete
    bswap = False,      # do not reverse the order of the word
    sniff_en = False,    # do not allow access to debug
    chain_to = dma0.channel # chain to self
)

dma1_ctrl = dma1.pack_ctrl(
    enable = True,      # enable DMA channel
    high_pri = True,   # set DMA bus traffic priority as high
    size = 2,           # Transfer size: 0=byte, 1=half word, 2=word (default: 2)
    inc_read = False,   # do not increment to read address
    inc_write = False,  # do not increment the write address
    ring_size = 0,      # increment size is zero
    ring_sel = False,   # use ring_size
    treq_sel = 5,       # select transfer rate of PIO0 RX FIFO, DREQ_PIO0_RX1
    irq_quiet = False,   # do not generate an interrupt after transfer is complete
    bswap = False,      # do not reverse the order of the word
    sniff_en = False,    # do not allow access to debug
    chain_to = dma1.channel # chain to self
)

def config_dma0(read0, write0, dma0_ctrl):
    dma0_config = dma0.config(read=read0, write=write0, count=1, ctrl=dma0_ctrl, trigger=True)

def config_dma1(read1, write1, dma1_ctrl):
    dma1_config = dma1.config(read=read1, write=uctypes.addressof(write1), count=1, ctrl=dma1_ctrl, trigger=True)

RXF0_addr = const(0x50200020)   # address of RX FIFO register for State Machine 0
TXF1_addr = const(0x50200014)   # address of TX FIFO register for State Machine 1
RXF1_addr = const(0x50200024)   # address of RX FIFO register for State Machine 1

def trigger_dma0(sm0):
    config_dma0(RXF0_addr,TXF1_addr,dma0_ctrl)

def trigger_dma1(sm1):
    config_dma1(RXF1_addr,data,dma1_ctrl)
    print(bin(data[0])) # view the 32-bit array to see if it matched test_bitstream that is declared below

sm0.irq(trigger_dma0, trigger=1, hard=True) # true = immedieate execution
sm1.irq(trigger_dma1, trigger=1, hard=False)    # false = scheduled execution

sm0.active(1)
sm1.active(1)
dma0.active(1)
dma1.active(1)

def test(x):
    print("DMA irq test, ", bin(data[0])) # verify interrupt from DMA

dma1.irq(handler=test, hard=False) # interrupt from state machine
### End DMA Code

test_bitstream = 0b111111111101010010010110001011100

# bit shift function
def get_bit(value, n):
    return ((value >> n & 1) != 0)

# write test_bitstream one bit at a time to state machine 0
for k in range(0, 4):
    for i in range(31,-1,-1):
        j = get_bit(test_bitstream, i)
        if j == 1:
            sm0.put(0b1)
        if j == 0:
            sm0.put(0b0)
        time.sleep_us(100)
        #print("write bit to sm0", i)
    print("write loop", k)
    #print(hex(data1))

print(hex(uctypes.addressof(data)))
print(bin(data[0]))
time.sleep(1)
sm0.active(0)
sm1.active(0)
dma0.active(0)
dma1.active(0)
dma0.close()
dma1.close()
machine.soft_reset()
