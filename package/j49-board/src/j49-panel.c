// SPDX-License-Identifier: GPL-2.0-only
/* Panel command data: Copyright (C) 2010-2011 Nest, Inc. */
#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/gpio/consumer.h>
#include <linux/regulator/consumer.h>
#include <linux/delay.h>
#include <drm/drm_panel.h>
#include <drm/drm_connector.h>
#include <drm/drm_modes.h>
#include <linux/media-bus-format.h>
struct panel_command {
	u8 command, length;
	u8 data[19];
	u16 delay;
};
static const struct panel_command init_commands[] = {
    {0x36, 1, {0xd0}, 0},
    {0xf0, 2, {0x5a, 0x5a}, 0},
    {0xf1, 2, {0x5a, 0x5a}, 0},
    {0xf2,
     19,
     {0x27, 0x30, 0x03, 0x0a, 0x08, 0x08, 0x08, 0x00, 0x08, 0x08, 0x00, 0x01, 0x00, 0x00, 0x54,
      0x0a, 0x08, 0x0a, 0x08},
     0},
    {0xf4,
     14,
     {0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x66, 0x02, 0x00, 0x52, 0x02},
     0},
    {0xf5, 12, {0x00, 0x5c, 0x5d, 0x00, 0x00, 0x04, 0x00, 0x00, 0x04, 0x00, 0x2a, 0x21}, 0},
    {0xf6, 9, {0x01, 0x00, 0x08, 0x03, 0x01, 0x01, 0x01, 0x00, 0x00}, 0},
    {0xf7, 5, {0x48, 0x81, 0x20, 0x12, 0x01}, 0},
    {0xf8, 2, {0x11, 0x00}, 0},
    {0xf9, 1, {0x17}, 0},
    {0xfa,
     16,
     {0x00, 0x02, 0x00, 0x21, 0x2a, 0x2d, 0x2e, 0x22, 0x28, 0x2f, 0x3c, 0x3f, 0x34, 0x00, 0x00,
      0x00},
     0},
    {0xfb,
     16,
     {0x00, 0x02, 0x34, 0x3f, 0x3c, 0x2f, 0x28, 0x22, 0x2e, 0x2d, 0x2a, 0x21, 0x00, 0x00, 0x00,
      0x00},
     0},
    {0x3a, 1, {0x77}, 0},
    {0x2a, 4, {0x00, 0x00, 0x01, 0x3f}, 0},
    {0x2b, 4, {0x00, 0x00, 0x01, 0x3f}, 0},
    {0x11, 0, {}, 120},
    {0x38, 0, {}, 0},
    {0x29, 0, {}, 10},
};

struct j49_panel {
	struct drm_panel panel;
	struct spi_device *spi;
	struct gpio_desc *reset;
	struct regulator *power;
};
static int command(struct j49_panel *p, const struct panel_command *c)
{
	u16 words[20];
	int i, error;
	words[0] = c->command;
	for (i = 0; i < c->length; i++)
		words[i + 1] = 0x100 | c->data[i];
	error = spi_write(p->spi, words, (c->length + 1) * sizeof(*words));
	if (!error && c->delay)
		msleep(c->delay);
	return error;
}
static int prepare(struct drm_panel *panel)
{
	struct j49_panel *p = container_of(panel, struct j49_panel, panel);
	int error = regulator_enable(p->power), i;
	if (error)
		return error;
	msleep(2);
	gpiod_set_value_cansleep(p->reset, 1);
	msleep(20);
	gpiod_set_value_cansleep(p->reset, 0);
	msleep(120);
	for (i = 0; i < ARRAY_SIZE(init_commands); i++) {
		error = command(p, &init_commands[i]);
		if (error) {
			regulator_disable(p->power);
			return error;
		}
	}
	return 0;
}
static int unprepare(struct drm_panel *panel)
{
	struct j49_panel *p = container_of(panel, struct j49_panel, panel);
	const struct panel_command off = {.command = 0x28}, sleep = {.command = 0x10, .delay = 120};
	command(p, &off);
	command(p, &sleep);
	gpiod_set_value_cansleep(p->reset, 1);
	return regulator_disable(p->power);
}
static int get_modes(struct drm_panel *panel, struct drm_connector *connector)
{
	static const u32 format = MEDIA_BUS_FMT_RGB888_1X24;
	struct drm_display_mode *mode = drm_mode_create(connector->dev);
	if (!mode)
		return -ENOMEM;
	mode->clock = 7180;
	mode->hdisplay = 320;
	mode->hsync_start = 336;
	mode->hsync_end = 338;
	mode->htotal = 354;
	mode->vdisplay = 320;
	mode->vsync_start = 328;
	mode->vsync_end = 330;
	mode->vtotal = 338;
	mode->flags = DRM_MODE_FLAG_NHSYNC | DRM_MODE_FLAG_NVSYNC;
	mode->type = DRM_MODE_TYPE_DRIVER | DRM_MODE_TYPE_PREFERRED;
	drm_mode_set_name(mode);
	drm_mode_probed_add(connector, mode);
	drm_display_info_set_bus_formats(&connector->display_info, &format, 1);
	connector->display_info.bus_flags =
	    DRM_BUS_FLAG_DE_LOW | DRM_BUS_FLAG_PIXDATA_DRIVE_NEGEDGE;
	return 1;
}
static const struct drm_panel_funcs functions = {
    .prepare = prepare, .unprepare = unprepare, .get_modes = get_modes};
static int probe(struct spi_device *spi)
{
	struct j49_panel *p = devm_drm_panel_alloc(&spi->dev, struct j49_panel, panel, &functions,
						   DRM_MODE_CONNECTOR_DPI);
	int error;
	if (IS_ERR(p))
		return PTR_ERR(p);
	p->spi = spi;
	p->reset = devm_gpiod_get(&spi->dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(p->reset))
		return PTR_ERR(p->reset);
	p->power = devm_regulator_get(&spi->dev, "power");
	if (IS_ERR(p->power))
		return PTR_ERR(p->power);
	spi->mode = SPI_MODE_3;
	spi->bits_per_word = 9;
	error = spi_setup(spi);
	if (error)
		return error;
	error = drm_panel_of_backlight(&p->panel);
	if (error)
		return error;
	spi_set_drvdata(spi, p);
	drm_panel_add(&p->panel);
	return 0;
}
static void remove_panel(struct spi_device *spi)
{
	struct j49_panel *p = spi_get_drvdata(spi);
	drm_panel_remove(&p->panel);
}
static const struct of_device_id match[] = {{.compatible = "nestlabs,j49-panel"}, {}};
MODULE_DEVICE_TABLE(of, match);
static const struct spi_device_id ids[] = {{"j49-panel", 0}, {}};
MODULE_DEVICE_TABLE(spi, ids);
static struct spi_driver j49_panel_driver = {
    .probe = probe,
    .remove = remove_panel,
    .id_table = ids,
    .driver = {.name = "j49-panel", .of_match_table = match}};
module_spi_driver(j49_panel_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Nest J49 Tianma TM025ZDZ01 panel");
