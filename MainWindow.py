from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import * #(QApplication, QMainWindow, QWidget, QDesktopWidget, QSizePolicy,
                             #QGridLayout, QHBoxLayout, QFormLayout,
                             #QToolButton, QAction, QMenu, QPushButton, QLineEdit)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from bluetooth import *
import os
import sys
import random
import numpy as np
import time
import serial
import serial.tools.list_ports
import json
import time
import threading

from USBArduino import USBArduino
from BluetoothArduino import BluetoothArduino
from APICommands import *
from camera_widget import camWidget, Camera

baudrate = 9600
blacklist = ["20:15:03:03:08:43"]
hwids = [["1A86", "7523"]]
bluetooth_devices = ["HC-06"]
usb_dir = "/media/pi"
bluetooth_port = 1

class PlotCanvas(FigureCanvas):
    """
    
    """
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        """
        
        """
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        FigureCanvas.setSizePolicy(self,
                QSizePolicy.Expanding,
                QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

    def plot(self, arduinos):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        for i, arduino in enumerate(arduinos):
            for label, data in arduino.data.items():
                if arduino.active_data[label]:
                    if len(data) == 0:  # avoid indexing an empty data list
                        ax.plot(data, label="{}. {}\t[{}]".format(i+1, label, arduino.data_units[label])
                                                          .expandtabs())
                    else:
                        ax.plot(data, label="{}. {}\t{}\t[{}]".format(i+1, label, data[-1], arduino.data_units[label])
                                                              .expandtabs())
                    #ax.annotate(str(data[-1]), xy=(len(data)-1,data[-1]), xytext=(0,0), textcoords='offset points')

        ax.legend(loc='upper left', prop={'family': 'DejaVu Sans Mono'})
        lims = [data_range[:][0] for arduino in arduinos for data_range in arduino.data_ranges]
        lims += [data_range[:][1] for arduino in arduinos for data_range in arduino.data_ranges]
        if len(lims) != 0:
            ax.set_ylim(min(lims), max(lims))
        self.draw()

class NumberPadPopup(QWidget):
    def __init__(self, mainwindow):
        """
        Initialise the Number Pad popup with each button and it's connection to 'AddDigit'
        """
        QWidget.__init__(self)
        
        # Define the grid layout
        layout = QGridLayout()
        
        # Create the buttons, add them to the layout and define their clicked link
        self.button1 = QPushButton('1')
        layout.addWidget(self.button1, 0,0)
        self.button1.clicked.connect(lambda: mainwindow.addDigit("1"))
        self.button2 = QPushButton('2')
        layout.addWidget(self.button2, 0,1)
        self.button2.clicked.connect(lambda: mainwindow.addDigit("2"))
        self.button3 = QPushButton('3')
        layout.addWidget(self.button3, 0,2)
        self.button3.clicked.connect(lambda: mainwindow.addDigit("3"))
        self.button4 = QPushButton('4')
        layout.addWidget(self.button4, 1,0)
        self.button4.clicked.connect(lambda: mainwindow.addDigit("4"))
        self.button5 = QPushButton('5')
        layout.addWidget(self.button5, 1,1)
        self.button5.clicked.connect(lambda: mainwindow.addDigit("5"))
        self.button6 = QPushButton('6')
        layout.addWidget(self.button6, 1,2)
        self.button6.clicked.connect(lambda: mainwindow.addDigit("6"))
        self.button7 = QPushButton('7')
        layout.addWidget(self.button7, 2,0)
        self.button7.clicked.connect(lambda: mainwindow.addDigit("7"))
        self.button8 = QPushButton('8')
        layout.addWidget(self.button8, 2,1)
        self.button8.clicked.connect(lambda: mainwindow.addDigit("8"))
        self.button9 = QPushButton('9')
        layout.addWidget(self.button9, 2,2)
        self.button9.clicked.connect(lambda: mainwindow.addDigit("9"))
        self.buttonBack = QPushButton('Delete')
        layout.addWidget(self.buttonBack, 3,0)
        self.buttonBack.clicked.connect(lambda: mainwindow.addDigit("back"))
        self.button0 = QPushButton('0')
        layout.addWidget(self.button0, 3,1)
        self.button0.clicked.connect(lambda: mainwindow.addDigit("0"))
        self.buttonEnter = QPushButton('Enter')
        layout.addWidget(self.buttonEnter, 3,2)
        self.buttonEnter.clicked.connect(lambda: self.close())
        self.setWindowTitle('Number Pad')
        
        self.button1.setMinimumHeight(50)
        self.button2.setMinimumHeight(50)
        self.button3.setMinimumHeight(50)
        self.button4.setMinimumHeight(50)
        self.button5.setMinimumHeight(50)
        self.button6.setMinimumHeight(50)
        self.button7.setMinimumHeight(50)
        self.button8.setMinimumHeight(50)
        self.button9.setMinimumHeight(50)
        self.buttonBack.setMinimumHeight(50)
        self.button0.setMinimumHeight(50)
        self.buttonEnter.setMinimumHeight(50)
        
        
        # Set the number pad layout
        self.setLayout(layout)

class MainWindow(QMainWindow):
    
    def __init__(self, parent=None):
        """
        Constructor for the QMainWindow, also containing constants and variables used throughout the class.
        """
        super(MainWindow, self).__init__(parent)
        self.showFullScreen()
        self.setWindowIcon(QtGui.QIcon('icon_logo.png'))

        # Other stuff - for keeping track of MedicalArduino instances and timing
        self.arduinos = []
        self.timer = QtCore.QTimer()
        self.prevs = []
        
        # UI Titles and size constants
        self.title = "Data Aqcuisition"
        self.tabname1 = "Devices"
        self.tabname2 = "File Upload"
        self.tabname3 = "Camera"
        self.width = 640
        self.height = 480
        self.initUI()
        self.supportedfiles = ('.jpg','.png','pdf') #files supported by USB file detection
        self.selected_image = None
        
    def addDigit(self, digit):
        """
        Adds a digit to the 'patient_ID' or removes the last digit if 'back' was pressed and then updates the QtLabel on the GUI
        """
        # Work out if 'back' or a digit was pressed and change patient_ID accordingly
        if digit == "back":
            self.patient_ID = self.patient_ID[:-1]
        else:
            self.patient_ID = self.patient_ID + digit
        
        # Update the GUI with the new patient_ID
        self.id.setText(self.patient_ID)
        self.id.update()
        
    def openNumberPad(self):
        """
        Tell user that number pad is opening and then open the number pad popup window
        """
        self.display("Opening popup number pad...")
        self.w = NumberPadPopup(self)
        self.w.show()

    def initUI(self):
        """
        Sets up Main Window GUI split into 2 sections;
        1. Top row containing common functions to all tabs
        2. Main body containing the tabs widget
        
        """
        
        #INTERFACE BUTTONS
        self.interface_row = QHBoxLayout()
        
        # Patient ID form -single patient ID form to avoid overwriting problem
        self.patient_ID = "" 
        self.id = QLabel()
        self.id.setText('[Please enter ID]')
        self.input_form = QFormLayout()
        self.input_ID_button = QPushButton("Input ID")
        self.input_ID_button.clicked.connect(self.openNumberPad)
        #self.input_ID_button.setMinimumHeight(50)
        patient_ID_row = QHBoxLayout()
        patient_ID_row.addWidget(self.id)
        patient_ID_row.addStretch(1)
        patient_ID_row.addWidget(self.input_ID_button)
        self.input_form.addRow("Patient ID:", patient_ID_row)
        self.interface_row.addLayout(self.input_form)
        
        # Detect button -single detect button to act as switch based on current tab
        self.detect = QPushButton("Detect",self)
        self.detect.setMinimumHeight(50)
        self.detect.clicked.connect(self.detectswitch)
        self.interface_row.addWidget(self.detect)

        # Send button - single send button to act as switch based on current tab
        self.send = QPushButton("Send")
        self.send.setMinimumHeight(50)
        self.send.clicked.connect(self.sendDataSwitch)
        self.interface_row.addWidget(self.send)
        
        #TABS WIDGET
        self.tabs = QTabWidget()
        self.tab1 = QWidget()
        self.tab2 = QWidget()
        self.tab3 = QWidget()
        self.tabs.resize(self.width, self.height)
        self.tabs.addTab(self.tab1, self.tabname1)
        self.tabs.addTab(self.tab2, self.tabname2)
        self.tabs.addTab(self.tab3, self.tabname3)
        self.tab1UI()
        self.tab2UI()
        self.tab3UI()
        
        #Set window title
        self.setWindowTitle(self.title)

        # Set size and centre the window in the desktop screen
        self.setGeometry(0, 0, self.width, self.height)
        qtRectangle = self.frameGeometry()
        centerPoint = QDesktopWidget().availableGeometry().center()
        qtRectangle.moveCenter(centerPoint)
        self.move(qtRectangle.topLeft())
        
        # Create a central widget which will hold all subcomponents
        layout = QGridLayout()
        layout.addLayout(self.interface_row,0,0)
        layout.addWidget(self.tabs,1,0)
        self.central=QWidget()
        self.central.setLayout(layout)
        self.setCentralWidget(self.central)
        self.statusBar()
        self.show()
        
    def tab1UI(self):
        """
        Tab1 is split into 2 rows.
        The top row contains: dropdown menu for selecting device, start/stop recording button
        The bottom row contains a matplotlib graph widget for plotting device outputs
        """
        # INTERFACE ROW
        top_row1 = QHBoxLayout()
        
        # Checkable dropdown menu for recording selection
        self.dropdown = QToolButton(self)
        self.dropdown.setMinimumHeight(50)
        dropdownSizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.dropdown.setSizePolicy(dropdownSizePolicy)
        self.dropdown.setText('Select recordings')
        self.dropdown.setPopupMode(QToolButton.InstantPopup)
        self.toolmenu = QMenu(self)
        self.toolmenu.triggered.connect(self.onChecked)
        self.dropdown.setMenu(self.toolmenu)
        top_row1.addWidget(self.dropdown)
        
        # Start stop button
        self.startstop = QPushButton("Start/Stop Recording")
        self.startstop.setMinimumHeight(50)
        self.startstop.clicked.connect(self.start_stop)
        top_row1.addWidget(self.startstop)

        # VISUAL ROW (PLOTTING WIDGET)
        visual_row1 = QHBoxLayout()
        self.graph = PlotCanvas(self)
        visual_row1.addWidget(self.graph)

        #DEFINE GRID LAYOUT AND ADD INTERFACE/VISUAL ROWS
        self.layout = QGridLayout()
        self.layout.addLayout(top_row1, 0, 0)
        self.layout.addLayout(visual_row1, 1, 0)
        self.tab1.setLayout(self.layout)
        
    def onChecked(self):
        """
        """
        for i, arduino in enumerate(self.arduinos):
            for action in self.toolmenu.actions():
                prefix = "{}. ".format(i+1)
                if action.text().startswith(prefix):
                    arduino.active_data[action.text().strip(prefix)] = action.isChecked()
        
        self.graph.plot(self.arduinos)

    def tab2UI(self):
        """
        Tab split into 2 rows
        1. Top row contains dropdown menu for selecting file upload
        2. Second row contains space for QPixmap image
        """
        
        #INTERFACE ROW
        top_row2=QHBoxLayout()
        
        #Drop down menu for selecting detected images
        dropdownSizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.imagemenu = QMenu(self)
        self.imagedrop=QToolButton()
        self.imagedrop.setMinimumHeight(50)
        self.imagedrop.setSizePolicy(dropdownSizePolicy)
        self.imagedrop.setText('Select File')
        self.imagedrop.setMenu(self.imagemenu)
        self.imagedrop.setPopupMode(QToolButton.InstantPopup)
        top_row2.addWidget(self.imagedrop)
             
        #DEFINE VISUAL ROW (IMAGE WIDGET)
        visual_row2 = QHBoxLayout()
        self.image = QLabel()
        self.image.setAlignment(QtCore.Qt.AlignCenter)
        visual_row2.addWidget(self.image)
        
        #DEFINE GRID LAYOUT AND ADD INTERFACE/VISUAL ROWS
        self.layout2 = QGridLayout()
        self.layout2.addLayout(top_row2,0,0)
        self.layout2.addLayout(visual_row2,1,0, QtCore.Qt.AlignCenter)
        self.tab2.setLayout(self.layout2)
        
    def tab3UI(self):
        """
        Holds custom camera_widget.
        """
        self.layout3 = QVBoxLayout()
        #initialise custom webcam widget
        self.webcam = camWidget(self)
        self.layout3.addWidget(self.webcam)
        self.tab3.setLayout(self.layout3)
        
        
    def display(self, msg):
        """
        Adds status bar to display messages to GUI
        """
        print(msg)
        self.statusBar().showMessage(str(msg))
        
    def detectUSBArduinos(self):
        """
        Within detectUSBArduinos():
        1. detect_ports connection
        2. Send header request ('A')
        3. Create USBArduino() using header
        """
        # Scan through USB connections: serial.tools.list_ports.comports()
        for p in serial.tools.list_ports.comports():
            self.display("detected device at port {}".format(p.device))
            if not any(all(id in p.hwid for id in hwid) for hwid in hwids):
                print("hwid mismatch")
                continue
            ser = serial.Serial(p.device, baudrate, timeout=10)
            time.sleep(2) # temporary workaround
            ser.write(b'A')
            time.sleep(0.5) # temporary workaround
            while True: # read until endline ('\n') in case json is buffered
                j = ser.readline()
                if j.endswith(b'\n'):
                    break
            try:
                header = json.loads(j.decode())
                print(header)
            except:
                continue

            # Create a new USBArduino using this information
            arduino = USBArduino(ser, header)
            self.arduinos.append(arduino)
            self.prevs.append(0) # such that data will be requested on '>/=' click
    
    def detectBluetoothArduinos(self):
        # Scan through Bluetooth connections
        self.display("scanning for nearby bluetooth devices...")
        nearby_devices = discover_devices(duration=4, lookup_names=True)
        print(nearby_devices)
        for i, (addr, name) in enumerate(nearby_devices):
            if name not in bluetooth_devices or addr in blacklist:
                continue
            self.display("detected bluetooth device at address {}".format(addr))
            sock = BluetoothSocket(RFCOMM)
            #sock.settimeout(10)
            try:
                sock.connect((addr, bluetooth_port))
            except btcommon.BluetoothError as err:
                self.display(err)
                continue
            #time.sleep(1)
            sock.send(b'A')
            #time.sleep(0.1)
            data = b''
            while True:
                data += sock.recv(1024)
                print(data)
                if data.endswith(b'\n'):
                    break
            header = json.loads(data.decode())
            print(header)
            
            # Create a new BluetoothArduino
            arduino = BluetoothArduino(sock, header)
            self.arduinos.append(arduino)
            self.prevs.append(0) # such that data will be requested on '>/=' click
    
    def detect_ports(self):
        # Close all currently open ports
        for arduino in self.arduinos:
            arduino.close()

        # Update self.dropdown (via self.toolmenu) and self.arduinos
        # TODO: submenus for each arduino and its data_labels in toolmenu
        self.toolmenu.clear()
        self.arduinos = []
        
        #usb_thread = threading.Thread(target=self.detectUSBArduinos)
        #usb_thread.start()
        #bluetooth_thread = threading.Thread(target=self.detectBluetoothArduinos)
        #bluetooth_thread.start()
        #usb_thread.join()
        #bluetooth_thread.join()
        
        self.detectUSBArduinos()
        self.detectBluetoothArduinos()
        
        # Register new arduinos in the GUI
        for i, arduino in enumerate(self.arduinos):
            for j, data_label in enumerate(arduino.data_labels):
                action = self.toolmenu.addAction("{}. {}".format(i+1, data_label))
                action.setCheckable(True)
                action.setChecked(True)
        
        # Replot graph such that the legend updates
        self.graph.plot(self.arduinos)
        self.display("Done.")
        
    def start_stop(self):  # called when the start/stop button is clicked
        """
        Set up graph according to selected arduinos and start timer
        """
        if not self.timer.isActive():
            #for action in self.toolmenu.actions():
            #    action.setCheckable(False)
            
            # Reset data plots
            for arduino in self.arduinos:
                for label in arduino.data_labels:
                    arduino.data[label] = []

            # Connect the updater() function to the clock and start it
            self.timer.timeout.connect(self.updater)
            self.timer.start(0)
            self.display("Recording started")
        else:
            #for action in self.toolmenu.actions():
            #    action.setCheckable(True)
            self.timer.stop()
            self.display("Recording ended")

    def updater(self):  # called regularly by QTimer
        """
        Query arduinos for new data according to their sampling rates.
        Update active curves (according to toolmenu selection) with the returned data.
        """
        for i in range(len(self.arduinos)):
            if time.time() - self.prevs[i] > 1.0 / self.arduinos[i].sampling_rate:
                self.arduinos[i].sample()
                self.graph.plot(self.arduinos)
                self.prevs[i] = time.time()

    def sendDataTimeSeries(self):  # called when the send button is clicked
        """
        1. Read patient ID from GUI text field
        2. Extract data from MedicalArduino list
        3. Send data to Xenplate
        (This is for time series data)
        """
        if not self.timer.isActive():
            self.display("Sending data to Xenplate...")

            # Read patient ID
            print("Patient ID:", self.patient_ID)
            if self.patient_ID == "":
                self.display("Error: no patient ID input!")
                return

            # Check for no data
            if not any(any(len(medicaldata) > 0 for medicaldata in arduino.data)
                       for arduino in self.arduinos):
                self.display("No data to send!")
                return
            
            # Extract data
            # TODO data label repeat checking
            data = {}
            for arduino in self.arduinos:
                for label in arduino.data_labels:
                    data[label] = np.mean(arduino.data[label])
            print(data)

            # Convert to uploadable format
            values = [{'name': 'Date', 'value': to_long_time(datetime.now())},
                      {'name': 'Time', 'value': to_long_time(datetime.now())},
                      {'name': 'Pulse', 'value': data['Heart_rate']},
                      {'name': 'Oxygen', 'value': data['Oxygen']}]

            # Look up Xenplate patient record using patient ID and create an entry
            data_create(record_search(self.patient_ID),
                        template_read_active_full(arduino.name),
                        values)

            #self.graph.getPlotItem().clear()
            self.display("Sent.")
        else:
            self.display("Recording still ongoing - end recording before sending data")

    def sendDataFile(self, file_name):  # called when the send button is clicked
        """
        1. Read patient ID from GUI text field
        2. Extract data from MedicalArduino list
        3. Send data to Xenplate
        (This is for file/image data)
        """
        self.display("Sending data to Xenplate...")

        # Read patient ID
        print("Patient ID:", self.patient_ID)
        if self.patient_ID == "":
            self.display("Error: no patient ID input!")
            return
        print(file_name)

        # find file_key
        with open(file_name, 'rb') as content_file:
            content = content_file.read()
            file_key = file_create(content, file_name)
            
        # set the data to push
        values = [{'name': 'FileUpload1', 'value':  file_name, 'attachments': [{'description': 'image1', 'key': file_key, 'original_file_name': file_name, 'saved_date_time': to_long_time(datetime(2019,5,29))}]}]
            

        # Look up Xenplate patient record using patient ID and create an entry
        data_create(record_search(self.patient_ID),
                    template_read_active_full('Image_test'),
                    values)
        self.display("File sent")
        #self.display("Sent.")


    def showimage(self): #called when image from dropdown menu selected
        """
        Displays image in center of tab and displays "image_name selected"
        Then adds image to list of selected images
        """
        action=self.sender()
        path = action.text()
        self.selected_image = path
        self.display(path + ' selected')
        if path.endswith('pdf'):
            path='pdf_logo.jpg'
        self.pixmap = QtGui.QPixmap(path)
        self.pixmap = self.pixmap.scaled(230, 500, QtCore.Qt.KeepAspectRatio)
        self.image.setPixmap(self.pixmap)
        
        
    def detectUSB(self): #called when "Detect" button clicked on Images tab
        """
        1. Clears image list arrays
        2. Searches directory assigned to usb devices for files of type specified by self.supportedfiles
        3. Adds file paths to a new array and updates dropdown menu
        """
        self.imagemenu.clear()
        self.imagelist=[]
        #for root, dirs, files in os.walk(os.getcwd()): #temporary for PC
        for root, dirs, files in os.walk(usb_dir):
            for filename in files:
                if filename.endswith(self.supportedfiles): #edit this line for supported file formats
                    self.imagelist.append(os.path.join(root,filename))
        if self.imagelist: 
            group = QActionGroup(self.imagemenu)
            for image in self.imagelist:
                action = self.imagemenu.addAction(image, self.showimage)
                action.setCheckable(True)
                action.setChecked(False)
                group.addAction(action)
            self.display('Files found')
            group.setExclusive(True)
        elif not self.imagelist:
            self.display('No images found, please insert USB storage device')
        
        
    def keyPressEvent(self, e):
        """
        Closes window by pressing -esc key
        """
        if e.key() == QtCore.Qt.Key_Escape:
            for arduino in self.arduinos:
                arduino.close()
            self.close()
            
    def detectswitch(self):
        """
        Switches function of "Detect" button depending on current tab open
        tab1: detects Arduino devices
        tab2: detects USB flash drives
        tab3: sets up webcam
        """
        current_tab = self.tabs.currentIndex() + 1 #add 1 to be consistent with tab numbers
        if current_tab == 1:
            self.detect_ports()
        elif current_tab == 2:
            self.detectUSB()
        elif current_tab == 3:
            self.display('Detecting camera...')
            self.webcam.setup()
            
    def sendDataSwitch(self):
        """
        Switches function of "Send" button depending on current tab open
        tab1: sends time series data
        tab2: sends the file loaded
        tab3: sends the last capture
        """
        current_tab = self.tabs.currentIndex() + 1 #add 1 to be consistent with tab numbers
        if current_tab == 1:
            self.sendDataTimeSeries()
        elif current_tab == 2 or 3:
            if self.selected_image:
                self.sendDataFile(self.selected_image)
            else:
                self.display("No image selected")
            
        
if __name__ == '__main__':
    app = QApplication([])
    window = MainWindow()
    sys.exit(app.exec_())
