# DCC MicroPython Decoder for Pico RP2040

Work In Progress

This is software decodes DCC model train serial communication to obtain the state of function buttons F1-F12, which can be utilized for layout automation.

The intent is to use this software with a Raspberry Pi Pico or WaveShare RP2040-Zero to easily program and actuate signals and gates on a model train layout. Simply upload the DCC.py and main.py files to the Pico, then easily modify the main.py file as needed for your layout.

![image](https://github.com/user-attachments/assets/402a8c4d-a92e-432f-b2a8-601fd274922b)

For reference, this code was developed using MicroPython version v1.23

# Hardware

Note: appropriate circuitry is needed between the Pico and the railroad tracks to protect the Pico from damage. Below is a preliminary design of a DCC decoder for layout applications. See the hardware folder for more information.

![image](https://github.com/sk8board/DCC_MicroPython_Decoder_for_Pico_RP2040_and_Pico_2_RP2340/blob/main/hardware/RP2040%20DCC%20Encoder_bb.png)
![image](https://github.com/sk8board/DCC_MicroPython_Decoder_for_Pico_RP2040_and_Pico_2_RP2340/blob/main/hardware/RP2040%20DCC%20Encoder_sc.png)
