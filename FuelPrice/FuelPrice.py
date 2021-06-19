import sys
import numpy as np
import pandas as pd
import requests 
from datetime import date, timedelta
import warnings
import os
warnings.filterwarnings("ignore")

class FuelPrice:
    """Compute Fuel Price using input parameters

    Parameters
    ----------
    consumption: avarage consumptions
    distance: covered distance in km
    price: price in Euro/1 L. Set to None to get the value from https://data.statistics.sk APIs -> to get average price
    fuel: fuel type, 'diesel' or 'super95' (Euro-Super95)

    """

    def __init__(self,
                 consumption: float,
                 distance: float,
                 fuel: str = 'super95',
                 price: float = None
                 ):
                 
        self.consumption=consumption
        self.distance=distance
        self.price=price
        self.fuel=fuel


    def comp_price(self,
                   country: str = "Slovakia") -> float:
        """Compute the average price"""

        if self.price is None:
            price = self.get_average_price_eu(country)
        else:
            price = self.price

        return np.round(self.consumption*self.distance*price/100 ,2)


    def return_price(self,
                     country: str = "Slovakia") -> None:
        """Return the average price
        
        Parameters
        ----------
        country: country. I
        """
        if country.lower() == "slovakia":
            print(f"Cena za jazdu: {self.comp_price(country)} €")
        else:
            print(f"Price for the ride: {self.comp_price(country)} €")


    def get_average_price_sk(self,
                             lag: int = 14):
        """Query average price from https://data.statistics.sk/api/detail.php# searching for 'Priemerné ceny pohonných látok v SR'
        
        

        Parameters:
        ----------
        lag: As the API/DB has some lag, use 'lag' variable (in days)

        Returns
        -------
        price. Is None if no data or error during query 

        """


        # Get week of year
        woy = (date.today()-timedelta(days=lag)).strftime("%Y%V")

        # Get fuel type 
        if self.fuel == 'diesel':
            fuel_type = 'UKAZ04'
        else:
            fuel_type = 'UKAZ01'

        url_json = f"https://data.statistics.sk/api/v2/dataset/sp0207ts/{woy}/{fuel_type}?lang=sk&type=json"

        # download data set
        try:
            r = requests.get(url_json)
            if r.status_code!=200:
                price = None
            else:
                price = r.json()['value'][-1]
        except:
            price = None

        return price


    def get_eu_prices(self):
        """Download dataset from https://ec.europa.eu/energy/data-analysis/weekly-oil-bulletin_en
        More specifically http://ec.europa.eu/energy/observatory/reports/latest_prices_with_taxes.xlsx

        """
        try:
            # Download data & fromat for easy processing
            r = requests.get('http://ec.europa.eu/energy/observatory/reports/latest_prices_with_taxes.xlsx')
            
            if r.status_code!=200:
                return pd.DataFrame()

            with open('latest_prices_with_taxes.xlsx','wb') as fid:
                fid.write(r.content)

            df = pd.read_excel('latest_prices_with_taxes.xlsx',
                                sheet_name="En In EURO",engine='openpyxl')
                                
            os.remove('latest_prices_with_taxes.xlsx')

            df = df.dropna(subset=["Unnamed: 1","Unnamed: 2","Unnamed: 3"]).iloc[0:-2]
            df = df.rename(columns={"Unnamed: 1":"country", 
                                    "Unnamed: 2":"super95",
                                    "Unnamed: 3":"diesel"})
            df = df.set_index("country")[["super95","diesel"]]
            # convert to Euro/L
            for i in df.columns:
                df[i] = df[i].replace(",","",regex=True).astype(float)/1000

            return df

        except:

            return pd.DataFrame()


    def get_average_price_eu(self,
                             country: str = "Slovakia"):
        """Query average price from https://ec.europa.eu/energy/data-analysis/weekly-oil-bulletin_en
        More specifically http://ec.europa.eu/energy/observatory/reports/latest_prices_with_taxes.xlsx
        and return the price for selected fuel and country

        Parameters:
        ----------
        country: name of the country in EU, e.g. Slovakia, Czechia, Austria,...

        Returns
        -------
        price. Is None if no data or error during query 

        """

        df = self.get_eu_prices()
        if df.empty:
            return None
        else: 
            return df.loc[country][self.fuel]



if __name__ == "__main__":
    
    # For test = no user input
    if len(sys.argv) == 1:
        fp = FuelPrice(3.3,74,"super95",1.365)
        
        fp.return_price()

    else:
        
        # Get user inputs and convert to floating numbers
        consumption = float(sys.argv[1].replace(",","."))
        distance = float(sys.argv[2].replace(",","."))

        # get optional inputs
        if len(sys.argv) >= 6:
            price = float(sys.argv[5].replace(",","."))
        else:
            price = None

        if len(sys.argv) >= 4:
            fuel = sys.argv[3].lower()
        else:
            fuel = 'super95'

        if len(sys.argv) >= 5:
            country = sys.argv[4]
        else:
            country = 'Slovakia'

        fp = FuelPrice(consumption,distance,fuel,price=price)
        
        fp.return_price(country)