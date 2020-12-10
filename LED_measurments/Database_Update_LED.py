import pandas as pd
import datetime
import time
from sqlalchemy import create_engine
import ipywidgets as widgets
from ipywidgets import interactive
from IPython.display import display   
import warnings

def write_to_database(summarydatarow):
    table = []
    Date , Time = date_time()
    for item in summarydatarow :
        table_temp = []
        table_temp.append(Date)
        table_temp.append(Time)
        for data in item :
            table_temp.append(data)
        table.append(table_temp)
    for item in table :
        for i in range(len(item)):
            if i == 4 :
                item[i] = str(item[i]) + ' nm'
            elif i == 5 :
                item[i] = str(item[i]) + ' nm'
            elif i == 6 :
                item[i] = str(item[i]) + ' W/A'

    engine = create_engine("postgresql://postgres:uv-sintec@localhost:5432/LED_Measurements") 
    for item in table :
        df1 = pd.DataFrame([item] , columns = ["date", "time", "device_number", "product_code", "average_peak_wavelength", "fwhm_bandwidth", "slope", "r_squared", "filename"])

        df1.to_sql('led_measurements' , con = engine , if_exists = "append" , index = False)
        df = pd.read_sql_query('select * from "led_measurements"' , con = engine)

        index = []
        count = 0
        device_number = item[2]
        productcode = item[3]
        
        
        for i in range(len(df)):
            if [df.loc[count][2],df.loc[count][3] ] == [device_number, productcode]:
                index.append(count)
            count += 1

        if len(index) > 1:
            check = False
            print("The LED with Device Number %s has been identified as a duplicate" % device_number)
            print("")
            while check == False :
                update = input("Do you want to update the LED in the Database (y/n) :")
                if update.lower().strip() == "y" :
                    if len(index) > 1 :
                        df = df.drop(index[-2]).reset_index(drop = True)
                    check = True
                elif update.lower().strip() == "n" :
                    check = True
                else :
                    print("")
                    print("Error please select y/n")
                    check = False


        df.to_sql('led_measurements' , con = engine , if_exists = "replace" , index = False)

    return df

def date_time():
    datetime_object = datetime.datetime.now()
    time = str(datetime_object.time())[:8]
    date = str(datetime_object.date())
    
    return date , time

def Database_Search() :
    engine = create_engine("postgresql://postgres:uv-sintec@localhost:5432/LED_Measurements")

    df = pd.read_sql_query('select * from "led_measurements"' , con = engine)

    def print_database(product_code , wavelength , device_number):
        if wavelength == "All" :
            wavelength = ''
        if device_number == "All" :
            device_number = ''
        filtered = df["product_code"].str.contains(product_code)
        filtered2 = df["average_peak_wavelength"].str.contains(wavelength)
        filtered3 = df["device_number"].str.contains(device_number)
        if len(df[filtered][filtered2][filtered3]) > 0 :
            display(df[filtered][filtered2][filtered3])
        else :
            print("No LED's in the database match your search")  

    def menu_adjust(wavelength , product_code):
        filtered = df["product_code"].str.contains(product_code)
        wavelengthW.options = update_menu(df[filtered]["average_peak_wavelength"])
        filtered2 = df[filtered]["average_peak_wavelength"].str.contains(wavelength)
        device_numberW.options = update_menu(df[filtered][filtered2]["device_number"])

    def update_menu(menu) :
        menu_final = ["All"]
        for item in menu :
            if item in menu_final :
                pass 
            else :
                menu_final.append(item)        

        return menu_final
    
    style = {'description_width': 'initial'}

    product_codeW = widgets.Text(
        placeholder='Enter Product Code',
        description=' Product Code:',
        disabled=False ,
        style = style   
    )

    init = product_codeW.value
    filter1 = df["product_code"].str.contains(init)
    wavelengthW = widgets.Dropdown(
        options =  update_menu(df[filter1]["average_peak_wavelength"]),
        description = 'Wavelength : ',
        disabled = False ,
        style = style
    )

    init2= wavelengthW.value 
    filter2 = df[filter1]["average_peak_wavelength"].str.contains(init2)
    device_numberW = widgets.Dropdown(
        options= update_menu(df[filter1][filter2]["device_number"]) , 
        description = 'Device Number : ',
        disabled = False ,
        style = style) 

    j = widgets.interactive(print_database, product_code=product_codeW, wavelength=wavelengthW , device_number = device_numberW)
    k = widgets.interactive(menu_adjust, wavelength = wavelengthW , product_code = product_codeW ) 

    return display(j)  

def Data_Extract() :
    product_code = str(input("Enter Full Product Code :")).replace(" ", "")

    engine = create_engine("postgresql://postgres:uv-sintec@localhost:5432/LED_Measurements")

    df = pd.read_sql_query('select * from "led_measurements"' , con = engine)
    df1 = df.loc[(df["product_code"] == product_code)] 

    if len(df1) > 0 :
        display(df1)
        row = int(input("Which Row do you wish to extract data from :"))

        items_list = [df1.columns.values.tolist()] + df1.loc[row].tolist()
        print("The Data has been saved to variable 'items_list'")
        print("The location of the data corresponds to the location of the column heading ")
        print("e.g. the label_wavelength value is item_list[4]")

        for i in range(len(items_list[0])) :
            print("%i. %s" %(i+1 , items_list[0][i]))

        return items_list

    else :
        return print("This product code does not match any LED's in the Database")
    
def Row_Delete() :
    product_code = str(input("Enter Full Product Code :")).replace(" ", "")
    
    engine = create_engine("postgresql://postgres:uv-sintec@localhost:5432/LED_Measurements")
    
    df = pd.read_sql_query('select * from "led_measurements"' , con = engine)
    df1 = df.loc[(df["product_code"] == product_code)]
    
    if len(df1) > 0 :
        
        display(df1)
        index = int(input("Select the row you wish to delete :"))

        if index in df1.index.values :
            df = df.drop(index).reset_index(drop = True)

            df.to_sql('led_measurements' , con = engine , if_exists = "replace" , index = False)
        else :
            return print("The row you selected does not correspond to the product code entered")
    else :
        return print("This product code does not match any LED's in the Database")