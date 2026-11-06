J49_XLOADER_VERSION = 9b7bb7281b715544e6f5201390d8dac416a4a494
J49_XLOADER_SITE = https://nest-open-source.googlesource.com/nest-learning-thermostat/5.9.4/x-loader
J49_XLOADER_SITE_METHOD = git
J49_XLOADER_LICENSE = GPL-2.0+
J49_XLOADER_LICENSE_FILES = x-loader/README
J49_XLOADER_INSTALL_IMAGES = YES
J49_XLOADER_INSTALL_TARGET = NO
J49_XLOADER_MAKE = $(TARGET_MAKE_ENV) $(MAKE) -C $(@D)/x-loader ARCH=arm CROSS_COMPILE="$(TARGET_CROSS)" CC="$(TARGET_CC) -marm -fcommon -std=gnu89" HOSTCC="$(HOSTCC) -fcommon -std=gnu89"

define J49_XLOADER_BUILD_CMDS
 sed -i s/-fno-common/-fcommon/g $(@D)/x-loader/config.mk
 $(SED) s/-fno-common/-fcommon/g $(@D)/x-loader/cpu/omap3/config.mk
 $(J49_XLOADER_MAKE) j49_config
 $(J49_XLOADER_MAKE)
endef

define J49_XLOADER_INSTALL_IMAGES_CMDS
 $(INSTALL) -m 0644 $(@D)/x-loader/x-load.bin.ift $(BINARIES_DIR)/MLO
endef

$(eval $(generic-package))
