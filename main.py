from m5stack import *
from m5ui import *
from uiflow import *
import machine
import i2c_bus

setScreenColor(0x222222)

label1 = M5TextBox(62, 48, "Text", lcd.FONT_Default, 0xFFFFFF, rotate=0)

adc0 = machine.ADC(35)
adc0.width(machine.ADC.WIDTH_9BIT)
adc0.atten(machine.ADC.ATTN_0DB)

i2c_l = i2c_bus.get(i2c_bus.PORTA)
i2cAddr = (0x22 >> 1)

def register_short(register, value=None, buf=bytearray(2)):
  if value is None:
    i2c_l.readfrom_mem_into(i2cAddr, register, buf)
    return buf[0]*256 + buf[1]
  buf[0] = (value & 0xff00) >> 8
  buf[1] = value & 0x00ff
  i2c_l.writeto_mem(i2cAddr, register, buf)

def write_u16(address, val):
  return register_short(address, val)

def read_u16(address):
  return register_short(address)

def getRegister(address):
  return read_u16(address)

def updateRegister(reg, mask, value):
  write_u16(reg, (read_u16(reg) & ~mask | value))

def lowByte(byte):
  return byte & 0x0F

def highByte(byte):
  return byte >> 4

RDA5807M_BandLowerLimits = [8700, 7600, 7600, 6500, 5000]
RDA5807M_BandHigherLimits = [10800, 9100, 10800, 7600, 6500]
RDA5807M_ChannelSpacings = [100, 200, 50, 25]
RDA5807M_BAND_WEST = (0x0 << 2)
RDA5807M_BAND_JAPAN = (0x1 << 2)
RDA5807M_BAND_WORLD = (0x2 << 2)
RDA5807M_BAND_EAST = (0x3 << 2)
RDA5807M_BAND_MASK = 0x000C
RDA5807M_BAND_SHIFT = 2
RDA5807M_REG_CHIPID = 0x00
RDA5807M_REG_CONFIG = 0x02
RDA5807M_REG_TUNING = 0x03
RDA5807M_REG_VOLUME = 0x05
RDA5807M_REG_BLEND = 0x07
RDA5807M_REG_STATUS = 0x0A
RDA5807M_REG_RSSI = 0x0B
RDA5807M_FLG_ENABLE = 0x0001
RDA5807M_FLG_SEEKUP = 0x0200
RDA5807M_FLG_SEEK = 0x0100
RDA5807M_FLG_EASTBAND65M = 0x0200
RDA5807M_FLG_SKMODE = 0x0080
RDA5807M_FLG_RDS = 0x0008
RDA5807P_FLG_I2SSLAVE = 0x1000
RDA5807M_FLG_DHIZ = 0x8000
RDA5807M_FLG_NEW = 0x0004
RDA5807M_FLG_DMUTE = 0x4000
RDA5807M_STATUS_STC = 0x4000
RDA5807M_VOLUME_MASK = 0x000F
RDA5807M_SPACE_MASK = 0x0003
RDA5807M_READCHAN_MASK = 0x03FF
RDA5807M_RSSI_MASK = 0xFE00
RDA5807M_RSSI_SHIFT = 9
MUTE = False

#lcd.clear()
#lcd.print(volume, 0, 0, 0xffffff)

def seekDown():
  updateRegister(RDA5807M_REG_CONFIG, (RDA5807M_FLG_SEEKUP | RDA5807M_FLG_SEEK | RDA5807M_FLG_SKMODE), (RDA5807M_REG_CHIPID | RDA5807M_FLG_SEEK | RDA5807M_FLG_SEEK | RDA5807M_FLG_SKMODE))

def seekUp():
  updateRegister(RDA5807M_REG_CONFIG, (RDA5807M_FLG_SEEKUP | RDA5807M_FLG_SEEK | RDA5807M_FLG_SKMODE), (RDA5807M_FLG_SEEKUP | RDA5807M_FLG_SEEK | RDA5807M_FLG_SKMODE))

def mute(m):
  global MUTE
  if m == True:
    updateRegister(RDA5807M_REG_CONFIG, RDA5807M_FLG_DMUTE, 0x00)
    MUTE = True
  else:
    updateRegister(RDA5807M_REG_CONFIG, RDA5807M_FLG_DMUTE, RDA5807M_FLG_DMUTE)
    MUTE = False

def volumeDown():
  volume = read_u16(RDA5807M_REG_VOLUME) & RDA5807M_VOLUME_MASK
  volume = volume - 1 if volume - 1 > -1 else 0
  updateRegister(RDA5807M_REG_VOLUME, RDA5807M_VOLUME_MASK, volume)
  if volume == 0:
    mute(True)
  return volume

def volumeUp():
  volume = read_u16(RDA5807M_REG_VOLUME) & RDA5807M_VOLUME_MASK
  volume = volume + 1 if volume + 1 <= 15 else 15
  updateRegister(RDA5807M_REG_VOLUME, RDA5807M_VOLUME_MASK, volume)
  if MUTE == True:
    mute(False)
  return volume

def getBandAndSpacing():
  band = read_u16(RDA5807M_REG_TUNING) & (RDA5807M_BAND_MASK | RDA5807M_SPACE_MASK)
  space = band & RDA5807M_SPACE_MASK
  if (band & RDA5807M_BAND_MASK == RDA5807M_BAND_EAST) and not (read_u16(RDA5807M_REG_BLEND) & RDA5807M_FLG_EASTBAND65M):
    band = (band >> RDA5807M_BAND_SHIFT) + 1
  else:
    band = band >> RDA5807M_BAND_SHIFT
  return space, band

def getFrequency():
  space, band = getBandAndSpacing()
  return int((RDA5807M_BandLowerLimits[lowByte(space)] + (read_u16(RDA5807M_REG_STATUS) & RDA5807M_READCHAN_MASK) * RDA5807M_ChannelSpacings[highByte(band)] / 10))

def getRSSI():
  return (read_u16(RDA5807M_REG_RSSI) & RDA5807M_RSSI_MASK) >> RDA5807M_RSSI_SHIFT

write_u16(RDA5807M_REG_CONFIG, (RDA5807M_FLG_DHIZ | RDA5807M_STATUS_STC | RDA5807P_FLG_I2SSLAVE | RDA5807M_FLG_SEEKUP | RDA5807M_FLG_RDS | RDA5807M_FLG_NEW | RDA5807M_FLG_ENABLE))
updateRegister(RDA5807M_REG_TUNING, RDA5807M_BAND_MASK, RDA5807M_BAND_WEST)

def buttonA_pressed():
  seekDown()

def buttonB_pressed():
  global MUTE
  mute(not MUTE)

def buttonC_pressed():
  seekUp()

btnA.wasPressed(callback=buttonA_pressed)
btnB.wasPressed(callback=buttonB_pressed)
btnC.wasPressed(callback=buttonC_pressed)

lastTime = 0

seekUp()

while True:
  # if time.ticks_us() - lastTime >= 2000000:
  # lastTime = time.ticks_us()
  # rssi = getRSSI()
  # label1.setText(str(getFrequency() / 100))
  # label1.setText(str(adc0.read()))
  wait(0.001)
