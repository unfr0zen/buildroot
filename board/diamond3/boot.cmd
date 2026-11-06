setenv mtdparts mtdparts=mx6_nand:4m(u-boot),-(ubipart)
ubi part ubipart
ubi read 0x83000000 kernel
ubi read 0x85000000 dtb
ubi read 0x86000000 initramfs
setenv bootargs console=tty0 console=ttymxc0,115200 earlycon ubi.mtd=1 root=ubi0:rootfs rootfstype=ubifs rw clk_ignore_unused
bootm 0x83000000 0x86000000 0x85000000
