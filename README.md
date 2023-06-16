# Parser for listings on zillow, streeteasy, renthop.com 
Parses and adds the extracted attributes to the specified google sheets document.  

1. Clone the repository.  
2. Create an .env file in the root directory and define the following;  
   - BASE_URL: your domain or local machine url (e.g. xxxxx.com)
   - SPREADSHEET_ID: for google sheets ( e.g. 1dk2k137ihnmdfwqe...we213)
   - RANGE_NAME : for google sheets (e.g. !A2:E)  
   - SERVICE_ACCOUNT_INFO: a json object that you will be given at Google Cloud console.  
   - TELEGRAM_API_TOKEN: your key for the telegram bot you created through Telegram's BotFather. You can generate it with ```/token``` command.
   - TELEGRAM_BOT_CHAT_IDS: a list of allowed users' chat IDS to make the bot for your private use. 
4. pip install the dependencies in  the requirements.txt file  after changing the directory to each of them.(e.g. ```cd flask-server``` and/or ```cd telegrambot```  
5. Run them seperately and make sure to update your BASE_URL if you deploy.
6. Test out the flask-server by sending a POST request to ```{{BASE_URL}}/api/parse-listing ``` with a body of  
   {  
      "url": "THE URL OF THE LISTING YOU WANT TO PARSE"  
   }  
7. if you deployed the telegrambot as well and added your chat_id of you will be able to trigger the endpoint by searching your bot's name on telegram, tapping start and running ```/add LISTING_URL``` command, which will return a JSON object of the attributes extracted.  
   


