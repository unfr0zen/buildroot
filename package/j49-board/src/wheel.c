// SPDX-License-Identifier: GPL-2.0-only
#include <fcntl.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <linux/uinput.h>
#include <stdio.h>
#include <stdint.h>
#include <sys/ioctl.h>
#include <unistd.h>

static int sensor_read(int fd, unsigned char reg)
{
	union i2c_smbus_data data;
	struct i2c_smbus_ioctl_data request = {.read_write = I2C_SMBUS_READ,
					       .command = reg,
					       .size = I2C_SMBUS_BYTE_DATA,
					       .data = &data};
	return ioctl(fd, I2C_SMBUS, &request) < 0 ? -1 : data.byte;
}
static int sensor_write(int fd, unsigned char reg, unsigned char value)
{
	union i2c_smbus_data data = {.byte = value};
	struct i2c_smbus_ioctl_data request = {.read_write = I2C_SMBUS_WRITE,
					       .command = reg,
					       .size = I2C_SMBUS_BYTE_DATA,
					       .data = &data};
	return ioctl(fd, I2C_SMBUS, &request);
}
int main(void)
{
	int sensor = open("/dev/i2c-1", O_RDWR);
	if (sensor < 0 || ioctl(sensor, I2C_SLAVE, 0x57))
		return 1;
	if (sensor_read(sensor, 0) != 0x83) {
		fprintf(stderr, "ADBS-A320 not detected\n");
		return 1;
	}
	int resolution = sensor_read(sensor, 0x62), speed = sensor_read(sensor, 0x63);
	if (resolution < 0 || speed < 0 || sensor_write(sensor, 0x62, (resolution & ~0x38) | 8) ||
	    sensor_write(sensor, 0x63, (speed | 2) & ~1))
		return 1;
	int input = open("/dev/uinput", O_WRONLY);
	struct uinput_setup setup = {.id = {.bustype = BUS_I2C}, .name = "J49 wheel"};
	if (input < 0 || ioctl(input, UI_SET_EVBIT, EV_REL) ||
	    ioctl(input, UI_SET_RELBIT, REL_DIAL) || ioctl(input, UI_DEV_SETUP, &setup) ||
	    ioctl(input, UI_DEV_CREATE))
		return 1;
	for (;;) {
		int motion = sensor_read(sensor, 2);
		if (motion < 0)
			return 1;
		if (motion & 0x80) {
			int x = sensor_read(sensor, 3), y = sensor_read(sensor, 4);
			if (x < 0 || y < 0)
				return 1;
			if (y) {
				struct input_event events[2] = {
				    {.type = EV_REL, .code = REL_DIAL, .value = (int8_t)y},
				    {.type = EV_SYN, .code = SYN_REPORT}};
				if (write(input, events, sizeof(events)) != sizeof(events))
					return 1;
			}
		}
		usleep(16667);
	}
}
