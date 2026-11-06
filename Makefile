.DEFAULT_GOAL := all
ROOT := $(CURDIR)
BR_VERSION := 2026.08.1
BR := $(ROOT)/buildroot
OUT := $(ROOT)/output
BRMAKE = $(MAKE) -C $(BR) O=$(OUT) BR2_EXTERNAL=$(ROOT)

.PHONY: all configure diamond3-defconfig menuconfig linux-menuconfig clean docker prepare
prepare:
	git submodule update --init --depth 1 buildroot
diamond3-defconfig configure: prepare
	$(BRMAKE) diamond3_defconfig
all: prepare
	@test -f $(OUT)/.config || $(BRMAKE) diamond3_defconfig
	$(BRMAKE) -j8
menuconfig linux-menuconfig clean: prepare
	$(BRMAKE) $@
docker:
	./scripts/build.sh

.PHONY: qemu
qemu:
	@test -n "$(UBOOT)" || { echo 'Set UBOOT=/absolute/path/to/signed.hab'; exit 1; }
	python3 scripts/qemu.py --uboot "$(UBOOT)"

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
qemu-ui:
	@test -n "$(UBOOT)" || { echo 'Set UBOOT=/absolute/path/to/signed.hab'; exit 1; }
	python3 scripts/qemu.py --uboot "$(UBOOT)" --ui
smoke:
	@test -n "$(UBOOT)" || { echo 'Set UBOOT=/absolute/path/to/signed.hab'; exit 1; }
	python3 scripts/qemu.py --uboot "$(UBOOT)" --nand .work/smoke-nand.bin --fresh --smoke
