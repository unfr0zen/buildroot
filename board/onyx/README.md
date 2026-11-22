# Onyx board reference

Nest Thermostat E: i.MX6UL Cortex-A7, 128 MiB LPDDR2, 512 MiB NAND.
The public signed loader is `u-boot-sdp-5.8d44-onyx-0NUR.hab`.
Unsigned development FITs require open fuses or an authorized unlock token;
QEMU's development launcher explicitly selects open fuses.

| Function | Onyx EVT wiring | Buildroot interface |
| --- | --- | --- |
| Debug console | UART1, `ttymxc0` | Enabled |
| Display | LCDIF, 320×320 RGB888; ECSPI2, CS GPIO1_29, reset GPIO3_4 | DRM console |
| Backlight | LM3695, I2C2 `0x63`, enable GPIO4_16 | Enabled during display startup |
| Front button | GPIO2_8, active low | `KEY_ENTER` |
| USB | USB OTG1 peripheral | CDC ACM and ECM, DHCP server |
| BLE | UART2, reset GPIO2_1 | UART exposed; radio integration pending |
| Backplate | UART3, reset GPIO1_18, detect GPIO4_28 | `nest-backplate`, `/run/nest/backplate.state` |
| Wheel | ADC1 channels 7/6, enable GPIO2_21 active low | `REL_DIAL` input events |
| Battery | ADC1 channel 4, divider 169/124, enable GPIO2_4 | `nest-battery/voltage_now` in µV |
| Wi-Fi | USDHC2, reset GPIO2_16, IRQ GPIO2_17 | BCM43341 SDIO, `wlan0` |
| Piezo | PWM8, enable GPIO2_6 active low | `nest-tone` |
| Thread | ECSPI4, reset GPIO2_19, wake GPIO2_2, IRQ GPIO2_18 | EM358 Spinel SPI, `/dev/spidev_em35x` |

Build the image with `make BOARD=onyx`. Run `make onyx-smoke` for the guest hardware checks or
`make onyx-qemu-ui FRESH=1` to start the UI with the new image. QEMU advertises the open Wi-Fi
network `QEMU`; the smoke test connects and checks its DHCP lease.

If a cached QEMU build predates the Thread model, `qemu/qemu-src/build/qemu-system-arm -device help`
will omit `spinel-ncp`. Move that `qemu/qemu-src` directory aside and run `make qemu-build` to apply
the pinned patch set in a fresh tree.

The panel is TM025ZDHG03. Its R61529A1 initialization and timing
are inferred from Nest's Onyx Proto1.1/EVT sources; physical confirmation
of the controller and orientation remains necessary. QEMU models LCDIF
scanout, not the panel's internal command processor.

Sources: [Onyx EVT device tree](https://nest-open-source.googlesource.com/nest-learning-thermostat/6.5/linux-imx-ul/+/refs/heads/master/arch/arm/boot/dts/onyx-evt.dts),
[Proto1.1 display setup](https://nest-open-source.googlesource.com/nest-learning-thermostat/6.5/linux-imx-ul/+/refs/heads/master/arch/arm/boot/dts/onyx-proto11.dts),
[common wiring](https://nest-open-source.googlesource.com/nest-learning-thermostat/6.5/linux-imx-ul/+/refs/heads/master/arch/arm/boot/dts/onyx-common.dtsi),
[R61529A1 driver](https://nest-open-source.googlesource.com/nest-learning-thermostat/6.5/linux-imx-ul/+/refs/heads/master/drivers/video/backlight/r61529a1.c).
