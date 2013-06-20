Tutorial
========
1. Connect your cameras to your computer (at the moment only Canon A2200 models
   with the custom CHDK firmware are supported, but you can
   :doc:`change that! <extending>`).
   Make sure that you have *gphoto2* and *ptpcam* installed.
2. Run the following command in the shell of your choice and follow the
   instructions on the screen:
   
  ``$ spread configure``

3. Now you can begin shooting:

   ``$ spread shoot``

   When you're done, press any key besides the **spacebar** or **b**.

4. Time to get those images to your computer!

   ``$ spread download ~/scans/mybook``

5. And now let's make those scans pretty :-)

   ``$ spread postprocess ~/scans/mybook``

If you want to know more about any of the above commands, check out their
respective entries in the :doc:`command-line reference <commands>`.

