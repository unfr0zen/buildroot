J49_UBOOT_VERSION = 3e6d8487fcc10d400584dce41900e66733cb41a3
J49_UBOOT_SITE = https://nest-open-source.googlesource.com/nest-learning-thermostat/5.7/u-boot
J49_UBOOT_SITE_METHOD = git
J49_UBOOT_LICENSE = GPL-2.0+
J49_UBOOT_LICENSE_FILES = u-boot/COPYING
J49_UBOOT_INSTALL_IMAGES = YES
J49_UBOOT_INSTALL_TARGET = NO
J49_UBOOT_DEPENDENCIES = host-uboot-tools
J49_UBOOT_MAKE = $(TARGET_MAKE_ENV) $(MAKE) -C $(@D)/u-boot ARCH=arm CROSS_COMPILE="$(TARGET_CROSS)" CC="$(TARGET_CC) -marm -fcommon -std=gnu89" HOSTCC="$(HOSTCC) -fcommon -std=gnu89"

define J49_UBOOT_BUILD_CMDS
 cp $(@D)/u-boot/include/linux/compiler-gcc4.h $(@D)/u-boot/include/linux/compiler-gcc$(shell $(TARGET_CC) -dumpversion | cut -d. -f1).h
 sed -i s/-fno-common/-fcommon/g $(@D)/u-boot/config.mk
 $(J49_UBOOT_MAKE) j49_config
 printf '#define NEST_BUILD_CONFIG "buildroot"\n' >> $(@D)/u-boot/include/config.h
 $(J49_UBOOT_MAKE) u-boot.bin
endef

define J49_UBOOT_INSTALL_IMAGES_CMDS
 $(INSTALL) -m 0644 $(@D)/u-boot/u-boot.bin $(BINARIES_DIR)/u-boot-j49.bin
 $(HOST_DIR)/bin/mkimage -A arm -O u-boot -T firmware -C none -a 0x80100000 -e 0x80100000 -n J49 -d $(@D)/u-boot/u-boot.bin $(BINARIES_DIR)/u-boot-j49.img
endef

$(eval $(generic-package))
