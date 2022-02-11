if __name__ == "__main__":
    import sys
    import numpy
    from PIL import Image
    with open(sys.argv[1], "rb") as f:
        width, height, channels, colorspace, pixels = compile_chain(
            [(QOI, "decode")], f.read()
        )
        print(width)
        print(height)
        print(width*height)
        print(len(pixels))
    Image.fromarray(
        numpy.array(
            numpy.split(
                numpy.array(pixels, dtype=numpy.uint8),
                height
            ),
        ),
        "RGBA"
    ).save(f"{sys.argv[1]}.png")
