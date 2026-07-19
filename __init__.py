"""Quick Map GIF -- capture map canvas frames and export them as an animated GIF."""


def classFactory(iface):
    from .quick_map_gif import QuickMapGifPlugin

    return QuickMapGifPlugin(iface)
