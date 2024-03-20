# -*- coding: utf-8 -*-
"""

"""
from ScopeFoundry import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
from ScopeFoundry import h5_io
import pyqtgraph as pg
import numpy as np
import os
import time


class PlantMeasure(Measurement):

    name = "Plant_measurement"

    def setup(self):
        """
        Runs once during App initialization.
        This is the place to load a user interface file,
        define settings, and set up data structures.
        For Pointgrey Grasshopper CMOS the pixelsize is: 5.86um
        """

        self.ui_filename = sibling_path(__file__, "camera.ui")
        self.ui = load_qt_ui_file(self.ui_filename)

        self.settings.New('save_h5', dtype=bool, initial=False)
        self.settings.New('refresh_period', dtype=float,
                          unit='s', spinbox_decimals=3, initial=0.05, vmin=0)

        self.settings.New('xsampling', dtype=float, unit='um',
                          initial=0.0586, spinbox_decimals=4)
        self.settings.New('ysampling', dtype=float, unit='um',
                          initial=0.0586, spinbox_decimals=4)
        self.settings.New('zsampling', dtype=float, unit='um',
                          initial=1.0, spinbox_decimals=4)

        self.auto_range = self.settings.New(
            'auto_range', dtype=bool, initial=True)
        self.settings.New('auto_levels', dtype=bool, initial=True)
        self.settings.New('level_min', dtype=int, initial=60)
        self.settings.New('level_max', dtype=int, initial=4000)

        self.image_gen = self.app.hardware['camera_x']
        self.dlp_hw = self.app.hardware['led_x']

    def setup_figure(self):
        """
        Runs once during App initialization, after setup()
        This is the place to make all graphical interface initializations,
        build plots, etc.
        """

        # connect ui widgets to measurement/hardware settings or functions
        self.ui.start_pushButton.clicked.connect(self.start)
        self.ui.interrupt_pushButton.clicked.connect(self.interrupt)
        self.settings.save_h5.connect_to_widget(self.ui.save_h5_checkBox)
        self.settings.auto_levels.connect_to_widget(
            self.ui.autoLevels_checkbox)
        self.settings.auto_range.connect_to_widget(self.ui.autoRange_checkbox)
        self.settings.level_min.connect_to_widget(self.ui.min_doubleSpinBox)
        self.settings.level_max.connect_to_widget(self.ui.max_doubleSpinBox)

        # Set up pyqtgraph graph_layout in the UI
        self.imv = pg.ImageView()
        self.ui.imageLayout.addWidget(self.imv)
        colors = [(0, 0, 0),
                  (45, 5, 61),
                  (84, 42, 55),
                  (150, 87, 60),
                  (208, 171, 141),
                  (255, 255, 255)
                  ]
        cmap = pg.ColorMap(pos=np.linspace(0.0, 1.0, 6), color=colors)
        self.imv.setColorMap(cmap)

    def update_display(self):
        """
        Displays (plots) the numpy array self.buffer. 
        This function runs repeatedly and automatically during the measurement run.
        its update frequency is defined by self.display_update_period
        """
        #self.display_update_period = self.settings['refresh_period']
        length = self.image_gen.frame_num.val

        self.settings['progress'] = (self.frame_index + 1) * 100/length

        if hasattr(self, 'img'):
            self.imv.setImage(self.img.T,
                              autoLevels=self.settings['auto_levels'],
                              autoRange=self.auto_range.val,
                              levelMode='mono'
                              )

            if self.settings['auto_levels']:
                lmin, lmax = self.imv.getHistogramWidget().getLevels()
                self.settings['level_min'] = lmin
                self.settings['level_max'] = lmax
            else:
                self.imv.setLevels(min=self.settings['level_min'],
                                   max=self.settings['level_max'])

    def measure(self):
        """
        Set mode to Multiframe, acquire Nframes frames and eventually save them in h5 
        """
        self.image_gen.camera.acq_stop()
        self.image_gen.settings['acquisition_mode'] = 'MultiFrame'
        self.dlp_hw.turn_on()
        first_frame_acquired = False
        frame_num = self.image_gen.frame_num.val
        self.image_gen.camera.set_framenum(frame_num)
        self.image_gen.camera.acq_start()

        for frame_idx in range(frame_num):
            # self.dlp_hw.turn_on()
            self.frame_index = frame_idx
            self.img = self.image_gen.camera.get_nparray()
            # self.dlp_hw.turn_off()
            if self.settings['save_h5']:
                if not first_frame_acquired:
                    self.create_h5_file()
                    first_frame_acquired = True

                self.image_h5[frame_idx, :, :] = self.img
                self.h5file.flush()
            if self.interrupt_measurement_called:
                break

        self.image_gen.camera.acq_stop()
        self.dlp_hw.turn_off()

    def run(self):
        """
        Runs when measurement is started. Runs in a separate thread from GUI.
        It should not update the graphical interface directly, and should only
        focus on data acquisition.
        """
        self.image_gen.read_from_hardware()

        try:
            self.frame_index = -1
            self.image_gen.settings['acquisition_mode'] = 'Continuous'
            self.image_gen.camera.acq_start()

            while not self.interrupt_measurement_called:

                self.img = self.image_gen.camera.get_nparray()

                if self.interrupt_measurement_called:
                    break

                if self.settings['save_h5']:
                    # measure is triggered by save_h5 button
                    self.measure()
                    break

        finally:

            self.image_gen.camera.acq_stop()
            if self.settings['save_h5'] and hasattr(self, 'h5file'):
                # make sure to close the data file
                self.h5file.close()

    def create_saving_directory(self):

        if not os.path.isdir(self.app.settings['save_dir']):
            os.makedirs(self.app.settings['save_dir'])

    def create_h5_file(self):
        self.create_saving_directory()
        # file name creation
        timestamp = time.strftime("%y%m%d_%H%M%S", time.localtime())
        sample = self.app.settings['sample']
        #sample_name = f'{timestamp}_{self.name}_{sample}.h5'
        if sample == '':
            sample_name = '_'.join([timestamp, self.name])
        else:
            sample_name = '_'.join([timestamp, self.name, sample])
        fname = os.path.join(
            self.app.settings['save_dir'], sample_name + '.h5')

        self.h5file = h5_io.h5_base_file(
            app=self.app, measurement=self, fname=fname)
        self.h5_group = h5_io.h5_create_measurement_group(
            measurement=self, h5group=self.h5file)

        img_size = self.img.shape
        dtype = self.img.dtype

        length = self.image_gen.frame_num.val
        self.image_h5 = self.h5_group.create_dataset(name='t0/c0/image',
                                                     shape=[
                                                         length, img_size[0], img_size[1]],
                                                     dtype=dtype)
        self.image_h5.attrs['element_size_um'] = [
            self.settings['zsampling'], self.settings['ysampling'], self.settings['xsampling']]
