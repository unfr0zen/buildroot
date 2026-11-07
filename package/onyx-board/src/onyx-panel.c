// SPDX-License-Identifier: GPL-2.0-only
/* Panel command data: Copyright (C) 2010-2011 Nest, Inc. */
#include <linux/module.h>
#include <linux/spi/spi.h>
#include <linux/gpio/consumer.h>
#include <linux/delay.h>
#include <drm/drm_panel.h>
#include <drm/drm_connector.h>
#include <drm/drm_modes.h>
#include <linux/media-bus-format.h>
struct panel_command {
	u8 command, length;
	u8 data[24];
	u16 delay;
};
static const struct panel_command init_commands[] = {
	{0x01, 0, {}, 85},
	{0xb0, 1, {0x04}, 0},
	{0xb3, 4, {0x02, 0x00, 0x00, 0x01}, 0},
	{0xb4, 1, {0x00}, 0},
	{0xc0, 8, {0x13, 0x3f, 0x40, 0x10, 0x00, 0x01, 0x00, 0x55}, 0},
	{0xc1, 5, {0x13, 0x29, 0x08, 0x08, 0x00}, 0},
	{0xc4, 4, {0x57, 0x00, 0x05, 0x03}, 0},
	{0xc6, 1, {0x1c}, 0},
	{0xc8, 24, {0x05, 0x0d, 0x1a, 0x28, 0x3c, 0x51, 0x3b, 0x31, 0x2b, 0x27, 0x23, 0x13, 0x05, 0x0d, 0x1a, 0x28, 0x3c, 0x51, 0x3b, 0x31, 0x2b, 0x27, 0x23, 0x13}, 0},
	{0xc9, 24, {0x05, 0x0d, 0x1a, 0x28, 0x3c, 0x51, 0x3b, 0x31, 0x2b, 0x27, 0x23, 0x13, 0x05, 0x0d, 0x1a, 0x28, 0x3c, 0x51, 0x3b, 0x31, 0x2b, 0x27, 0x23, 0x13}, 0},
	{0xca, 24, {0x05, 0x0d, 0x1a, 0x28, 0x3c, 0x51, 0x3b, 0x31, 0x2b, 0x27, 0x23, 0x13, 0x05, 0x0d, 0x1a, 0x28, 0x3c, 0x51, 0x3b, 0x31, 0x2b, 0x27, 0x23, 0x13}, 0},
	{0xd0, 16, {0x99, 0x06, 0x08, 0x20, 0x0a, 0x04, 0x01, 0x00, 0x08, 0x01, 0x00, 0x06, 0x01, 0x00, 0x00, 0x20}, 50},
	{0xd1, 4, {0x02, 0x1c, 0x1c, 0x36}, 0},
	{0x36, 1, {0xc1}, 0},
	{0x3a, 1, {0x77}, 0},
	{0x2a, 4, {0x00, 0x00, 0x01, 0x3f}, 0},
	{0x2b, 4, {0x00, 0x00, 0x01, 0x3f}, 50},
	{0x11, 0, {}, 102},
	{0x29, 0, {}, 17},
};

struct onyx_panel {
	struct drm_panel panel;
	struct spi_device *spi;
	struct gpio_desc *reset;
};
static int command(struct onyx_panel *p, const struct panel_command *c)
{
	u16 words[25];
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
	struct onyx_panel *p = container_of(panel, struct onyx_panel, panel);
	int error, i;
	gpiod_set_value_cansleep(p->reset, 1);
	msleep(20);
	gpiod_set_value_cansleep(p->reset, 0);
	msleep(120);
	for (i = 0; i < ARRAY_SIZE(init_commands); i++) {
		error = command(p, &init_commands[i]);
		if (error)
			return error;
	}
	return 0;
}
static int unprepare(struct drm_panel *panel)
{
	struct onyx_panel *p = container_of(panel, struct onyx_panel, panel);
	const struct panel_command off = {.command = 0x28}, sleep = {.command = 0x10, .delay = 120};
	command(p, &off);
	command(p, &sleep);
	gpiod_set_value_cansleep(p->reset, 1);
	return 0;
}
static int get_modes(struct drm_panel *panel, struct drm_connector *connector)
{
	static const u32 format = MEDIA_BUS_FMT_RGB888_1X24;
	struct drm_display_mode *mode = drm_mode_create(connector->dev);
	if (!mode)
		return -ENOMEM;
	mode->clock = 8088;
	mode->hdisplay = 320;
	mode->hsync_start = 370;
	mode->hsync_end = 380;
	mode->htotal = 400;
	mode->vdisplay = 320;
	mode->vsync_start = 328;
	mode->vsync_end = 330;
	mode->vtotal = 336;
	mode->flags = DRM_MODE_FLAG_PHSYNC | DRM_MODE_FLAG_PVSYNC;
	mode->type = DRM_MODE_TYPE_DRIVER | DRM_MODE_TYPE_PREFERRED;
	drm_mode_set_name(mode);
	drm_mode_probed_add(connector, mode);
	drm_display_info_set_bus_formats(&connector->display_info, &format, 1);
	connector->display_info.bus_flags =
	    DRM_BUS_FLAG_DE_HIGH | DRM_BUS_FLAG_PIXDATA_DRIVE_POSEDGE;
	return 1;
}
static const struct drm_panel_funcs functions = {
    .prepare = prepare, .unprepare = unprepare, .get_modes = get_modes};
static int probe(struct spi_device *spi)
{
	struct onyx_panel *p = devm_drm_panel_alloc(&spi->dev, struct onyx_panel, panel, &functions,
						   DRM_MODE_CONNECTOR_DPI);
	int error;
	if (IS_ERR(p))
		return PTR_ERR(p);
	p->spi = spi;
	p->reset = devm_gpiod_get(&spi->dev, "reset", GPIOD_OUT_HIGH);
	if (IS_ERR(p->reset))
		return PTR_ERR(p->reset);
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
	struct onyx_panel *p = spi_get_drvdata(spi);
	drm_panel_remove(&p->panel);
}
static const struct of_device_id match[] = {{.compatible = "nestlabs,onyx-panel"}, {}};
MODULE_DEVICE_TABLE(of, match);
static const struct spi_device_id ids[] = {{"onyx-panel", 0}, {}};
MODULE_DEVICE_TABLE(spi, ids);
static struct spi_driver onyx_panel_driver = {
    .probe = probe,
    .remove = remove_panel,
    .id_table = ids,
    .driver = {.name = "onyx-panel", .of_match_table = match}};
module_spi_driver(onyx_panel_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Nest Onyx Tianma TM025ZDHG03 panel");
