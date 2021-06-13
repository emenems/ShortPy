import sys
import numpy as np
import requests 
from datetime import date, timedelta

class FuelPrice:
    """Compute Fuel Price using input parameters

    Parameters
    ----------
    consumption: avarage consumptions
    distance: covered distance in km
    price: price in Euro/1 L. Set to None to get the value from https://data.statistics.sk APIs -> to get average price
    fuel: fuel type, 'diesel' or 'gasoline' (95 octane)

    """

    def __init__(self,
                 consumption: float,
                 distance: float,
                 price: float = None,
                 fuel: str = 'gasoline'
                 ):
                 
        self.consumption=consumption
        self.distance=distance
        self.price=price
        self.fuel=fuel


    def comp_price(self) -> float:
        """Compute the average price"""

        if self.price is None:
            price = self.get_average_price()

        return np.round(self.consumption*self.distance*price/100 ,2)


    def return_price(self,
                     lang: str = "en") -> None:
        """Return the average price
        
        Parameters
        ----------
        lang: output language. 'sk' for slovak or english 
        """
        if lang == "sk":
            print(f"Cena za jazdu: {self.comp_price()} €")
        else:
            print(f"Price for the ride: {self.comp_price()} €")

    def get_average_price(self,
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


if __name__ == "__main__":
    consumption = 3.3
    distance = 74

    fp = FuelPrice(consumption,distance)
    fp.return_price()