// SPDX-License-Identifier: GPL-2.0-only
#include <linux/gpio/consumer.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/property.h>

struct nest_line {
	struct device_attribute attribute;
	struct attribute_group group;
	struct attribute *attributes[2];
	struct gpio_desc *gpio;
};
static ssize_t show(struct device *device, struct device_attribute *attribute, char *buffer)
{
	struct nest_line *line = container_of(attribute, struct nest_line, attribute);
	int value = gpiod_get_raw_value_cansleep(line->gpio);
	return value < 0 ? value : sysfs_emit(buffer, "%d\n", value);
}
static ssize_t store(struct device *device, struct device_attribute *attribute, const char *buffer,
		     size_t size)
{
	struct nest_line *line = container_of(attribute, struct nest_line, attribute);
	bool value;
	int error = kstrtobool(buffer, &value);
	if (error)
		return error;
	gpiod_set_raw_value_cansleep(line->gpio, value);
	return size;
}
static int probe(struct platform_device *device)
{
	struct device *dev = &device->dev;
	int inputs = device_property_string_array_count(dev, "input-names");
	int outputs = device_property_string_array_count(dev, "output-names");
	struct nest_line *lines;
	int index = 0;
	inputs = max(inputs, 0);
	outputs = max(outputs, 0);
	if (!inputs && !outputs)
		return -ENODEV;
	lines = devm_kcalloc(dev, inputs + outputs, sizeof(*lines), GFP_KERNEL);
	if (!lines)
		return -ENOMEM;
	for (int direction = 0; direction < 2; direction++) {
		bool output = direction == 1;
		int count = output ? outputs : inputs;
		const char *property = output ? "output-names" : "input-names";
		const char **names = devm_kcalloc(dev, count, sizeof(*names), GFP_KERNEL);
		if (!count)
			continue;
		if (!names)
			return -ENOMEM;
		int error = device_property_read_string_array(dev, property, names, count);
		if (error < 0)
			return error;
		for (int i = 0; i < count; i++, index++) {
			struct nest_line *line = &lines[index];
			line->gpio = devm_gpiod_get_index(dev, output ? "output" : "input", i,
							  output ? GPIOD_OUT_LOW : GPIOD_IN);
			if (IS_ERR(line->gpio))
				return dev_err_probe(dev, PTR_ERR(line->gpio), "%s GPIO\n",
						     names[i]);
			gpiod_set_consumer_name(line->gpio, names[i]);
			sysfs_attr_init(&line->attribute.attr);
			line->attribute.attr.name = "value";
			line->attribute.attr.mode = output ? 0644 : 0444;
			line->attribute.show = show;
			line->attribute.store = output ? store : NULL;
			line->attributes[0] = &line->attribute.attr;
			line->group.name = names[i];
			line->group.attrs = line->attributes;
			error = devm_device_add_group(dev, &line->group);
			if (error)
				return error;
		}
	}
	return 0;
}
static const struct of_device_id match[] = {{.compatible = "nestlabs,gpio-exporter"}, {}};
MODULE_DEVICE_TABLE(of, match);
static struct platform_driver nest_gpio_driver = {
    .probe = probe, .driver = {.name = "nest-gpio-exporter", .of_match_table = match}};
module_platform_driver(nest_gpio_driver);
MODULE_DESCRIPTION("Named Nest board GPIO inputs and outputs");
MODULE_LICENSE("GPL");
