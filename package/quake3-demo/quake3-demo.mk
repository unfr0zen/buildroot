QUAKE3_DEMO_VERSION = 1.11-6
QUAKE3_DEMO_SOURCE = linuxq3ademo-$(QUAKE3_DEMO_VERSION).x86.gz.sh
QUAKE3_DEMO_SITE = https://ftp.gwdg.de/pub/misc/ftp.idsoftware.com/idstuff/quake3/linux
QUAKE3_DEMO_EXTRA_DOWNLOADS = $(QUAKE3_DEMO_SITE)/linuxq3apoint-1.32b-3.x86.run
QUAKE3_DEMO_LICENSE = Proprietary
QUAKE3_DEMO_LICENSE_FILES = Help/Q3A_EULA.txt Q3A_EULA.txt
QUAKE3_DEMO_REDISTRIBUTE = NO
QUAKE3_DEMO_DEPENDENCIES = ioquake3

# Extract the self-extracting archive without running its x86 installer.
define QUAKE3_DEMO_EXTRACT_CMDS
 tail -n +165 $(QUAKE3_DEMO_DL_DIR)/$(QUAKE3_DEMO_SOURCE) | \
  $(TAR) -xz -C $(@D) demoq3/pak0.pk3 Help/Q3A_EULA.txt
 tail -n +356 $(QUAKE3_DEMO_DL_DIR)/linuxq3apoint-1.32b-3.x86.run | \
  $(TAR) -xz -C $(@D) baseq3 Q3A_EULA.txt
endef

define QUAKE3_DEMO_INSTALL_TARGET_CMDS
 $(INSTALL) -D -m 0644 $(@D)/demoq3/pak0.pk3 $(TARGET_DIR)/usr/lib/ioquake3/demoq3/pak0.pk3
 for module in cgame qagame ui; do \
  ln -sf ../baseq3/$$module.so $(TARGET_DIR)/usr/lib/ioquake3/demoq3/$$module.so; \
 done
 for pak in $(@D)/baseq3/pak*.pk3; do \
  $(INSTALL) -D -m 0644 $$pak $(TARGET_DIR)/usr/lib/ioquake3/baseq3/$$(basename $$pak); \
 done
 $(INSTALL) -D -m 0644 $(@D)/Q3A_EULA.txt $(TARGET_DIR)/usr/share/licenses/quake3-demo/Q3A_EULA-point-release.txt
 $(INSTALL) -D -m 0644 $(@D)/Help/Q3A_EULA.txt $(TARGET_DIR)/usr/share/licenses/quake3-demo/Q3A_EULA.txt
endef

$(eval $(generic-package))
