ShortPy
=======

Collection of scripts iOS shortcuts & Python (for non-commercial purposes only):


# FuelPrice

Compute price for your ride providing average consumption and distance. The script will query the price from Slovak Stats DB (you can modify the script easily to input the price manually)


### **Python/PyTo**

Open [PyTo](https://pyto.app) and 
* save the file `FuelPrice/FuelPrice.py`
* test by running `FuelPrice.py` 

### **iOS shortcut**

1. Ask for Number (consumption) with description (e.g. average consumption l/100 km)
2. Set variable from provided input as `consumption`
3. Ask for Number (distance) with description (e.g. distance covered (km))
4. Set variable from provided input as `distance`
5. Call PyTo to execute Script FuelPrice with `consumption` and `distance` arguments + check the Show Console

> Full shortcut on [iCloud](https://www.icloud.com/shortcuts/4b5c44e628274ed5b380523857292802)



--------------
# Dependencies

* iOS version with shortcuts, tested on > 14.5
* Python interpreter/REPL on iOS: [PyTo](https://pyto.app) including option to install PyPi ([Full Version](https://apps.apple.com/us/app/pyto-python-3/id1436650069?ign-mpt=uo%3D4) or Trial)
    * See  `requirements.txt` for the full list of PIP dependencies 