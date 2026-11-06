"""Size validation and layout reporting shared by the NAND image packers."""


def validate_components(components):
    print('--- Validating component sizes ---', flush=True)
    for name, offset, size, limit in components:
        print(f'  {name}: {size} bytes / {limit} bytes ({size * 100 // limit}%)')
        if size > limit:
            raise SystemExit(f'{name} exceeds its NAND reservation')


def begin_image(components):
    print('--- Assembling NAND flash image ---')
    print('  Offsets are NAND data addresses.')
    for name, offset, size, limit in components:
        print(f'  {name:<10} offset 0x{offset:08x}, {size} / {limit} bytes')
    print(flush=True)


def finish_image(path, capacity):
    size = path.stat().st_size
    extra = f', {size - capacity} OOB/ECC bytes' if size > capacity else ''
    print(f'  {path.name}: {size} bytes (flash data capacity {capacity}{extra})')
    print('=== NAND image assembled ===')
    print(f'  Location: {path.resolve()}')
