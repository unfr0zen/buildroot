// SPDX-License-Identifier: GPL-2.0-only
#include <linux/hwmon-sysfs.h>
#include <linux/hwmon.h>
#include <linux/iio/consumer.h>
#include <linux/module.h>
#include <linux/platform_device.h>

struct nest_madc {
	struct iio_channel *channels;
};
/* TPS65921 prescalers used by the stock twl4030-madc driver. */
static const u8 ratio[16][2] = {
    {1, 1},  {1, 1}, {6, 10}, {6, 10},	 {6, 10}, {6, 10}, {6, 10}, {6, 10},
    {3, 14}, {1, 3}, {1, 1},  {15, 100}, {1, 4},  {1, 1},  {1, 1},  {5, 11},
};
static const char *const labels[16] = {
    "battery_adc",
    "battery_thermistor_adc",
    "adc2",
    "adc3",
    "adc4",
    "adc5",
    "adc6",
    "adc7",
    "vbus",
    "vbkp",
    "charger_current_adc",
    "charger_voltage",
    "main_battery_voltage",
    "adc13",
    "adc14",
    "adc15",
};
static ssize_t voltage_show(struct device *dev, struct device_attribute *attribute, char *buffer)
{
	struct nest_madc *madc = dev_get_drvdata(dev);
	int index = to_sensor_dev_attr(attribute)->index, raw;
	int error = iio_read_channel_raw(&madc->channels[index], &raw);
	if (error < 0)
		return error;
	return sysfs_emit(buffer, "%d\n", raw * 1500 * ratio[index][1] / (1023 * ratio[index][0]));
}
static ssize_t label_show(struct device *dev, struct device_attribute *attribute, char *buffer)
{
	return sysfs_emit(buffer, "%s\n", labels[to_sensor_dev_attr(attribute)->index]);
}
#define CHANNEL(n)                                                                                 \
	static SENSOR_DEVICE_ATTR_RO(in##n##_input, voltage, n);                                   \
	static SENSOR_DEVICE_ATTR_RO(in##n##_label, label, n)
CHANNEL(0);
CHANNEL(1);
CHANNEL(2);
CHANNEL(3);
CHANNEL(4);
CHANNEL(5);
CHANNEL(6);
CHANNEL(7);
CHANNEL(8);
CHANNEL(9);
CHANNEL(10);
CHANNEL(11);
CHANNEL(12);
CHANNEL(13);
CHANNEL(14);
CHANNEL(15);
static SENSOR_DEVICE_ATTR_RO(in0_battery_type, voltage, 0);
static SENSOR_DEVICE_ATTR_RO(in1_battery_temp, voltage, 1);
static SENSOR_DEVICE_ATTR_RO(in8_vbus, voltage, 8);
static SENSOR_DEVICE_ATTR_RO(in9_vbkp, voltage, 9);
static SENSOR_DEVICE_ATTR_RO(in10_battery_charger_current, voltage, 10);
static SENSOR_DEVICE_ATTR_RO(in11_battery_charger_voltage, voltage, 11);
static SENSOR_DEVICE_ATTR_RO(in12_main_battery_voltage, voltage, 12);
#define ATTR(n)                                                                                    \
	&sensor_dev_attr_in##n##_input.dev_attr.attr, &sensor_dev_attr_in##n##_label.dev_attr.attr
static struct attribute *attributes[] = {
    ATTR(0),
    ATTR(1),
    ATTR(2),
    ATTR(3),
    ATTR(4),
    ATTR(5),
    ATTR(6),
    ATTR(7),
    ATTR(8),
    ATTR(9),
    ATTR(10),
    ATTR(11),
    ATTR(12),
    ATTR(13),
    ATTR(14),
    ATTR(15),
    &sensor_dev_attr_in0_battery_type.dev_attr.attr,
    &sensor_dev_attr_in1_battery_temp.dev_attr.attr,
    &sensor_dev_attr_in8_vbus.dev_attr.attr,
    &sensor_dev_attr_in9_vbkp.dev_attr.attr,
    &sensor_dev_attr_in10_battery_charger_current.dev_attr.attr,
    &sensor_dev_attr_in11_battery_charger_voltage.dev_attr.attr,
    &sensor_dev_attr_in12_main_battery_voltage.dev_attr.attr,
    NULL,
};
static const struct attribute_group group = {.attrs = attributes};
static const struct attribute_group *groups[] = {&group, NULL};
static int probe(struct platform_device *device)
{
	struct device *dev = &device->dev, *hwmon;
	struct nest_madc *madc = devm_kzalloc(dev, sizeof(*madc), GFP_KERNEL);
	int count = 0, error;
	if (!madc)
		return -ENOMEM;
	madc->channels = devm_iio_channel_get_all(dev);
	if (IS_ERR(madc->channels))
		return dev_err_probe(dev, PTR_ERR(madc->channels), "MADC channels\n");
	while (madc->channels[count].indio_dev)
		count++;
	if (count != 16)
		return -EINVAL;
	platform_set_drvdata(device, madc);
	error = devm_device_add_group(dev, &group);
	if (error)
		return error;
	hwmon = devm_hwmon_device_register_with_groups(dev, "j49_madc", madc, groups);
	return PTR_ERR_OR_ZERO(hwmon);
}
static const struct of_device_id match[] = {{.compatible = "nestlabs,j49-madc-hwmon"}, {}};
MODULE_DEVICE_TABLE(of, match);
static struct platform_driver nest_madc_driver = {
    .probe = probe, .driver = {.name = "nest-madc-hwmon", .of_match_table = match}};
module_platform_driver(nest_madc_driver);
MODULE_DESCRIPTION("Nest J49 stock MADC voltage readings");
MODULE_LICENSE("GPL");
MODULE_IMPORT_NS("IIO_CONSUMER");
