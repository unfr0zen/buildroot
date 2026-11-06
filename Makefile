.DEFAULT_GOAL := all
ROOT := $(CURDIR)
BR_VERSION := 2026.08.1
BR := $(ROOT)/buildroot
BOARD ?= diamond3
OUT := $(ROOT)/output$(if $(filter j49,$(BOARD)),/j49,)
BRMAKE = $(MAKE) -C $(BR) O=$(OUT) BR2_EXTERNAL=$(ROOT)

.PHONY: all configure diamond3-defconfig menuconfig linux-menuconfig clean docker prepare
prepare:
	git submodule update --init --depth 1 buildroot
diamond3-defconfig configure: prepare
	$(BRMAKE) $(BOARD)_defconfig
all: prepare
	@test -f $(OUT)/.config || $(BRMAKE) $(BOARD)_defconfig
	$(BRMAKE) -j8
menuconfig linux-menuconfig clean toolchain: prepare
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
	@test -n "$(NAND)" || { echo 'Set NAND=/absolute/path/to/stock-j49.raw'; exit 1; }
	python3 scripts/qemu-j49.py --stock "$(NAND)" $(if $(filter j49-qemu-ui,$@),--ui,) $(if $(FRESH),--fresh,)

.PHONY: j49-smoke
j49-smoke:
	@test -n "$(NAND)" || { echo 'Set NAND=/absolute/path/to/stock-j49.raw'; exit 1; }
	python3 scripts/qemu-j49.py --stock "$(NAND)" --nand .work/j49-smoke.raw --fresh --smoke
