import taichi as ti


from textures.sprite import ImageSprite
from textures.stage import Stage

if __name__ == "__main__":

    ti.init(arch=ti.gpu, debug=True, log_level=ti.TRACE, offline_cache=False)

    WIDTH = 720
    HEIGHT = 1280

    stage = Stage(width=WIDTH, height=HEIGHT)

    image = ImageSprite(
        image_file="0.jpg",
        width=WIDTH,
        height=HEIGHT,
    )

    image.x = 0
    image.y = 0
    image.alpha = 0.5
    stage.add_child(image)



    stage.render()
    stage.save("alpha.jpg")

    image.x = -30
    stage.render()

    stage.save("alpha1.jpg")
