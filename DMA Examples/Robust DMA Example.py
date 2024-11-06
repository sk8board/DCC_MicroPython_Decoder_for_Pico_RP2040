###
# This is an example of two common DMA use cases for RP2040
#
# 1) The first use case shows how to configure dma0 and dma1
# in parallel as described in the RP2040 Datasheet as "ping-pong".
# dma 0 and dma1 will perform the same work, but alternate their
# time of work by triggering the other dma after completing
# a data transfer.
#
# 2) The second use case shows how to configure dma2 and dma3
# in series, where dma2 performs the data transfer and
# dma3 writes to dma2 register as a restart trigger to dma2.
#
# 3) dma2 uses an interrupt handler to timely print data
# in the serial monitor.
#
# This example will print three rows of 32-bit random numbers
#
# This was made using MicroPython version v1.23
###

import rp2, time, random, array, uctypes

data = array.array('L', [0,0])

# generate random bit then put the bit into State Machine 0
def random_bits():
    for i in range (103):
        x = random.getrandbits(1)
        sm0.put(x)
        time.sleep_us(100)
######

# State Machine 0 passes the bit to DMA 0 or DMA 1
@rp2.asm_pio(set_init=rp2.PIO.IN_HIGH, in_shiftdir=0, out_shiftdir=1, autopull=True, pull_thresh=1, autopush=True, push_thresh=1)    
def pass_bit():
    wrap_target()
    out(x, 1)
    in_(x, 1)
    wrap()

sm0 = rp2.StateMachine(0, pass_bit)
sm0.active(1)
######

# DMA 0 and DMA 1 are chained together in parallel (ping-pong per RP2040 datasheet) 
# DMA 0 and DMA 1 alternate transfer of a bit from State Machine 0 to State Machine 1
# After DMA 0 completes the transfer, DMA 0 will trigger DMA 1 using the "chain_to" parameter
# Then DMA 1 does the same to DMA 0. These two DMA's alternate their data transfer and trigger
# responsibilities.
dma0 = rp2.DMA()
dma1 = rp2.DMA()

dma0_ctrl = dma0.pack_ctrl(
    enable = True,          # enable DMA channel
    high_pri = True,        # set DMA bus traffic priority as high
    size = 0,               # Transfer size: 0=byte, 1=half word, 2=word (default: 2)
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
    size = 0,               # Transfer size: 0=byte, 1=half word, 2=word (default: 2)
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
dma0.active(1)  # set DMA channel active
dma1.active(1)  # set DMA channel active

RXF0_addr = const(0x50200020)   # address of RX FIFO register for State Machine 0, see RP2040 datasheet
TXF1_addr = const(0x50200014)   # address of TX FIFO register for State Machine 1

dma0_config = dma0.config(read=RXF0_addr,	# read the RX FIFO of State Machine 0
                          write=TXF1_addr,	# write to the TX FIFO of State Machine 1
                          count=1,			# transfer one byte
                          ctrl=dma0_ctrl,
                          trigger=False)

dma1_config = dma1.config(read=RXF0_addr,	# read the RX FIFO of State Machine 0
                          write=TXF1_addr,	# write to the TX FIFO of State Machine 1
                          count=1,			# transfer one byte
                          ctrl=dma1_ctrl,
                          trigger=False)
######


# State Machine 1 will accumulate bits from State Machine 0 to build a 32-bit number
# The first 32-bit number is comprised of all random bits
# The second 32-bits number only has random bits at three least significant bits
@rp2.asm_pio(in_shiftdir=0, out_shiftdir=1, autopull=True, pull_thresh=1, autopush=False, push_thresh=32)  
def build_bitstream():
    wrap_target()

    set(y, 31)			    # set scratch y to 31, this will count down for each bit to be added to ISR

    label("loop_1")
    pull(block)			    # wait (block) for a 32-bit word to be added to the TX FIFO, then move the word to the OSR
    out(x, 1)			    # move one bit from OSR to scratch x
    in_(x, 1)			    # move one bit from scratch x to ISR
    jmp(y_dec, "loop_1")	# loop back until 32 bits (bit stream) have filled the ISR
    
    push(noblock)		    # move the 32-bits from the ISR to the RX FIFO

    set(y, 2)			    # set scratch y to 2, this will count down for each bit to be added to ISR

    label("loop_2")
    pull(block)			    # wait (block) for a 3-bit word to be added to the TX FIFO, then move the word to the OSR
    out(x, 1)			    # move one bit from OSR to scratch x
    in_(x, 1)			    # move one bit from scratch x to ISR
    jmp(y_dec, "loop_2")	# loop back until 3 bits (bit stream) have filled the ISR
    
    push(noblock)		    # move the 32-bits from the ISR to the RX FIFO

    wrap()

sm1 = rp2.StateMachine(1, build_bitstream)	# build array of bits
sm1.active(1) 
#######


# DMA 2 is chained to DMA 3 in series
# DMA 2 transfers two 32-bit numbers from State Machine 1 to a data array in memory
# DMA 3 writes to DMA 2 register as a restart trigger for DMA 2
dma2 = rp2.DMA()    # initialize DMA channel
dma3 = rp2.DMA()  

dma2_ctrl = array.array('L',[0])	# create array to store dma2_ctrl in memory for setup of dma3
dma2_ctrl[0] = dma2.pack_ctrl(
    enable = True,          # enable DMA channel
    high_pri = True,        # set DMA bus traffic priority as high
    size = 2,               # Transfer size: 0=byte, 1=half word, 2=word (default: 2)
    inc_read = False,       # do not increment to read address
    inc_write = True,      	# increment the write address
    ring_size = 3,          # total transfer is two 32-bit integers, which is a total of 8 bytes (2^3)
    ring_sel = True,       	# apply to write address
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
    ring_sel = True,       	# apply to write address
    treq_sel = 0x3f,        # select transfer rate of unlimited due to transfer from memory to register
    irq_quiet = False,      # do not generate an interrupt after transfer is complete
    bswap = False,          # do not reverse the order of the word
    sniff_en = False,       # do not allow access to debug
    chain_to = dma3.channel # chain to self
)

dma2.active(1)  # set DMA channel active
dma3.active(1)

RXF1_addr = const(0x50200024)   # address of RX FIFO register for State Machine 1
dma2_ctrl_addr = uctypes.addressof(dma2_ctrl) # address of dma2_ctrl

dma2_config = dma2.config(read=RXF1_addr,				# read the RX FIFO of State Machine 1
                          write=uctypes.addressof(data),# write to the address of data array
                          count=2,						# transfer two 32-bit numbers before trigger dma3
                          ctrl=dma2_ctrl[0],
                          trigger=False)

dma3_config = dma3.config(read=dma2_ctrl_addr,			# read dma2_ctrl from the address of dma2_ctrl
                          write=dma2.registers[3:3],	# write to the fourth register of dma2 (trigger register)
                          count=1,						# transfer one 32-bit number
                          ctrl=dma3_ctrl,
                          trigger=False)

def dma2_irq_handler(dma2):
    print(f"{data[0]:032b}",f"{data[1]:032b}")

dma2.irq(handler=dma2_irq_handler, hard=False)  # dma2 will trigger the handler after dma2 completes two transfers (count=2)
######

# start random bits sent to State Machine 0
print("            data[0]         ","               data[1]")
random_bits()

# close DMA's so RP2040 can run this again without needing a hard reset
sm0.active(0)
sm1.active(0)
dma0.active(0)
dma1.active(0)
dma2.active(0)
dma3.active(0)
dma0.close()
dma1.close()
dma2.close()
dma3.close()
