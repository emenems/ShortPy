import sys
import numpy as np
from forex_python.converter import CurrencyRates
import warnings
warnings.filterwarnings("ignore")

"""
Simple currency convertor

Example:
```
# Convert 1 EUR to CZK
python currencies.py EUR->CZK 1
```
"""
if __name__ == "__main__":
    
    # see https://forex-python.readthedocs.io/en/latest/usage.html
    c = CurrencyRates()

    # For test = no user input
    if len(sys.argv) == 1:
        value = 1
        origin = "EUR"
        target = "CZK"

    else:
        # Get user inputs and convert to floating number for input value
        # Expecting input in format 'EUR->CZK' (FROM->TO)
        fromto = sys.argv[1].replace(" ","")
        origin = fromto.split("->")[0].upper()
        target = fromto.split("->")[-1].upper()
        value = float(sys.argv[2].replace(",","."))
        
    print(f"{np.round(c.convert(origin,target,value),2)} {target}")

