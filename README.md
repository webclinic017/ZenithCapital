
# Zenith Capital

### Installation
* Install the latest version of TWS workstation [here](https://www.interactivebrokers.com/en/index.php?f=14099#tws-software)
* Once logged in, navigate to File > Global Configuration > API > Settings
    * Enable "Enable ActiveX and Socket Clients"
    * Enable "Download open orders on connection"
    * Disable "Read-Only API"
    * Take note of "Socket port"
* Subscribe to relevant market streams in IBKR if needed
* Fill in config.py file, place the socket port found here
* Install python prerequisites using `pip install -r requirements.txt`

### Google Spreadsheet
* Create spreadsheet, for each sheet it will refer to a stock
* Sheets should be named as the stock symbol in all capitals
* Ensure the sheet follows this format ![spreadsheet](https://i.imgur.com/ZqZgaFK.png) 
* Place the spreadsheet id in the config.py file

### Setting Up sheets.py
This has to be done to allow the program to access the spreadsheet
* First create a google cloud project by following this [tutorial](https://developers.google.com/workspace/guides/create-project)
* Enable this API: "Google Sheets API"
* Add `http://localhost:12345` as a Redirect URI
* Create credentials by following this [tutorial](https://developers.google.com/workspace/guides/create-credentials)
* Rename JSON file to `cred.json`
* Run `python sheets.py` and it will create necessary `tokens.json` file
    * In the future, this may need to be re-run to update the tokens

### Running
Once all of the above steps have been followed, this script can be ran indefinitely by using the following command:
`python main.py`

This will subscribe to all of the enabled stocks found in the spreadsheet, once a price comes close to a support/resistance defined in the spreadsheet and a trend has been determined, it will place the corresponding order determined by other factors within the spreadsheet. 

## 
Developed by Youssef, theorized by Max and Lucian

For any help, please contact me [here](mailto:youssef@elshemi.com)