import logging
import operator
import os
import shutil

from spreads.plugin import HookPlugin


class CombinePlugin(HookPlugin):
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
        for page in left_pages:
            with open(page, "a+b") as fp:
                fp.write("\xff\xfeLEFT")
        for page in left_pages:
            with open(page, "a+b") as fp:
                fp.write("\xff\xfeRIGHT")
        if len(left_pages) != len(right_pages):
            logging.warn("The left and right camera produced an inequal"
                         " amount of images!")
        combined_pages = reduce(operator.add, zip(right_pages, left_pages))
        logging.info("Combining images.")
        for idx, fname in enumerate(combined_pages):
            fext = os.path.splitext(os.path.split(fname)[1])[1]
            target_file = os.path.join(target_dir, "{0:04d}{1}"
                                       .format(idx, fext))
            shutil.copyfile(fname, target_file)
        shutil.rmtree(right_dir)
        shutil.rmtree(left_dir)
