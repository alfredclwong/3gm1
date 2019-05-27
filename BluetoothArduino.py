import json
import time

# TODO incorporate MedicalArduino (rename to SerialArduino?) and BluetoothArduino into a class hierachy

class BluetoothArduino:
    def __init__(self, sock, header_dict):
        """
        Interpret and store the decoded json dictionary from the handshake header file.
        Start an empty data tracking dictionary, according to data_labels.
        """
        self.sock = sock
        
        self.name           = header_dict["name"]
        self.data_labels    = header_dict["labels"]
        #self.data_types     = header_dict["data_types"]
        #self.data_units     = header_dict["data_units"]
        self.data_ranges    = header_dict["data_range"]
        self.sampling_rate  = header_dict["sampling_rate"]
        
        self.data = {label: [] for label in self.data_labels}#["time"] + self.data_labels}
        self.start = time.time()
        
        #self.active_data = [True] * 
    
    def set_active_data(self):
        pass
    
    def sample(self):
        """
        Called by the GUI clock at regular intervals according to self.sampling_rate.        
        Send a data request signal to the Arduino and interpret the json output.
        Return the entire history of all recorded data (regardless of whether or not a
        null value was read or if the data series are not 'checked' in the GUI).
        """
        self.sock.send('B')
        data = b''
        while True:
            data += self.sock.recv(1024)
            if data.endswith(b'\n'):
                break
        data = json.loads(data.decode())
        if not any(x == 0 for x in data.values()):
            for label in self.data_labels:
                self.data[label].append(data[label])
            #self.data["time"].append(time.time() - self.start)
        print(data)
        #print(self.data)
        #return self.data
