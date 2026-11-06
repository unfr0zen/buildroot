JITTERENTROPY_RNGD_VERSION = 1.3.1
JITTERENTROPY_RNGD_SITE = $(call github,smuellerDD,jitterentropy-rngd,v$(JITTERENTROPY_RNGD_VERSION))
JITTERENTROPY_RNGD_LICENSE = BSD-3-Clause OR GPL-2.0-only
JITTERENTROPY_RNGD_LICENSE_FILES = COPYING COPYING.bsd COPYING.gplv2

# The noise source requires optimization to be disabled.
define JITTERENTROPY_RNGD_BUILD_CMDS
 $(TARGET_MAKE_ENV) $(MAKE) -C $(@D) CC="$(TARGET_CC)" \
  CFLAGS="$(TARGET_CFLAGS) -O0 -I. -Ilib -fwrapv" \
  LDFLAGS="$(TARGET_LDFLAGS) -lrt -lpthread"
endef

define JITTERENTROPY_RNGD_INSTALL_TARGET_CMDS
 $(INSTALL) -D -m 0755 $(@D)/jitterentropy-rngd $(TARGET_DIR)/usr/sbin/jitterentropy-rngd
 $(INSTALL) -D -m 0644 $(@D)/COPYING $(TARGET_DIR)/usr/share/licenses/jitterentropy-rngd/COPYING
endef

define JITTERENTROPY_RNGD_INSTALL_INIT_SYSTEMD
 $(INSTALL) -D -m 0644 $(JITTERENTROPY_RNGD_PKGDIR)/jitterentropy.service $(TARGET_DIR)/usr/lib/systemd/system/jitterentropy.service
endef

$(eval $(generic-package))
