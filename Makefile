.DEFAULT_GOAL := all
ROOT := $(CURDIR)
BR_VERSION := 2026.08.1
BR := $(ROOT)/buildroot
BOARD ?= diamond3
OUT := $(ROOT)/output$(if $(filter j49,$(BOARD)),/j49,)
UBOOT ?= $(ROOT)/output/images/u-boot-sdp-5.2d43-nand.bin
BRMAKE = $(MAKE) -C $(BR) O=$(OUT) BR2_EXTERNAL=$(ROOT)

.PHONY: all configure diamond3-defconfig menuconfig linux-menuconfig clean docker prepare
prepare:
	git submodule update --init --depth 1 buildroot
diamond3-defconfig configure: prepare
	$(BRMAKE) $(BOARD)_defconfig
all: prepare $(if $(filter diamond3,$(BOARD)),uboot,)
	@test -f $(OUT)/.config || $(BRMAKE) $(BOARD)_defconfig
	$(BRMAKE) -j8
menuconfig linux-menuconfig clean toolchain: prepare
	$(BRMAKE) $@
docker:
	./scripts/build.sh

.PHONY: uboot
uboot:
	python3 scripts/fetch-uboot.py output/images

.PHONY: qemu
qemu: uboot
	python3 scripts/qemu.py --uboot "$(UBOOT)" $(if $(FRESH),--fresh,) $(if $(BLE_HCI_TEST),--ble-hci-test,)

.PHONY: diamond3-image
diamond3-image: uboot
	@test -n "$(BOOT_NAND)" || { echo 'Set BOOT_NAND=/absolute/path/to/logical-nand-backup.bin'; exit 1; }
	python3 scripts/diamond3-nand.py --uboot "$(UBOOT)" --boot-reference "$(BOOT_NAND)"

.PHONY: firmware
firmware:
	@test -n "$(FIRMWARE_DIR)" || { echo 'Set FIRMWARE_DIR to the stock lib/firmware/brcm directory'; exit 1; }
	mkdir -p .work/firmware/brcm
	cp "$(FIRMWARE_DIR)/brcmfmac43340-sdio.bin" "$(FIRMWARE_DIR)/brcmfmac43340-sdio.txt" .work/firmware/brcm/

QEMU ?= ../qemu/qemu-src/build/qemu-system-arm
.PHONY: rom
rom:
	@test -n "$(ROM)" || { echo 'Set ROM=/absolute/path/to/full-rom.bin'; exit 1; }
	$(QEMU) -M diamond3,boot-rom="$(ROM)" -display none -serial stdio -monitor none

%-rebuild %-reconfigure %-dirclean: prepare
	$(BRMAKE) $@

.PHONY: qemu-ui smoke
qemu-ui: uboot
	python3 scripts/qemu.py --uboot "$(UBOOT)" --ui $(if $(FRESH),--fresh,) $(if $(BLE_HCI_TEST),--ble-hci-test,)
smoke: uboot
	python3 scripts/qemu.py --uboot "$(UBOOT)" --nand .work/smoke-nand.bin --fresh --smoke

.PHONY: j49-defconfig j49
j49-defconfig:
	$(MAKE) BOARD=j49 configure
j49:
	./scripts/build.sh --board j49 all

.PHONY: j49-firmware j49-qemu j49-qemu-ui
j49-firmware:
	@test -n "$(NVS)" || { echo 'Set NVS=/path/to/stock/wl12xx-nvs.bin'; exit 1; }
	mkdir -p .work/firmware/ti-connectivity
	cp "$(NVS)" .work/firmware/ti-connectivity/wl1271-nvs.bin
j49-qemu j49-qemu-ui:
	python3 scripts/qemu-j49.py $(if $(filter j49-qemu-ui,$@),--ui,) $(if $(FRESH),--fresh,)

.PHONY: j49-smoke
j49-smoke:
	python3 scripts/qemu-j49.py --nand .work/j49-smoke.raw --fresh --smoke
