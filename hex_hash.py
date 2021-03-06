import os	
import hashlib	
import base64	
import requests	

url = 'https://api.github.com/repos/alfredclwong/3GM1/contents/hashes.txt'
avr_exe = "avrdude"
avr_conf = "/etc/avrdude.conf"
port = "/dev/ttyUSB0"
hex_fname = "nano.hex"	

def sha256(fname):	
    # Generate SHA256 hash from the hex file	
    hash_sha256 = hashlib.sha256()	
    with open(hex_fname, "rb") as f:	
        for chunk in iter(lambda: f.read(4096), b""):	
            hash_sha256.update(chunk)	
        return hash_sha256.hexdigest()	

def verify_arduino(port):
    # Call avrdude.exe to extract and save the Arduino's hex file	
    os.system("{} -c arduino -p m328p -C {} -P \"{}\" -b 57600 -U flash:r:{}:i"
              .format(avr_exe, avr_conf, port, hex_fname))

    # Generate SHA256 checksum from the hex file	
    hash = sha256(hex_fname)	
    print(hash)	

    # Verify hash against list of verified hashes on GitHub	
    req = requests.get(url)	
    if req.status_code == requests.codes.ok:	
        req = req.json()
        verified_hashes = base64.b64decode(req['content']).decode().split('\n')	
        verified_hashes = list(filter(('').__ne__, verified_hashes))
        print(verified_hashes)
        return (hash in verified_hashes)
    else:
        print('Content was not found.')
        return False
