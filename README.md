# DCC MicroPython Decoder for Pico RP2040

Work In Progress

This is software decodes DCC model train serial communication to obtain the state of function buttons F1-F12, which can be utilized for layout automation.

The intent is to use this software with a Raspberry Pi Pico or WaveShare RP2040-Zero to easily program and actuate signals and gates on a model train layout. Simply upload the DCC.py and main.py files to the Pico, then easily modify the main.py file as needed for your layout.

![image](https://github.com/user-attachments/assets/402a8c4d-a92e-432f-b2a8-601fd274922b)

# How to use

There are five key parts to using this DCC decoder.

1) `import DCC`
   
   You must import the DCC module for the decoder to operate
   
2) `my_dcc_decoder = DCC.pin_addr(16,1)`
   
   You must communicate the following information to the DCC module:
   
   a) The GPIO pin number that is connected to the DCC square wave signal
       from the tracks. Note: the railroad tracks must not be directly
       connected to the GPIO pin, since the track voltage it too high
       for the GPIO pin. A signal conditioner circuit must be placed
       between the tracks and the GPIO pin to prevent damage to the
       Raspberry Pi Pico.
   
   b) The address of the decoder. The address must be from 1 to 9999.
   
   The example above uses GPIO pin 16 and an address of 1
   
3) `DCC.f_btn(3)`
   
   This function returns the state of the function button number
   that is provided.

    The example above uses function button 3 to operate an LED.
   
4) `x = DCC.throttle_dir`

    This provides the throttle direction. 1 or True indicates forward while
   0 or False idicates reverse.
   
5) `y = DCC.throttle_pos`

    This provides the throttle position. NMRA allows the throttle
   position to be configured in the roster as 28-step resolution
   or 127-step resolution. `DCC.throttle_pos` will return
   either 0 to 28 or 0 to 127 depending on the roster config.

For reference, this code was developed using MicroPython version v1.23

# Hardware

Note: appropriate circuitry is needed between the Pico and the railroad tracks to protect the Pico from damage. Below is a preliminary design of a DCC decoder for layout applications. See the hardware folder for more information.

![image](https://github.com/sk8board/DCC_MicroPython_Decoder_for_Pico_RP2040_and_Pico_2_RP2340/blob/main/hardware/RP2040%20DCC%20Encoder_bb.png)
![image](https://github.com/sk8board/DCC_MicroPython_Decoder_for_Pico_RP2040_and_Pico_2_RP2340/blob/main/hardware/RP2040%20DCC%20Encoder_sc.png)
