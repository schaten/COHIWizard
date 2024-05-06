from pathlib import Path
from PyQt5.QtGui import QIcon


class Icons:

    """This class provides various assets for the different modules."""

    @staticmethod
    def load_icon(folder, name):
        """Loads an icon and returns it as a QIcon.

        Args:
            folder (str): The folder in which the image is located.
            name (str): The name of the image to load.

        Returns:
            QIcon: The loaded image.
        """
        #path = Path(__file__).parent / folder / name
        path = Path(folder) / name
        print(f"path for splashscreen: {path}")
        icon = QIcon(str(path))

        # Print warning if the icon could not be loaded
        if icon.availableSizes() == []:
            print(f"Could not load icon: {path}")

        return icon

class Logos(Icons):

    """This class provides the logos for the different modules."""

    @staticmethod
    def get_logo(logopath, name):
        """Returns a logo as a QIcon.

        Args:
            name (str): The name of the logo to load.

        Returns:
            QIcon: The loaded logo.
        """
        return Icons.load_icon(logopath, name)
    
    @staticmethod
    def Logo_full(logopath):
        """ Returns the Logo_fulllogo as QIcon.
        This is also exported in 400%. Only use this for the splash screen and maybe about page. It has a weird size.
        Returns:
            QIcon: The Logo_full"""
        return Logos.get_logo(logopath,"SplasScreen_s.png")
