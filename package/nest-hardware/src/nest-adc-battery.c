// SPDX-License-Identifier: GPL-2.0-only
#include <linux/delay.h>
#include <linux/gpio/consumer.h>
#include <linux/iio/consumer.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/platform_device.h>
#include <linux/power_supply.h>
#include <linux/property.h>

struct nest_battery {
	struct iio_channel *voltage;
	struct gpio_desc *enable;
	struct mutex lock;
	u32 r1, r2, delay;
};
static enum power_supply_property properties[] = {POWER_SUPPLY_PROP_VOLTAGE_NOW};
static int read_voltage(struct power_supply *supply, enum power_supply_property property,
			union power_supply_propval *value)
{
	struct nest_battery *battery = power_supply_get_drvdata(supply);
	int millivolts, error;
	if (property != POWER_SUPPLY_PROP_VOLTAGE_NOW)
		return -EINVAL;
	mutex_lock(&battery->lock);
	gpiod_set_value_cansleep(battery->enable, 1);
	if (battery->delay)
		usleep_range(battery->delay, battery->delay + 20);
	error = iio_read_channel_processed(battery->voltage, &millivolts);
	gpiod_set_value_cansleep(battery->enable, 0);
	mutex_unlock(&battery->lock);
	if (error < 0)
		return error;
	value->intval = div_s64((s64)millivolts * 1000 * (battery->r1 + battery->r2), battery->r2);
	return 0;
}
static const struct power_supply_desc description = {
    .name = "nest-battery",
    .type = POWER_SUPPLY_TYPE_BATTERY,
    .properties = properties,
    .num_properties = ARRAY_SIZE(properties),
    .get_property = read_voltage,
};
static int probe(struct platform_device *device)
{
	struct device *dev = &device->dev;
	struct nest_battery *battery = devm_kzalloc(dev, sizeof(*battery), GFP_KERNEL);
	struct power_supply_config config = {.fwnode = dev_fwnode(dev)};
	struct power_supply *supply;
	if (!battery)
		return -ENOMEM;
	battery->r2 = 1;
	device_property_read_u32(dev, "divider-r1-ohm", &battery->r1);
	device_property_read_u32(dev, "divider-r2-ohm", &battery->r2);
	device_property_read_u32(dev, "delay-us", &battery->delay);
	if (!battery->r2)
		return -EINVAL;
	battery->voltage = devm_iio_channel_get(dev, "voltage");
	if (IS_ERR(battery->voltage))
		return dev_err_probe(dev, PTR_ERR(battery->voltage), "voltage ADC\n");
	battery->enable = devm_gpiod_get_optional(dev, "enable", GPIOD_OUT_LOW);
	if (IS_ERR(battery->enable))
		return dev_err_probe(dev, PTR_ERR(battery->enable), "ADC divider enable\n");
	mutex_init(&battery->lock);
	config.drv_data = battery;
	supply = devm_power_supply_register(dev, &description, &config);
	return PTR_ERR_OR_ZERO(supply);
}
static const struct of_device_id match[] = {{.compatible = "nestlabs,adc-battery"}, {}};
MODULE_DEVICE_TABLE(of, match);
static struct platform_driver nest_battery_driver = {
    .probe = probe, .driver = {.name = "nest-adc-battery", .of_match_table = match}};
module_platform_driver(nest_battery_driver);
MODULE_DESCRIPTION("Nest battery voltage and switched ADC divider");
MODULE_LICENSE("GPL");

MODULE_IMPORT_NS("IIO_CONSUMER");
