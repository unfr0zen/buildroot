// SPDX-License-Identifier: GPL-2.0-only
#include <linux/module.h>
#include <linux/i2c.h>
#include <linux/backlight.h>
#include <linux/gpio/consumer.h>

struct j49_backlight {
	struct i2c_client *client;
	struct gpio_desc *enable;
};
static int update(struct backlight_device *backlight)
{
	struct j49_backlight *p = bl_get_data(backlight);
	return i2c_smbus_write_byte_data(p->client, 0xa0, backlight_get_brightness(backlight));
}
static const struct backlight_ops operations = {.options = BL_CORE_SUSPENDRESUME,
						.update_status = update};
static int probe(struct i2c_client *client)
{
	struct j49_backlight *p = devm_kzalloc(&client->dev, sizeof(*p), GFP_KERNEL);
	struct backlight_device *backlight;
	struct backlight_properties props = {.type = BACKLIGHT_RAW,
					     .max_brightness = 120,
					     .brightness = 108,
					     .power = BACKLIGHT_POWER_OFF};
	int error;
	if (!p)
		return -ENOMEM;
	p->client = client;
	p->enable = devm_gpiod_get(&client->dev, "enable", GPIOD_OUT_HIGH);
	if (IS_ERR(p->enable))
		return PTR_ERR(p->enable);
	error = i2c_smbus_write_byte_data(client, 0x10, 0x1d);
	if (!error)
		error = i2c_smbus_write_byte_data(client, 0x30, 0x2d);
	if (!error)
		error = i2c_smbus_write_byte_data(client, 0xa0, 0);
	if (error)
		return error;
	backlight = devm_backlight_device_register(&client->dev, "j49-backlight", &client->dev, p,
						   &operations, &props);
	if (IS_ERR(backlight))
		return PTR_ERR(backlight);
	i2c_set_clientdata(client, p);
	return 0;
}
static void remove_backlight(struct i2c_client *client)
{
	struct j49_backlight *p = i2c_get_clientdata(client);
	gpiod_set_value_cansleep(p->enable, 0);
}
static const struct of_device_id match[] = {{.compatible = "nestlabs,j49-backlight"}, {}};
MODULE_DEVICE_TABLE(of, match);
static const struct i2c_device_id ids[] = {{"j49-backlight", 0}, {}};
MODULE_DEVICE_TABLE(i2c, ids);
static struct i2c_driver j49_backlight_driver = {
    .probe = probe,
    .remove = remove_backlight,
    .id_table = ids,
    .driver = {.name = "j49-backlight", .of_match_table = match}};
module_i2c_driver(j49_backlight_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Nest J49 LM3530 backlight");
