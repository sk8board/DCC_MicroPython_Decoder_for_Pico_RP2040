#! /bin/bash

# Display linux messages filtered with "usb"
# Connect the USB device then run this command to deterime the device name of the USB device

sudo dmesg | grep -i usb

$SHELL

# Example:
```
home14@home14:~$ sudo dmesg | grep -i usb
[ 5425.404493] usb 1-1: USB disconnect, device number 5
[ 5440.892664] usb 1-1: new full-speed USB device number 6 using xhci_hcd
[ 5441.042700] usb 1-1: New USB device found, idVendor=2e8a, idProduct=0005, bcdDevice= 1.00
[ 5441.042715] usb 1-1: New USB device strings: Mfr=1, Product=2, SerialNumber=3
[ 5441.042722] usb 1-1: Product: Board in FS mode
[ 5441.042728] usb 1-1: Manufacturer: MicroPython
[ 5441.042733] usb 1-1: SerialNumber: e6613008e343bd2e
[ 5441.045138] cdc_acm 1-1:1.0: ttyACM0: USB ACM device
```

