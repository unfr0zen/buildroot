NBNSD_VERSION = 97a1695e85b22aef5116d5e83ec722d67816cfaf
NBNSD_SITE = $(call github,cfstras,nbnsd,$(NBNSD_VERSION))
NBNSD_LICENSE = MIT
NBNSD_LICENSE_FILES = nbnsd.c

define NBNSD_BUILD_CMDS
 $(TARGET_MAKE_ENV) $(MAKE) $(TARGET_CONFIGURE_OPTS) -C $(@D)
endef

define NBNSD_INSTALL_TARGET_CMDS
 $(INSTALL) -D -m 0755 $(@D)/out/nbnsd $(TARGET_DIR)/usr/sbin/nbnsd
 $(INSTALL) -D -m 0644 $(@D)/nbnsd.c $(TARGET_DIR)/usr/share/licenses/nbnsd/nbnsd.c
endef

$(eval $(generic-package))
