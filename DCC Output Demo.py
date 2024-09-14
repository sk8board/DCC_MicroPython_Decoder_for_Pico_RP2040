# Demo of how to use MicroPython for DCC train control with a Pico
# Code provides: Two seconds forward at speed 16 of 28 steps, then two seconds backward at speed 16 of 28 steps.
# GPIO2 is connected to the direction pin of a full H-bridge driver.
# The output terminals of the H-bridge driver are connected to the railroad track rails.
# Original code is from the YouTube channel by Sonny Cruz.
# https://www.youtube.com/watch?v=NSRU2ZYB_7U

import array
from machine import Pin
import rp2
import utime
import struct

#  packet is 64 bits lots of preamble and trailer 1 bits
packet = bytearray(b'\xff\xff\xfe\xff\xff\xff\xff\xff')
address = 0x20  # 32
forward = 0x79  # speed 16 of 28 steps
backward = 0x59 # speed 16 of 28 steps

def init():
    global packet
    packet = bytearray(b'\xff\xff\xfe\xff\xff\xff\xff\xff')

#  demo only use 8 bit addres, 8 bit speed + direction
def assemble_packet(address, speed):
#  bit counts starts at zero
    global packet
    checksum = address ^ speed 
    packet[3] = address              # 3rd byte address 8 bits
    packet[4] = speed >> 1           # 4th byte msb zero separator 7 bits of speed
    packet[5] = checksum >> 2	     # 5th byte rotate 2 zeros from the left
                                     # bit 6 is zero separator
                                     # 6 bits of 5th byte are checksum 
    if not((speed >> 7) & 1):        # check lsb of speed
        packet[5] |= 1 << 7          # set msb of 5th byte to 1
                                     # 7th bit of 5th byte is lsb bit of speed

    temp = checksum << 6
    packet[6] = temp | 0x3f          # 6th byte 2 msb is 2 lsb of checksum


@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW, out_shiftdir=rp2.PIO.SHIFT_LEFT, autopull=True)
def dcc():
    label("bitloop")
    set(pins, 1)           [20] 
    out(x, 1)                  
    jmp(not_x, "do_zero")       
    set(pins, 0)           [21] 
    jmp("bitloop")             
    label("do_zero")
    nop()                  [16]
    set(pins, 0)           [30]
    nop()                  [8]  
 
#  freq = 400_000 2.5us clock cycle
sm = rp2.StateMachine(0, dcc, freq=400000, set_base=Pin(2))
sm.active(1)

while True:
    
    init()
    assemble_packet(address, forward) ## train forward
    word1,word2 = struct.unpack('>II', packet)
    #print(hex(word1))
    #print(hex(word2))
    sm.put(word1)
    sm.put(word2)
    sm.put(word1)
    sm.put(word2)
    sm.put(word1)
    sm.put(word2)
    utime.sleep(2)
    
    init()
    assemble_packet(address, backward) ## train backward
    word1,word2 = struct.unpack('>II', packet)
    #print(hex(word1))
    #print(hex(word2))
    #print(" ")
    sm.put(word1)
    sm.put(word2)
    sm.put(word1)
    sm.put(word2)
    sm.put(word1)
    sm.put(word2)
    utime.sleep(2)
