ShortPy
=======

Collection of iOS shortcuts & with (and without) Python scripts:


# Restaurant Menu Bot

> This shortcut requires installed ChatGPT + permissions to "Execute scripts" (in Shortcuts Settings)  
> Shourtcut does not require Python

1. Choose from menu (to get the location or restaurant)
2. For each entry, set Text with the URL link (to the restaurant menu)
3. Afte End Menu, insert "Get contents of ..." where ... is the Menu Result
4. Set variable `menu` to "Content of the URL" output
5. Ask for Text input (what do you fancy today?)
6. Set variable `choice` to "Provided input"
7. Insert standalone Text - put your prompt for GPT. For example, _Following is a restaurant menu. I need to select only those options that ..._
8. Set variable `prompt` to the inserted Text
9. Add "Ask ChatGPT" with input: '`prompt`: `menu`. This is my preference: `choice`'
    * Recommended options of the shortcut: Start new chat, but without continuous chat and without Show When Run. Select a model of your choice (4o mini should be the fastest)
10. Add Show "Ask ChatGPT" output

# FuelPrice

> Shourtcut does require Python (see dependencies)

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

# Currency Convertor

Simple currency convertor

> Shourtcut does require Python (see dependencies)

### **Python/PyTo**

Open [PyTo](https://pyto.app) and 
* save the file `Currencies/currencies.py`
* test by running `currencies.py` 

### **iOS shortcut**

1. Ask from menu to select "FROM -> TO", e.g. "CZK -> EUR"
2. Set the selected menu result item as `fromto` (meaning if "CZK -> EUR" set 'TEXT' to "CZK->EUR")
3. Ask for value to be converted (simple Ask for Number with XYZ descruption)
4. Save the result of the user input as `value`
5. Call `currencies.py` with `fromto` and `value` arguments

# Github Trending scraper

[See the respective README](GithubTrending/README.md)

--------------
# Dependencies

* iOS version with shortcuts, tested on > 14.5
* Python interpreter/REPL on iOS: [PyTo](https://pyto.app) including option to install PyPi ([Full Version](https://apps.apple.com/us/app/pyto-python-3/id1436650069?ign-mpt=uo%3D4) or Trial)
    * See  `requirements.txt` for the full list of PIP dependencies 
* Allowed permissions to execute scripts

## Disclaimer

* No guarantee the code will run on your device :)
* for non-commercial purposes only