# -*- coding: utf-8 -*-
"""
Created on Mar 20 12:45:26 2024

@authors: Andrea Bassi. Politecnico di Milano
"""
from ScopeFoundry import BaseMicroscopeApp

class camera_app(BaseMicroscopeApp):
    

    name = 'plant_app'
    
    def setup(self):
        
        #Add hardware components
        print("Adding Hardware Components")
        from camera_hw import FlirHW
        self.add_hardware(FlirHW(self, name='camera_y'))
        self.add_hardware(FlirHW(self, name='camera_x'))
         
        from io_hw import IoHW
        self.add_hardware(IoHW(self, name='led_y'))
        self.add_hardware(IoHW(self, name='led_x'))
        
        
        # Add measurement components
        print("Create Measurement objects")
        # from Flir_ScopeFoundry.camera_measure import FlirMeasure
        # self.add_measurement(FlirMeasure(self))
        
        #from plant_measure import PlantMeasure
        #self.add_measurement(PlantMeasure(self))
        
        #from plant_timelapse_measure import PlantTimeLapseMeasure
        #self.add_measurement(PlantTimeLapseMeasure(self))

        from plant_timelapse_dual_measure import PlantTimeLapseDualMeasure
        self.add_measurement(PlantTimeLapseDualMeasure(self))


        self.ui.show()
        self.ui.activateWindow()


if __name__ == '__main__':
    import sys

    app = camera_app(sys.argv)
    app.settings_load_ini(".\\Settings\\settings_timelapse_dualview.ini")
    
    for hc_name, hc in app.hardware.items():
        hc.settings['connected'] = True    # connect all the hardwares  
    
    sys.exit(app.exec_())