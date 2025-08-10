# st7789.py - minimal ST7789 driver (RGB565)
import time

CHUNK = 4096

class ST7789:
    BLACK = 0x0000
    WHITE = 0xFFFF
    def __init__(self, spi, width, height, cs, dc, reset=None, backlight=None, rotation=0):
        self.spi = spi
        self.width = width
        self.height = height
        self.cs = cs
        self.dc = dc
        self.reset = reset
        self.backlight = backlight
        self.rotation = rotation

        # configure pins (Pin objects are passed in)
        try:
            self.cs.init(self.cs.OUT, value=1)
            self.dc.init(self.dc.OUT, value=0)
            if self.reset:
                self.reset.init(self.reset.OUT, value=1)
            if self.backlight:
                self.backlight.init(self.backlight.OUT, value=1)
        except Exception:
            # some firmwares don't have .init; pins already configured
            pass

    def _cs_low(self):
        self.cs.value(0)
    def _cs_high(self):
        self.cs.value(1)
    def write_cmd(self, cmd):
        self._cs_low()
        self.dc.value(0)
        self.spi.write(bytes([cmd]))
        self._cs_high()

    def write_data(self, data):
        self._cs_low()
        self.dc.value(1)
        # send in chunks to avoid memory/SPI driver limits
        for i in range(0, len(data), CHUNK):
            self.spi.write(data[i:i+CHUNK])
        self._cs_high()

    def reset_pulse(self):
        if self.reset:
            self.reset.value(0)
            time.sleep_ms(50)
            self.reset.value(1)
            time.sleep_ms(50)

    def init(self):
        self.reset_pulse()
        # Minimal init sequence
        self.write_cmd(0x01)  # SWRESET
        time.sleep_ms(150)
        self.write_cmd(0x11)  # SLPOUT
        time.sleep_ms(120)

        # Pixel format 16-bit
        self.write_cmd(0x3A)
        self.write_data(bytes([0x55]))

        # MADCTL (memory access) - orientation default
        self.write_cmd(0x36)
        # common default; you can change depending on rotation
        self.write_data(bytes([0x00]))

        # Turn on display
        self.write_cmd(0x29)
        time.sleep_ms(50)

    def set_window(self, x0, y0, x1, y1):
        # Column address set
        self.write_cmd(0x2A)
        self.write_data(bytes([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))
        # Row address set
        self.write_cmd(0x2B)
        self.write_data(bytes([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))
        # Memory write
        self.write_cmd(0x2C)

    def fill(self, color):
        # write by rows to limit memory
        hi = color >> 8
        lo = color & 0xFF
        row = bytes([hi, lo]) * self.width
        self.set_window(0, 0, self.width - 1, self.height - 1)
        # disable cs/dc toggling inside write_data to optimize
        self._cs_low()
        self.dc.value(1)
        for y in range(self.height):
            for i in range(0, len(row), CHUNK):
                self.spi.write(row[i:i+CHUNK])
        self._cs_high()

    def blit_buffer(self, buffer):
        # buffer must be width*height*2 bytes in RGB565 order
        self.set_window(0, 0, self.width - 1, self.height - 1)
        self.write_data(buffer)

    def pixel(self, x, y, color):
        self.set_window(x, y, x, y)
        self.write_data(bytes([color >> 8, color & 0xFF]))
