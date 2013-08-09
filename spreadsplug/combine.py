import logging
import operator
import os
import shutil

from spreads.plugin import HookPlugin

logger = logging.getLogger('spreadsplug.combine')


class CombinePlugin(HookPlugin):
    @classmethod
    def add_arguments(cls, command, parser):
        if command == 'download':
            parser.add_argument("--first-page", "-fp",
                                dest="first_page", default="left",
                                help="Set device with first page (left/right)"
                                " [default: left]")

    def download(self, cameras, path):
        left_dir = os.path.join(path, 'left')
        right_dir = os.path.join(path, 'right')
        target_dir = os.path.join(path, 'raw')
        if not os.path.exists(target_dir):
            os.mkdir(target_dir)
        left_pages = [os.path.join(left_dir, x)
                      for x in sorted(os.listdir(left_dir))]
        right_pages = [os.path.join(right_dir, x)
                       for x in sorted(os.listdir(right_dir))]
        # Write the orientation as a JPEG comment to the end of the file
        if len(left_pages) != len(right_pages):
            logger.warn("The left and right camera produced an inequal"
                        " amount of images, please fix the problem!")
            logger.warn("Will not combine images")
            return
        if (self.config['first_page']
                and not self.config['first_page'].get(str) == 'left'):
            combined_pages = reduce(operator.add, zip(right_pages, left_pages))
        else:
            combined_pages = reduce(operator.add, zip(left_pages, right_pages))
        logger.info("Combining images.")
        for idx, fname in enumerate(combined_pages):
            fext = os.path.splitext(os.path.split(fname)[1])[1]
            target_file = os.path.join(target_dir, "{0:04d}{1}"
                                       .format(idx, fext))
            shutil.copyfile(fname, target_file)
        shutil.rmtree(right_dir)
        shutil.rmtree(left_dir)
