NEST_TOOLS_VERSION = 1
NEST_TOOLS_SITE = $(BR2_EXTERNAL_DIAMOND3_PATH)/package/nest-tools/src
NEST_TOOLS_SITE_METHOD = local
NEST_TOOLS_LICENSE = GPL-2.0-only

define NEST_TOOLS_BUILD_CMDS
 $(TARGET_CC) $(TARGET_CFLAGS) -Wall -Wextra -o $(@D)/nest-terminal $(@D)/terminal.c $(TARGET_LDFLAGS) -lutil
 $(TARGET_CC) $(TARGET_CFLAGS) -Wall -Wextra -o $(@D)/diamond3-tone $(@D)/tone.c $(TARGET_LDFLAGS)
endef

define NEST_TOOLS_INSTALL_TARGET_CMDS
 $(INSTALL) -D -m 0755 $(@D)/nest-terminal $(TARGET_DIR)/usr/bin/nest-terminal
 $(INSTALL) -D -m 0755 $(@D)/diamond3-tone $(TARGET_DIR)/usr/bin/diamond3-tone
 $(INSTALL) -D -m 0755 $(@D)/diamond3-tone $(TARGET_DIR)/usr/bin/nest-tone
endef

$(eval $(generic-package))
